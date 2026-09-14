from typing import Any, override

import bascenev1
from bascenev1._dualteamsession import DualTeamSession

from server import utils
from server.clients import Client
from tournament import tournament
from tournament.manager import manager


class TournamentSession(DualTeamSession):
    """dual team session configured for tournament"""

    def __init__(self):
        super().__init__()

    @override
    def on_team_join(self, team: bascenev1.Team) -> None:
        super().on_team_join(team)
        # change the team name to their actual team name.
        team.name = manager.active_match["teams"][team.id]

    @override
    def on_player_request(self, player: bascenev1.SessionPlayer):
        client = Client(
            client_id=player.inputdevice.client_id, account_id=player.get_account_id()
        )
        if (
            manager.active_match
            and not client.account_id in manager.active_match["players"]
        ):
            # a match is active, if the player is not any of the teams of the match, dont let them join.
            client.error("A match is active. You cannot join.")
            return False

        if not client.public_uuid in manager.active_match["uuids"]:
            utils.error(
                message=f"{player.getname(full=True)}'s device uuid is changed, please contact the server admins."
            )
            client.error(
                "Your device uuid could not be verified, please contact the server admins."
            )
            return False

        return super().on_player_request(player)

    @override
    def handlemessage(self, msg: Any) -> Any:
        from bascenev1._lobby import ChangeMessage, PlayerReadyMessage

        if isinstance(msg, PlayerReadyMessage):
            player = msg.chooser.getplayer()
            if not player:
                return
            team = msg.chooser.sessionteam
            identifier = player.get_account_id()
            if team.name != manager.players[identifier][1]:
                # if this is not the team of the player, we move him into his team.
                msg.chooser.handlemessage(ChangeMessage("team", 1))
                return

            self._on_player_ready(chooser=msg.chooser)
        else:
            super().handlemessage(msg)

    @override
    def _switch_to_score_screen(self, results: bascenev1.GameResults) -> None:
        from bascenev1lib.activity.drawscore import DrawScoreScreenActivity
        from bascenev1lib.activity.dualteamscore import (
            TeamVictoryScoreScreenActivity,
        )
        from bascenev1lib.activity.multiteamvictory import (
            TeamSeriesVictoryScoreScreenActivity,
        )

        winnergroups = results.winnergroups

        # If everyone has the same score, call it a draw.
        if len(winnergroups) < 2:
            self.setactivity(bascenev1.newactivity(DrawScoreScreenActivity))
        else:
            winner = winnergroups[0].teams[0]
            loser = winnergroups[1].teams[0]
            winner.customdata["score"] += 1

            if not hasattr(winner, "score"):
                winner.score = 0

            winner.score += 1

            # If a team has won, show final victory screen.
            if winner.customdata["score"] >= (self._series_length - 1) / 2 + 1:
                if not hasattr(winner, "series"):
                    winner.series = 0
                winner.series += 1
                self.setactivity(
                    bascenev1.newactivity(
                        TeamSeriesVictoryScoreScreenActivity,
                        {"winner": winner},
                    )
                )

                if winner.series >= tournament.series_length:
                    if not hasattr(loser, "score"):
                        loser.score = 0
                    if not hasattr(loser, "series"):
                        loser.series = 0

                    utils.success(
                        message=f"Match concluded. Winner: {winner.name}, Loser: {loser.name}\nResults are announced in discord.\nServer will restart in 10 seconds."
                    )
                    manager.conclude_active_match(winner, loser)
            else:
                self.setactivity(
                    bascenev1.newactivity(
                        TeamVictoryScoreScreenActivity, {"winner": winner}
                    )
                )
