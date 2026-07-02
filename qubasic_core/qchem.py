"""QUBASIC molecular Hamiltonians — self-contained STO-3G integrals engine.

HAMILTONIAN H = MOLECULE H2 [R_angstrom] builds the exact 4-qubit
Jordan-Wigner Hamiltonian of molecular hydrogen in the STO-3G minimal basis:
Gaussian s-orbital integrals (Szabo & Ostlund closed forms), restricted
Hartree-Fock molecular orbitals (analytic by symmetry for H2), the
spin-orbital tensors, and a Jordan-Wigner transform done by building the
second-quantized 16x16 matrix from ladder operators and decomposing it with
SparsePauliOp.from_operator. No pyscf, no openfermion.

Ground truth: exact diagonalization of the result at R = 0.7414 A gives the
FCI/STO-3G energy -1.1373 Ha (nuclear repulsion included as the identity
coefficient).
"""

from __future__ import annotations

from math import erf, pi, sqrt, exp

import numpy as np

BOHR_PER_ANGSTROM = 1.0 / 0.529177210903

# STO-3G hydrogen 1s: (exponent, contraction) with zeta = 1.24 folded in.
_STO3G_H = ((3.42525091, 0.15432897),
            (0.62391373, 0.53532814),
            (0.16885540, 0.44463454))


def _f0(x: float) -> float:
    """Boys function F0(x) = (1/2) sqrt(pi/x) erf(sqrt(x))."""
    if x < 1e-12:
        return 1.0 - x / 3.0
    return 0.5 * sqrt(pi / x) * erf(sqrt(x))


def _h2_ao_integrals(r_bohr: float):
    """AO overlap, core Hamiltonian, and two-electron integrals for H2.

    Two 1s contractions on the z-axis at 0 and r_bohr. Primitive formulas are
    the standard s-orbital closed forms; contraction coefficients absorb the
    primitive normalization (2a/pi)^(3/4).
    """
    centers = (0.0, r_bohr)
    prims = []
    for c in centers:
        prims.append([(a, d * (2.0 * a / pi) ** 0.75) for a, d in _STO3G_H])

    def sep2(i, j):
        return (centers[i] - centers[j]) ** 2

    S = np.zeros((2, 2))
    T = np.zeros((2, 2))
    V = np.zeros((2, 2))
    for i in range(2):
        for j in range(2):
            r2 = sep2(i, j)
            for a, ca in prims[i]:
                for b, cb in prims[j]:
                    g = a + b
                    pre = ca * cb * exp(-a * b / g * r2)
                    S[i, j] += pre * (pi / g) ** 1.5
                    T[i, j] += pre * (a * b / g) * (3.0 - 2.0 * a * b / g * r2) \
                        * (pi / g) ** 1.5
                    # Gaussian product center (z coordinate).
                    zp = (a * centers[i] + b * centers[j]) / g
                    for zc in centers:                      # both protons, Z=1
                        V[i, j] += -pre * (2.0 * pi / g) * _f0(g * (zp - zc) ** 2)

    eri = np.zeros((2, 2, 2, 2))                            # chemists (ij|kl)
    for i in range(2):
        for j in range(2):
            for k in range(2):
                for l in range(2):
                    for a, ca in prims[i]:
                        for b, cb in prims[j]:
                            for c, cc in prims[k]:
                                for d, cd in prims[l]:
                                    g1, g2 = a + b, c + d
                                    zp = (a * centers[i] + b * centers[j]) / g1
                                    zq = (c * centers[k] + d * centers[l]) / g2
                                    pre = (ca * cb * cc * cd
                                           * exp(-a * b / g1 * sep2(i, j))
                                           * exp(-c * d / g2 * sep2(k, l)))
                                    eri[i, j, k, l] += pre * 2.0 * pi ** 2.5 / (
                                        g1 * g2 * sqrt(g1 + g2)) * _f0(
                                        g1 * g2 / (g1 + g2) * (zp - zq) ** 2)
    return S, T + V, eri


def h2_hamiltonian(r_angstrom: float = 0.7414):
    """4-qubit Jordan-Wigner SparsePauliOp for H2/STO-3G at bond length R.

    Spin-orbital order (qubit index): 0 = g up, 1 = g down, 2 = u up,
    3 = u down, with g/u the symmetric/antisymmetric molecular orbitals.
    Nuclear repulsion rides on the identity term.
    """
    from qiskit.quantum_info import Operator, SparsePauliOp

    r_bohr = r_angstrom * BOHR_PER_ANGSTROM
    S, hcore, eri = _h2_ao_integrals(r_bohr)
    s12 = S[0, 1]
    # RHF MOs by inversion symmetry: gerade and ungerade combinations.
    cg = 1.0 / sqrt(2.0 * (1.0 + s12))
    cu = 1.0 / sqrt(2.0 * (1.0 - s12))
    C = np.array([[cg, cu], [cg, -cu]])
    h_mo = C.T @ hcore @ C
    eri_mo = np.einsum('ip,jq,kr,ls,ijkl->pqrs', C, C, C, C, eri)

    # Spatial -> spin orbitals: index 2*mo + spin, spin in (0 up, 1 down).
    n_so = 4
    h_so = np.zeros((n_so, n_so))
    g_so = np.zeros((n_so, n_so, n_so, n_so))    # physicists <pq|rs>
    for p in range(n_so):
        for q in range(n_so):
            if p % 2 == q % 2:
                h_so[p, q] = h_mo[p // 2, q // 2]
            for r in range(n_so):
                for s in range(n_so):
                    if p % 2 == r % 2 and q % 2 == s % 2:
                        g_so[p, q, r, s] = eri_mo[p // 2, r // 2, q // 2, s // 2]

    # Jordan-Wigner ladder operators as dense 16x16 matrices. Qubit j is the
    # j-th kron factor from the right (little-endian, matching the display).
    I2 = np.eye(2)
    Z2 = np.diag([1.0, -1.0])
    low = np.array([[0.0, 1.0], [0.0, 0.0]])     # sigma-minus: |0><1|
    def ann(j):
        out = np.array([[1.0]])
        for k in range(n_so - 1, -1, -1):
            out = np.kron(out, low if k == j else (Z2 if k < j else I2))
        return out
    a = [ann(j) for j in range(n_so)]
    ad = [m.conj().T for m in a]

    H = np.zeros((16, 16), dtype=complex)
    for p in range(n_so):
        for q in range(n_so):
            if h_so[p, q]:
                H += h_so[p, q] * (ad[p] @ a[q])
    for p in range(n_so):
        for q in range(n_so):
            for r in range(n_so):
                for s in range(n_so):
                    if g_so[p, q, r, s]:
                        H += 0.5 * g_so[p, q, r, s] * (ad[p] @ ad[q] @ a[s] @ a[r])
    e_nuc = 1.0 / r_bohr
    H += e_nuc * np.eye(16)
    op = SparsePauliOp.from_operator(Operator(H)).simplify(atol=1e-10)
    return op
