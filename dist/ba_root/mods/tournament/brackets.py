"""storage for brackets"""

from pathlib import Path

from server.enums import Status
from server.storage import Storage
from tournament.storage import SEASONS_DIR
from tournament.registration import Registration
from tournament.graphics import runner


class Brackets(Storage):
    """generates brackets and handles the rounds."""

    def __init__(self, season_id: str):
        super().__init__("brackets.json", SEASONS_DIR / season_id)
        self.season_id = season_id
        self.group_stage_path = self.directory / "rounds" / "group-stage.json"
        self.group_stage_path.parent.mkdir(parents=True, exist_ok=True)
        self.bootstrap()

    def bootstrap(self):
        """creates the file and setups up method"""
        self.registration = Registration(self.season_id)
        if not self.path.exists():
            database = {
                "active_round": "",
                "total_rounds": 0,
            }
            self.commit(database)

    def generate_group_stage(self, teams: list) -> None | bool:
        """generates the group stage brackets."""
        # TODO: make it more dynamically syncing with real logic.
        # we assume that the total number of teams is even.
        teams_count = len(teams)
        groups_count = (teams_count & -teams_count) // 2 # for now.

        # ah we dont want the groups to be only two, round-robin will make it longer otherwise or the teams count is less than 4
        assert groups_count >= 4
        if groups_count == teams_count:
            # the number is power of 2 value
            # we go straight to the main stage
            self.generate_main_stage(teams=teams)
            return

        # mhm.. groups are needed now.
        groups = {}
        main_stage_capacity = 1 << (teams_count.bit_length() - 1)
        teams_per_group = teams_count // groups_count

        # calculates the number of winning teams needed out of each group
        winning_teams_per_group = main_stage_capacity // groups_count // 2

        for index in range(groups_count):
            group_key = f"group_{index + 1}"
            groups[group_key] = {
                "rounds": self.generate_round_robin(
                    teams[index * teams_per_group : (index + 1) * teams_per_group],
                    count=teams_per_group,
                    group_key=group_key,
                ),
                "standings": [],
                "standings_sorted": []
            }
            # fill up the standings.
            self.recalculate_group_standings(groups[group_key])

        # we have the rounds of each group now.
        # let's save them into their database file.
        database = {
            "status": Status.IN_PROGRESS,
            "groups": groups,
            "winning_teams_per_group": winning_teams_per_group,
        }

        self.commit(data=database, external_path=self.group_stage_path)

        # also update it in brackets.json that groupstage is active;
        brackets = self.read()
        brackets["active_round"] = "group-stage"
        brackets["total_rounds"] += 1
        self.commit(brackets)

        return True

    def generate_round_robin(self, teams: list, count: int, group_key: str) -> dict:
        """generates rounds robin for teams."""
        rounds = {}

        # if the teams count is odd.. we can add an empty team and then remove it while making rounds.
        if count % 2 != 0:
            teams = teams + [None]
            count += 1

        for round in range(1, count):
            round_matches = {}
            # for each round.
            for i in range(count // 2):
                first = teams[i]  # first in sense of next front.
                last = teams[count - 1 - i]  # last in sense of previous back.

                match = self.create_match_format(team1=first, team2=last, group_key=group_key, round_key=f"round {round}")

                # if one of them is None, we give them BYEs.
                if first is None or last is None:
                    match["status"] = Status.COMPLETED
                    match["winner"] = first if last is None else last
                    match["loser"] = None

                round_matches[f"m{i + 1}"] = match

            rounds[f"round {round}"] = {
                "matches": round_matches,
                "status": Status.IN_PROGRESS if round == 1 else Status.PENDING,
            }

            # shuffle it so the teams dont get matched up with the same team twice.
            teams = [teams[0]] + [teams[-1]] + teams[1:-1]
        return rounds

    def update_gs_match(
        self, group_key: str, round_key: str, match_key: str, score1: int, score2: int, series1: int, series2: int
    ):
        """updates the match of the group round."""
        gs = self.read(external_path=self.group_stage_path)
        group = gs["groups"][group_key]
        round = group["rounds"][round_key]
        match = round["matches"][match_key]

        if series1 > series2:
            match["winner"] = match["team1"]
            match["loser"] = match["team2"]
        else:
            match["winner"] = match["team2"]
            match["loser"] = match["team1"]

        match["score1"] = score1
        match["score2"] = score2
        match["status"] = Status.COMPLETED

        # all the matches of same round across all the groups
        all_groups_round_completed = all(
            m["status"] == Status.COMPLETED
            for g in gs["groups"].values()
            for m in g["rounds"][round_key]["matches"].values()
        )

        # lets check if the round of all groups is completed.
        if all_groups_round_completed:
            # all matches are completed.
            next_round_key = f"round {int(round_key.split()[1]) + 1}"

            for g in gs["groups"].values():
                if round_key in g["rounds"]:
                    g["rounds"][round_key]["status"] = Status.COMPLETED

                if next_round_key in g["rounds"]:
                    # if a next round exists, turn it on.
                    g["rounds"][next_round_key]["status"] = Status.IN_PROGRESS

        # recalculate the standings
        self.recalculate_group_standings(group=group)

        # check if the whole groupstage is completed.
        if all(
            round["status"] == Status.COMPLETED
            for g in gs["groups"].values()
            for round in g["rounds"].values()
        ):
            # groupstage is completed.
            gs["status"] = Status.COMPLETED

            # commit now because main stage will check the status of the groupstage.
            self.commit(gs, external_path=self.group_stage_path)
            self.send_groupstage_brackets()
            self.send_group_stage_standings()
            # load the main stage.
            self.generate_main_stage()
            return

        self.commit(gs, external_path=self.group_stage_path)
        self.send_groupstage_brackets()
        self.send_group_stage_standings()

    def update_ms_match(self, match_key: str, score1: int, score2: int, series1: int, series2: int):
        """updates the match of the main-stage."""
        current_round_path = self.get_active_round_path()
        current_round_data = self.read(current_round_path)

        match = current_round_data["matches"][match_key]

        if series1 > series2:
            match["winner"] = match["team1"]
            match["loser"] = match["team2"]
        else:
            match["winner"] = match["team2"]
            match["loser"] = match["team1"]

        match["score1"] = score1
        match["score2"] = score2
        match["status"] = Status.COMPLETED

        if all(
            match["status"] == Status.COMPLETED
            for match in current_round_data["matches"].values()
        ):
            # all matches are completed.
            current_round_data["status"] = Status.COMPLETED
            # commit now because next round will check the status of the current round.
            self.commit(current_round_data, external_path=current_round_path)
            self.send_mainstage_brackets()
            # load the next round only if finals has not been completed.
            if current_round_path.name == "finals.json":
                self.announce_tournament_completion()
                return
            self.generate_ms_next_round()
            return

        self.commit(current_round_data, external_path=current_round_path)
        self.send_mainstage_brackets()

    def recalculate_group_standings(self, group: dict) -> None:
        """recalculates the group standings based on:
        1. points
        2. diff
        3. rounds won."""
        stats = {}
        for round in group["rounds"].values():
            for match in round["matches"].values():
                # add to stats
                for team_id in (match["team1"], match["team2"]):
                    if team_id and team_id not in stats:
                        stats[team_id] = {
                            "id": team_id,
                            "wins": 0,
                            "loses": 0,
                            "points": 0,
                            "diff": 0,
                            "rounds_won": 0,
                            "rounds_lost": 0,
                        }

        # we put and calculate stats of the completed matches only.
        for round in group["rounds"].values():
            for match in round["matches"].values():
                if match["status"] != Status.COMPLETED:
                    continue

                if match["team1"] is None or match["team2"] is None:
                    continue
                t1 = match["team1"]
                t2 = match["team2"]
                s1, s2 = match["score1"], match["score2"]

                stats[t1]["rounds_won"] += s1
                stats[t1]["rounds_lost"] += s2
                stats[t2]["rounds_won"] += s2
                stats[t2]["rounds_lost"] += s1

                if match["winner"] == match["team1"]:
                    stats[t1]["wins"] += 1
                    stats[t2]["loses"] += 1
                else:
                    stats[t1]["loses"] += 1
                    stats[t2]["wins"] += 1

        # diff is tiebreaker.
        for team in stats.values():
            team["diff"] = team["rounds_won"] - team["rounds_lost"]
            team["points"] = team["wins"] * 3 - team["loses"]

        sorted_teams = sorted(
            stats.values(),
            key=lambda x: (x["points"], x["diff"], x["rounds_won"]),
            reverse=True,
        )

        group["standings"] = [team["id"] for team in sorted_teams]
        # this will come in help for showing the stats on leaderboard.
        group["standings_sorted"] = sorted_teams

    def send_group_stage_standings(self) -> None:
        """sends the group stage standings to discord webhook."""
        data = {
            "type": "group-standings",
            "season_id": self.season_id,
        }

        runner.run(data=data)

    def generate_first_round(
        self, teams: dict | list, winning_teams_per_group: int = 0
    ) -> dict:
        "generate first round of the main-stage."
        pairings = []
        if isinstance(teams, list):
            # there was no group stage before main-stage.
            import random

            shuffled_teams = teams.copy()
            random.shuffle(shuffled_teams)

            # make the pairings.
            for i in range(0, len(teams), 2):
                pairings.append((shuffled_teams[i], shuffled_teams[i + 1]))

        else:
            # there was a group stage.. so the teams dict is actually the dict of groups.
            # groups = teams
            groups_keys = list(teams.keys())
            groups_count = len(groups_keys)
            offset = groups_count // 2

            for i in range(groups_count):
                front_group = groups_keys[i]
                back_group = groups_keys[(i + offset) % groups_count]

                for index in range(winning_teams_per_group // 2):
                    team1 = teams[front_group]["standings"][index]
                    team2 = teams[back_group]["standings"][
                        winning_teams_per_group - 1 - index
                    ]
                    pairings.append((team1, team2))

        # we have the pairings now.
        matches = {}
        for index, (t1, t2) in enumerate(pairings, start=1):
            matches[f"m{index}"] = self.create_match_format(team1=t1, team2=t2)

        return {"matches": matches, "status": Status.IN_PROGRESS}

    def generate_main_stage(self, teams: dict = []):
        """generates the main stage"""
        brackets = self.read()

        if teams:
            # there was no group stage before us.
            round_data = self.generate_first_round(teams)
        else:
            # there was a group stage before us.
            # to make the match to be fair, we will shuffle them first to last; like we did for group-stage matches
            # but only once per team.
            gs = self.read(external_path=self.group_stage_path)
            round_data = self.generate_first_round(
                gs["groups"], gs["winning_teams_per_group"]
            )

        round_name = self.get_round_name(len(round_data["matches"]) * 2)
        brackets["total_rounds"] += 1
        brackets["active_round"] = round_name
        self.commit(brackets)
        file_path = self.get_active_round_path()
        self.commit(round_data, external_path=file_path)

        # send the brackets to discord.
        self.send_mainstage_brackets()

    def generate_ms_next_round(self):
        """generates the next rounds of main-stage"""
        brackets = self.read()
        current_round_path = self.get_active_round_path()
        current_round_data = self.read(current_round_path)
        if current_round_data["status"] != Status.COMPLETED:
            # the round did not complete. we cannot generate the next.
            return

        matches_data = current_round_data["matches"]
        next_matches = {}

        winners = [match["winner"] for match in matches_data.values()]

        if len(winners) == 2:
            # we just finished semi-finals.
            # finals has two matches.. first is for 1st/2nd position between semi-finals winners
            # second is for 3rd position between semi-finals losers
            losers = [match["loser"] for match in matches_data.values()]

            next_matches["FINALS"] = self.create_match_format(
                team1=winners[0], team2=winners[1]
            )
            next_matches["THIRD_PLACE"] = self.create_match_format(
                team1=losers[0], team2=losers[1]
            )

        else:
            # standard rounds.
            match_count = 1
            for i in range(0, len(winners), 2):
                next_matches[f"m{match_count}"] = self.create_match_format(
                    team1=winners[i], team2=winners[i + 1]
                )
                match_count += 1

        next_round_data = {"matches": next_matches, "status": Status.IN_PROGRESS}
        next_round_name = self.get_round_name(len(winners))
        brackets["active_round"] = next_round_name
        brackets["total_rounds"] += 1
        self.commit(brackets)
        next_round_path = self.get_active_round_path()
        self.commit(next_round_data, next_round_path)

    def announce_tournament_completion(self) -> None:
        """announces the tournament completion."""
        from tournament import tournament

        db = tournament.read()
        db.active_season = "0"
        tournament.commit(db)

        # TODO: announce completion with winners.

    def announce_match_start(self, team1: str, team2: str) -> None:
        """announces the match start in discord."""
        from tournament import tournament
        data = {
            "type": "match-announcement",
            "season_id": self.season_id,
            "participant_role_id": tournament.get_season(self.season_id).participant_role_id,
            "team1": team1,
            "team2": team2,
        }
        runner.run(data=data)

    def send_mainstage_brackets(self) -> None:
        """sends the mainstage brackets."""
        data = {
            "type": "main-stage",
            "season_id": self.season_id,
        }
        runner.run(data=data)

    def send_groupstage_brackets(self) -> None:
        """ sends groupstage brackets with webhooks."""
        data = {
            "type": "group-stage",
            "season_id": self.season_id,
        }
        runner.run(data=data)

    def send_results(
        self,
        winner: str,
        team1: str,
        team2: str,
        score1: int,
        score2: int,
        series1: int,
        series2: int,
        key: str,
    ) -> None:
        details = {
            "team1": team1,
            "team2": team2,
            "winner": winner,
            "score1": score1,
            "score2": score2,
            "series1": series1,
            "series2": series2,
            "key": key,
            "season_id": self.season_id,
        }
        data = {
            "type": "results",
            "details": details,
            "season_id": self.season_id,
        }
        runner.run(data=data)

    def send_players_dashboard(self) -> None:
        """sends the players dashboard."""
        data = {
            "type": "player-standings",
            "season_id": self.season_id,
        }
        runner.run(data=data)

    def get_active_round_path(self) -> Path:
        """returns the active round path."""
        brackets = self.read()
        return (self.directory / "rounds" / brackets["active_round"]).with_suffix(
            ".json"
        )

    def list_matches(self) -> dict:
        """ returns the list of all the matches in active round."""
        round_path = self.get_active_round_path()
        round_data = self.read(round_path)
        if not round_data:
            return {} # no active round.

        matches = {}

        # if the round is groupstage;
        if round_path.name == "group-stage.json":
            for g_key, group in round_data["groups"].items():
                for r_key, round in group["rounds"].items():
                    if round["status"] == Status.IN_PROGRESS:
                        for m_key, match in round["matches"].items():
                            composite_key = f"{g_key}-{r_key}-{m_key}"
                            matches[composite_key] = match
        else:
            matches.update(round_data["matches"])

        return matches

    def give_win_to_team(self, match_index: int, team_index: int, force: bool = False) -> str:
        """gives the win to the team."""
        if team_index not in (1, 2):
            return "Team index must be either 1 or 2."
        matches = self.list_matches()
        if not matches:
            return "No active round."

        match_keys = list(matches.keys())
        if match_index < 1 or match_index > len(match_keys):
            return f"Invalid match index. Must be between 1 and {len(match_keys)}."

        match_key = match_keys[match_index - 1]

        if match_key not in matches:
            return "No such match."

        match = matches[match_key]
        if match["status"] != Status.COMPLETED or force:
            from tournament import tournament
            series_length = tournament.series_length
            # update the team's score by 1
            series1, series2 = 0, 0
            if team_index == 1:
                team = match["team1"]
                match["score1"] = series_length * 4
                series1 = series_length
            else:
                team = match["team2"]
                match["score2"] = series_length * 4
                series2 = series_length
            
            if match["group_key"]:
                # its a group stage match.
                real_match_key = match_key.split("-")[-1]
                self.update_gs_match(
                    group_key=match["group_key"],
                    round_key=match["round_key"],
                    match_key=real_match_key,
                    score1=match["score1"],
                    score2=match["score2"],
                    series1=series1,
                    series2=series2,
                )
            else:
                # its a main stage match.
                self.update_ms_match(
                    match_key=match_key, score1=match["score1"], score2=match["score2"], series1=series1, series2=series2
                )

            # and now we can send the results to discord.
            self.send_results(team, match["team1"], match["team2"], match["score1"], match["score2"], series1, series2, match_key)
            self.send_players_dashboard()
            return f"Given {team} win."
        return "Match is already completed"

    def get_round_name(self, count: int) -> str:
        """returns the round-name by teams-count"""
        if count >= 16:
            return f"round-of-{count}"
        elif count == 8:
            return "quarter-finals"
        elif count == 4:
            return "semi-finals"
        else:
            return "finals"

    def get_team(self, team_id: str) -> dict:
        """returns the full team information dict."""
        return self.registration.read()["teams"][team_id]

    def create_match_format(
        self,
        team1: str,
        team2: str,
        group_key: str | None = None,
        round_key: str | None = None,
    ) -> dict:
        """match format."""
        return {
            "team1": team1,
            "team2": team2,
            "score1": 0,
            "score2": 0,
            "winner": None,
            "loser": None,
            "group_key": group_key,
            "round_key": round_key,
            "status": Status.PENDING,
        }
