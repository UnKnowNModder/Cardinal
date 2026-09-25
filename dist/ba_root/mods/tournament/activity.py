from typing import Any, override

import bascenev1
from bascenev1._activitytypes import TransitionActivity


class TournamentTransitionActivity(TransitionActivity):
    """transition activity to swtich from one session to tournament session."""

    @override
    def end(self, results: Any = None, delay: float = 0.0, force: bool = False) -> None:
        """on the end of transition, we switch to tournament session."""
        from .session import TournamentSession

        call = bascenev1.CallStrict(bascenev1.new_host_session, TournamentSession)
        bascenev1.pushcall(call)
        bascenev1.broadcastmessage("Join your respective teams!")

class TeamSessionTransitionActivity(TransitionActivity):
    """transition activity to swtich from tournament session to team session."""

    @override
    def end(self, results: Any = None, delay: float = 0.0, force: bool = False) -> None:
        """on the end of transition, we switch to team session."""
        from bascenev1._dualteamsession import DualTeamSession

        call = bascenev1.CallStrict(bascenev1.new_host_session, DualTeamSession)
        bascenev1.pushcall(call)
