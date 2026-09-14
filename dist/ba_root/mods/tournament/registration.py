from server.enums import TeamStatus
from server.storage import Storage
from tournament.storage import SEASONS_DIR
from secrets import randbelow


class Registration(Storage):
    """storage class for registration"""

    def __init__(self, season_id: str):
        super().__init__("registrations.json", SEASONS_DIR / season_id)
        self.bootstrap()

    def bootstrap(self):
        """creates the file if not already existing."""
        if not self.path.exists():
            data = {"teams": {}, "players": {}, "codes": {}}
            self.commit(data)

    def is_registered(self, id: str) -> bool:
        """returns whether the discord user is already registered?"""
        db = self.read()
        players = db.get("players", {})
        return id in players

    def register(
        self,
        team_name: str,
        captain_discord_id: str,
        captain_code: str,
        invited_members: list = [],
    ):
        """registers a team/solo in database."""
        size = len(invited_members) + 1
        if self.is_registered(captain_discord_id) or any(
            self.is_registered(discord_id) for discord_id in invited_members
        ):
            # if any of them is registered, decline it.
            return

        db = self.read()
        # team_id = f"team-{len(db['teams']) + 1}"
        # we use team-name as team-id
        team_id = team_name

        captain = {
            "account_id": "",
            "device_uuid": "",
            "discord_id": captain_discord_id,
            "code": captain_code,
        }
        db["players"][captain_discord_id] = team_id
        db["codes"][captain_code] = captain_discord_id

        members = [captain]
        for discord_id in invited_members:
            members.append(
                {
                    "account_id": "",
                    "device_uuid": "",
                    "discord_id": discord_id,
                    "code": "",
                }
            )
            db["players"][discord_id] = team_id

        # saving in players dict will help us do team lookup and verification much faster.
        db["teams"][team_id] = {
            "id": team_id,
            "captain": captain_discord_id,
            "status": TeamStatus.IN_INVITATION if size > 1 else TeamStatus.UNVERIFIED,
            "members": members,
        }
        self.commit(db)
        return team_id

    def delete(self, team_id: str) -> str:
        """deletes the team when someone declines the invitation."""
        db = self.read()
        team = db["teams"].get(team_id)

        for member in team["members"]:
            account_id = member["account_id"]
            if account_id in db["players"]:
                del db["players"][account_id]
            discord_id = member["discord_id"]
            if discord_id in db["players"]:
                del db["players"][discord_id]
            code = member["code"]
            if code in db["codes"]:
                del db["codes"][code]

        captain = team["captain"]
        del db["teams"][team_id]
        self.commit(db)
        return captain

    def generate_code(self) -> str:
        """generates a code for the registration."""
        db = self.read()
        code = f"{randbelow(1_000_000):06d}"
        if code in db["codes"]:
            return self.generate_code()
        return code

    def accept(self, discord_id: str, code: str) -> bool:
        """accepts invitation from a team."""
        db = self.read()
        # lookup team id from players map
        team_id = db["players"].get(discord_id)
        if not team_id:
            return False

        team = db["teams"].get(team_id)

        for member in team["members"]:
            if member["discord_id"] == discord_id:
                member["code"] = code

                # update in codes map
                db["codes"][code] = discord_id

                # check if everyone on the team has accepted the invitation.
                if all(m["code"] for m in team["members"]):
                    # update the team status
                    team["status"] = TeamStatus.UNVERIFIED

                self.commit(db)
                return True
        return False

    def verify(self, code: str, account_id: str, device_uuid: str) -> bool | None:
        """verifies the player"""
        db = self.read()
        discord_id = db["codes"].get(code)
        if not discord_id:
            return None
        team_id = db["players"].get(discord_id)
        if not team_id:
            return False

        team = db["teams"].get(team_id)

        for member in team["members"]:
            if member["discord_id"] == discord_id:
                # case: the guy is already verified
                if member["account_id"]:
                    return None
                member["device_uuid"] = device_uuid
                member["account_id"] = account_id

                # save in players map for avoiding duplications.
                db["players"][account_id] = team_id

                # check if everyone on the team has verified.
                if all(m["account_id"] for m in team["members"]):
                    # update the team status
                    team["status"] = TeamStatus.VERIFIED

                self.commit(db)
                return True
        return False

    def change_uuid(self, discord_id: str, new_uuid: str) -> bool:
        """changes the uuid of a player"""
        db = self.read()
        team_id = db["players"].get(discord_id)
        if not team_id:
            return False

        team = db["teams"].get(team_id)

        for member in team["members"]:
            if member["discord_id"] == discord_id:
                member["device_uuid"] = new_uuid
                self.commit(db)
                return True
        return False
