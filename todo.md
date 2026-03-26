# QBASIC — Cure List

1. Complete parse-layer migration: make `_exec_line` handle all typed `Stmt` objects without falling through to legacy regex path.
2. Eliminate the dual variable system fully. Remove all remaining `run_vars[x] = val; self.variables[x] = val` pairs — Scope handles both writes.
3. Make control-flow return types uniform across all handlers.
4. Remove remaining side effects from parsing helpers.
5. Define a minimal internal instruction set (typed opcodes replacing raw strings in the execution loop).
6. Unify subroutine expansion with the execution model.
7. Wire `QiskitBackend`/`LOCCRegBackend` into execution (replace direct `qc.*` calls).
8. Unify LOCC and non-LOCC execution paths at the instruction level.
9. Eliminate the dual gate-application paths (`_apply_gate` vs `_locc_apply_gate`).
10. Consolidate immediate execution and program execution (`run_immediate` and `cmd_run`).
11. Make measurement semantics explicit and consistent.
12. Reduce mixin state coupling.
13. Add a validation phase before execution.
14. Ensure deterministic program execution ordering.
15. Cache transpiled Qiskit circuits.
16. Optimize LOCC SEND mode.
17. Mock the Qiskit simulation backend in the test suite.
