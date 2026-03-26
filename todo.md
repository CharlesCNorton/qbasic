# QBASIC — Cure List

1. Wire `_exec_line` to dispatch on typed `Stmt` objects instead of raw strings.
2. Remove repeated string splitting and re-tokenization during execution.
3. Separate parsing from execution completely. `_exec_line` must operate only on parsed objects.
4. Fix `_substitute_vars` to use parsed representations.
5. Centralize execution state into `ExecContext`. Wire it through `build_circuit`, `_exec_line`, and all control-flow helpers.
6. Eliminate the dual variable system. Wire `Scope` into execution, replacing `self.variables`/`run_vars` pairs.
7. Make control-flow and statement-execution return types uniform.
8. Normalize the statement handler interface. Replace lambda-based `_stmt_handlers` with uniform callables.
9. Define and enforce a clear order of statement evaluation.
10. Remove side effects from parsing helpers.
11. Define a minimal internal instruction set.
12. Unify subroutine expansion with the execution model.
13. Replace implicit recursion limits with structured call tracking.
14. Formalize qubit addressing and register resolution.
15. Wire `QiskitBackend`/`LOCCRegBackend` into execution.
16. Unify LOCC and non-LOCC execution paths at the instruction level.
17. Eliminate the dual gate-application paths.
18. Consolidate immediate execution and program execution.
19. Make measurement semantics explicit and consistent.
20. Reduce mixin state coupling.
21. Eliminate silent fallbacks and implicit behavior.
22. Add a validation phase before execution.
23. Ensure deterministic program execution ordering.
24. Generate `cmd_help` output from the command registry.
25. Cache transpiled Qiskit circuits.
26. Optimize LOCC SEND mode.
27. Mock the Qiskit simulation backend in the test suite.
