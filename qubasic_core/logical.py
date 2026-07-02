"""QUBASIC logical-qubit mode — program at the logical level of a QEC code.

  LQUBITS 2 CODE SURFACE 5            2 logical qubits, rotated surface d=5
  LQUBITS 2 CODE SURFACE 5 PHYS 1e-3  ...at physical error rate p
  LQUBITS STATUS                      Show the active logical configuration
  LQUBITS OFF                         Back to physical qubits

While active, program gates address LOGICAL qubits: every operation carries
the code's per-op logical error channel (X/Z flips at the code-capacity
logical rate for the chosen code, distance, and physical p), measurement
carries a logical readout flip, and RUN appends a lattice-surgery compilation
report (surgery ops, syndrome rounds, physical qubits, wall time, error
budget). The histogram is over logical outcomes.
"""

from __future__ import annotations

from math import comb

import numpy as np


class LogicalMixin:
    """LQUBITS logical-qubit mode for QBasicTerminal.

    Requires: TerminalProtocol — uses self.io, self.variables, self.cmd_qubits,
    self._noise_model, self.last_circuit, self._qec_code / _logical_error_rate
    from QECMixin.
    """

    def _init_logical(self) -> None:
        self._logical_mode: dict | None = None
        self._logical_pl_cache: dict = {}

    # ── Per-operation logical error probability ─────────────────────────

    def _logical_pl(self, name: str, d: int, p: float) -> float:
        """Code-capacity logical error probability for one logical operation.

        Surface uses the standard scaling fit p_L ~ 0.1 (p/p_th)^((d+1)/2)
        with p_th = 0.01; the repetition code uses the exact majority-vote
        failure sum; Steane/Shor (d=3) fall back to a cached Monte Carlo with
        the optimal lookup decoder."""
        key = (name, d, round(p, 12))
        if key in self._logical_pl_cache:
            return self._logical_pl_cache[key]
        name = name.upper()
        if name in ('SURFACE', 'SURF'):
            pl = 0.1 * (p / 0.01) ** ((d + 1) // 2)
        elif name in ('REP', 'REPETITION', 'BITFLIP'):
            t = (d - 1) // 2
            pl = sum(comb(d, j) * p ** j * (1 - p) ** (d - j)
                     for j in range(t + 1, d + 1))
        else:
            code = self._qec_code(name, d)
            rng = np.random.default_rng(self._seed)
            pl = self._logical_error_rate(code, p, 20000, rng)
        pl = float(min(max(pl, 0.0), 0.75))
        self._logical_pl_cache[key] = pl
        return pl

    # ── Command ─────────────────────────────────────────────────────────

    def cmd_lqubits(self, rest: str) -> None:
        """LQUBITS <n> CODE <name> [d] [PHYS p] | STATUS | OFF — logical-qubit mode.

        Program gates then act on error-corrected logical qubits: each op is
        followed by the code's logical error channel and RUN reports the
        lattice-surgery compilation (ops, rounds, physical qubits, budget)."""
        arg = rest.strip()
        if not arg or arg.upper() == 'STATUS':
            lm = self._logical_mode
            if not lm:
                self.io.writeln("LQUBITS OFF (physical mode)")
            else:
                self.io.writeln(f"LQUBITS {lm['n']}: {lm['code']} d={lm['d']} "
                                f"phys p={lm['p']:g}  p_L={lm['pl']:.3e}/op")
            return
        if arg.upper() == 'OFF':
            self._logical_mode = None
            self._noise_model = None
            self._noise_spec = None
            self._circuit_cache_key = None
            self.io.writeln("LQUBITS OFF — back to physical qubits (noise cleared)")
            return
        import re as _re
        m = _re.match(r'(\d+)\s+CODE\s+(\w+)(?:\s+(\d+))?(?:\s+PHYS\s+(\S+))?\s*$',
                      arg, _re.IGNORECASE)
        if not m:
            self.io.writeln("?USAGE: LQUBITS <n> CODE <SURFACE|REP|STEANE|SHOR> [d] [PHYS p]"
                            "  |  LQUBITS OFF")
            return
        try:
            n = int(m.group(1))
            cname = m.group(2).upper()
            d = int(m.group(3)) if m.group(3) else 5
            if d % 2 == 0:
                d += 1
            p = float(self._eval_with_vars(m.group(4), {})) if m.group(4) else 1e-3
            pl = self._logical_pl(cname, d, p)

            from qiskit_aer.noise import NoiseModel, pauli_error, ReadoutError
            # Independent logical X and Z flips at rate pl per op.
            px = pz = pl * (1 - pl)
            py = pl * pl
            err1 = pauli_error([('X', px), ('Z', pz), ('Y', py),
                                ('I', 1.0 - px - pz - py)])
            _1q = ['h', 'x', 'y', 'z', 's', 't', 'sdg', 'tdg',
                   'sx', 'rx', 'ry', 'rz', 'p', 'u', 'id']
            _2q = ['cx', 'cy', 'cz', 'ch', 'swap', 'dcx', 'iswap',
                   'crx', 'cry', 'crz', 'cp', 'rxx', 'ryy', 'rzz']
            nm = NoiseModel()
            nm.add_all_qubit_quantum_error(err1, _1q)
            nm.add_all_qubit_quantum_error(err1.tensor(err1), _2q)
            nm.add_all_qubit_readout_error(
                ReadoutError([[1 - pl, pl], [pl, 1 - pl]]))
            self._noise_model = nm
            self._noise_spec = None
            self._logical_mode = {'n': n, 'code': cname, 'd': d, 'p': p, 'pl': pl}
            self.cmd_qubits(str(n))
            patch = 2 * d * d - 1 if cname in ('SURFACE', 'SURF') else \
                self._qec_code(cname, d)['n']
            self._logical_mode['patch'] = patch
            self.io.writeln(f"LQUBITS {n}: {cname} d={d}, physical p={p:g}")
            self.io.writeln(f"  p_L = {pl:.3e} per logical op "
                            f"({patch} physical qubits per patch)")
            if pl > 0.05:
                self.io.writeln("  WARNING: p is at or above threshold for this "
                                "distance — logical qubits are worse than physical")
        except Exception as e:
            self.io.writeln(f"?LQUBITS ERROR: {e}")

    # ── Post-run lattice-surgery report ─────────────────────────────────

    def _logical_trailer(self) -> None:
        lm = self._logical_mode
        if not lm or self.last_circuit is None:
            return
        d, pl, patch, n = lm['d'], lm['pl'], lm['patch'], lm['n']
        ops = dict(self.last_circuit.count_ops())
        ops.pop('measure', None)
        ops.pop('barrier', None)
        _2q_names = {'cx', 'cy', 'cz', 'ch', 'swap', 'dcx', 'iswap',
                     'crx', 'cry', 'crz', 'cp', 'rxx', 'ryy', 'rzz'}
        n2 = sum(c for g, c in ops.items() if g in _2q_names)
        n_t = ops.get('t', 0) + ops.get('tdg', 0)
        n1 = sum(ops.values()) - n2
        # Lattice-surgery schedule: a 2-qubit gate is a merge + split (2 surgery
        # ops, 2d rounds via an ancilla patch); 1-qubit Cliffords are
        # transversal (d rounds of syndrome extraction each); final readout d.
        surgery = 2 * n2
        rounds = 2 * d * n2 + d * n1 + d
        phys = (n + (1 if n2 else 0)) * patch
        total_ops = n1 + 2 * n2
        budget = 1.0 - (1.0 - pl) ** max(total_ops, 1)
        self.io.writeln(f"  logical: {lm['code']} d={d}  p_L={pl:.2e}/op  "
                        f"{surgery} surgery ops ({n2} CX-class)  "
                        f"{n_t} T (distillation required)")
        self.io.writeln(f"  logical: ~{rounds} syndrome rounds "
                        f"(~{rounds:.0f} us at 1 us/round), "
                        f"{phys:,} physical qubits "
                        f"({n} patches{' + 1 routing ancilla' if n2 else ''})")
        self.io.writeln(f"  logical: cumulative error budget = "
                        f"1-(1-p_L)^{total_ops} = {budget:.3e}")
