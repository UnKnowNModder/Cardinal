import os

import bascenev1

from server.enums import Status
from tournament.brackets import Brackets
from tournament.webhook import Webhook


class Manager:
    """manager class for tournament matches."""

    def __init__(self):
        self.pending_matches = {}
        self.players = {}
        self.ready_players = {}

        self.active_match = None

    def initialize(self, season_id: str):
        """initializes the manager."""
        self.season_id = season_id
        self.brackets = Brackets(season_id=season_id)
        self.webhook = Webhook(season_id=season_id)
        self.load_pending_matches()

    def load_pending_matches(self):
        """load all pending matches from the database."""
        round_path = self.brackets.get_active_round_path()
        round_data = self.brackets.read(round_path)
        if not round_data:
            return

        # if the round is groupstage;
        if round_path.name == "group-stage.json":
            for g_key, group in round_data["groups"].items():
                for r_key, round in group["rounds"].items():
                    if round["status"] == Status.IN_PROGRESS:
                        for m_key, match in round["matches"].items():
                            if match["status"] == Status.PENDING:
                                self.register_pending_match(
                                    match_key=m_key,
                                    team1=match["team1"],
                                    team2=match["team2"],
                                    group_key=g_key,
                                    round_key=r_key,
                                )
        else:
            for m_key, match in round_data["matches"].items():
                if match["status"] == Status.PENDING:
                    self.register_pending_match(
                        match_key=m_key, team1=match["team1"], team2=match["team2"]
                    )

    def register_pending_match(
        self,
        match_key: str,
        team1: str,
        team2: str,
        group_key: str | None = None,
        round_key: str | None = None,
    ):
        """registers a pending match."""
        if group_key and round_key:
            # add group and round to the match key.
            key = f"{group_key}-{round_key}-{match_key}"
        else:
            key = match_key
        players1 = self.extract_from_team_players(team=team1, key="account_id")
        players2 = self.extract_from_team_players(team=team2, key="account_id")

        self.pending_matches[key] = {
            "match_key": match_key,
            "team1": team1,
            "team2": team2,
            "uuids": self.extract_from_team_players(team=team1, key="device_uuid")
            + self.extract_from_team_players(team=team2, key="device_uuid"),
            "players": players1 + players2,
            "group_key": group_key,
            "round_key": round_key,
        }

        self.ready_players[key] = set()
        for team, players in ((team1, players1), (team2, players2)):
            for player in players:
                self.players[player] = [key, team]

    def extract_from_team_players(self, team: str, key: str) -> list:
        """extracts the key from team dict players."""
        return [
            member[key] for member in self.brackets.get_team(team_id=team)["members"]
        ]

    def handle_player_ready(self, account_id: str) -> dict:
        """handles the player ready event."""
        match_key = self.players.get(account_id, [None, None])[0]
        if not match_key:
            return {
                "status": "error",
                "message": "You are not registered for any matches.",
            }

        # if a match is already active, we cannot accept the player.
        if self.active_match:
            return {"status": "error", "message": "A match is already active."}

        if account_id in self.ready_players.get(match_key, set()):
            return {"status": "error", "message": "You are already ready."}

        self.ready_players[match_key].add(account_id)
        match = self.pending_matches[match_key]

        # if all players of a match are ready, we can start the match.
        if self.ready_players[match_key] == set(match["players"]):
            self.active_match = {
                "match_key": match["match_key"],
                "players": match["players"],
                "uuids": match["uuids"],
                "teams": [match["team1"], match["team2"]],
                "group_key": match["group_key"],
                "round_key": match["round_key"],
            }
            with bascenev1.ContextRef.empty():
                bascenev1.apptimer(2.0, self.start_tournament_session)
            return {
                "status": "success",
                "message": "You have been marked as ready.",
                "start": True,
            }

        return {"status": "success", "message": "You have been marked as ready."}

    def handle_player_leave(self, account_id: str) -> None:
        """handles the player leaving."""
        match_key = self.players.get(account_id, [None, None])[0]
        if not match_key:
            return

        if self.active_match:
            return

        if account_id in self.ready_players.get(match_key, set()):
            self.ready_players[match_key].remove(account_id)

    def conclude_active_match(
        self, winner: bascenev1.SessionTeam, loser: bascenev1.SessionTeam
    ) -> None:
        """concludes the active match."""
        if not self.active_match:
            return

        if self.active_match["teams"].index(winner.name) == 0:
            score1, score2 = winner.score, loser.score
            series1, series2 = winner.series, loser.series
        else:
            score1, score2 = loser.score, winner.score
            series1, series2 = loser.series, winner.series
        match_key = self.active_match["match_key"]
        group_key = self.active_match["group_key"]
        round_key = self.active_match["round_key"]

        if group_key:
            self.brackets.update_gs_match(
                group_key=group_key,
                round_key=round_key,
                match_key=match_key,
                score1=score1,
                score2=score2,
            )
        else:
            self.brackets.update_ms_match(
                match_key=match_key, score1=score1, score2=score2
            )

        self.brackets.send_results(
            winner.name, self.active_match["teams"][0], self.active_match["teams"][1], score1, score2, series1, series2, f"{group_key}-{round_key}-{match_key}"
        )
        self.brackets.send_players_dashboard()
        self.end_tournament_session()

    def start_tournament_session(self) -> None:
        """starts the tournament session."""
        # set os env to stop server from restarting in between a match and collect player stats.
        os.environ["BA_TOURNAMENT_MATCH"] = self.season_id
        from .activity import TournamentTransitionActivity

        session = bascenev1.get_foreground_host_session()
        with session.context:
            session.setactivity(bascenev1.newactivity(TournamentTransitionActivity))

    def end_tournament_session(self) -> None:
        """ends the tournament session."""
        bascenev1.broadcastmessage("Server will restart in 10 seconds.")
        with bascenev1.ContextRef.empty():
            bascenev1.apptimer(10.0, bascenev1.app.classic.server._execute_shutdown)


manager = Manager()
