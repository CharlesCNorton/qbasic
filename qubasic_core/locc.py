"""QUBASIC LOCC mixin — re-exports from split modules."""

from qubasic_core.locc_commands import LOCCCommandsMixin
from qubasic_core.locc_display import LOCCDisplayMixin
from qubasic_core.locc_execution import LOCCExecutionMixin


class LOCCMixin(LOCCCommandsMixin, LOCCDisplayMixin, LOCCExecutionMixin):
    """Combined LOCC mixin — commands, display, and execution."""
    pass
