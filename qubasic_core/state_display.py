"""QUBASIC state display mixin — STATE, BLOCH, HIST, PROBS commands."""

from qubasic_core.engine import MAX_BLOCH_DISPLAY


class StateDisplayMixin:
    """State inspection commands for QBasicTerminal.

    Requires: TerminalProtocol — uses self.locc_mode, self.last_sv,
    self.last_counts, self.last_circuit, self.num_qubits,
    self._locc_state(), self._locc_bloch(),
    self._print_statevector(), self._print_probs(), self._print_bloch_single(),
    self.print_histogram(), self.io.
    """

    def cmd_state(self, rest: str = '') -> None:
        if self.locc_mode:
            return self._locc_state(rest)
        if self.last_sv is None:
            self.io.writeln("?NO STATE — RUN first")
            return
        self._print_statevector(self.last_sv)

    def cmd_hist(self) -> None:
        if self.last_counts is None:
            self.io.writeln("?NO RESULTS — RUN first")
            return
        self.print_histogram(self.last_counts)

    def cmd_probs(self) -> None:
        if self.last_sv is None:
            self.io.writeln("?NO STATE — RUN first")
            return
        self._print_probs(self.last_sv)

    def cmd_bloch(self, rest: str) -> None:
        if self.locc_mode:
            return self._locc_bloch(rest)
        if self.last_sv is None:
            self.io.writeln("?NO STATE — RUN first")
            return
        if rest:
            q = int(rest)
            self._print_bloch_single(self.last_sv, q)
        else:
            for q in range(min(self.num_qubits, MAX_BLOCH_DISPLAY)):
                self._print_bloch_single(self.last_sv, q)
                if q < min(self.num_qubits, MAX_BLOCH_DISPLAY) - 1:
                    self.io.writeln('')

    def cmd_circuit(self) -> None:
        if self.last_circuit is None:
            self.io.writeln("?NO CIRCUIT — RUN first")
            return
        try:
            self.io.writeln(self.last_circuit.draw(output='text'))
        except Exception:
            self.io.writeln(f"Circuit: {self.last_circuit.num_qubits} qubits, "
                           f"depth {self.last_circuit.depth()}, "
                           f"{self.last_circuit.size()} gates")
