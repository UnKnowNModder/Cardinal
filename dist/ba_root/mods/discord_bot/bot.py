"""bot.py for discord bot functionality."""

import logging

import discord
from discord import Activity, ActivityType, Intents, Interaction, app_commands
from discord.ext import commands
import asyncio
from discord_bot.client import GameClient
from discord_bot.ui import (
    CaptainRegistrationModal,
    TeamInvitationView,
    SoloRegistrationModal,
)
from traceback import format_exc
from roles import roles
from server import config
from server.enums import Authority, Role, SeriesType, TournamentType
from tournament import tournament
from tournament.schema import SeasonSchema


class DiscordBot(commands.Bot):
    def __init__(self) -> None:
        intents = Intents.default()
        intents.members = True
        super().__init__(
            command_prefix=[],
            intents=intents,
            owner_id=config.discord.owner_id,
        )

    async def setup_hook(self) -> None:
        self.add_view(TeamInvitationView("9999"))
        self.tree.on_error = self.on_app_cmd_error
        await self.add_cog(GeneralCommands(self))
        await self.add_cog(TournamentCommands(self))

    async def on_app_cmd_error(
        self, interaction: Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.CheckFailure):
            return
        print(f"Discord: An error occurred while executing the command: {format_exc()}")

    async def on_ready(self):
        """the bot is ready"""
        print(f"Discord: logged in as {self.user}")

        # change presence and sync slash commands.
        await self.change_presence(
            activity=Activity(type=ActivityType.listening, name="Zzzzzz....")
        )
        for guild in self.guilds:
            self.tree.clear_commands(guild=guild)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)


def require(authority: Authority):
    """decorator for authority check"""

    async def examine(interaction: Interaction) -> bool:
        if interaction.user.id == interaction.client.owner_id:
            return True

        if roles.get_authority_level(interaction.user.id) >= authority:
            return True

        await interaction.response.send_message(
            "You are not authorised", ephemeral=True
        )
        return False

    return app_commands.check(examine)


class GeneralCommands(commands.Cog):
    """cog for slash commands"""

    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.client = GameClient()

    @app_commands.command(name="say")
    @app_commands.describe(message="The text to send")
    @require(Authority.ADMIN)
    async def say(self, interaction: Interaction, message: str) -> None:
        """sends message in game chat"""
        self.client.send_action(
            action="message", text=message, sender=interaction.user.display_name
        )
        await interaction.response.send_message("Done!", ephemeral=True)

    @app_commands.command(name="cmd")
    @app_commands.describe(command="The chat-command to execute")
    async def cmd(self, interaction: Interaction, command: str) -> None:
        """executes a chat command in game."""
        self.client.send_action(
            action="command", command=command, account_id=interaction.user.id
        )
        await interaction.response.send_message("Done!", ephemeral=True)

    @app_commands.command(name="list")
    async def list(self, interaction: Interaction) -> None:
        """lists all the players from game"""
        await interaction.response.defer(ephemeral=True)
        response = await self.client.send_action(action="list", response=True)

        if not response["players"]:
            await interaction.followup.send("There are no players in the server")
            return

        heads = "{0:^16}{1:^15}\n"
        result = ""
        for player in response["players"]:
            result += heads.format(player["name"], player["client_id"])

        await interaction.followup.send(result)

    @app_commands.command(name="admin")
    @app_commands.describe(user="the user to add/remove")
    @require(Authority.LEADER)
    async def admin(self, interaction: Interaction, user: discord.Member) -> None:
        """to add/remove a user to admins"""
        if roles.has_role(Role.ADMIN, user.id):
            roles.remove(Role.ADMIN, user.id)
            await interaction.response.send_message(
                f"{user.name} has been removed from admins", ephemeral=True
            )
        else:
            roles.add(Role.ADMIN, user.id)
            await interaction.response.send_message(
                f"{user.name} has been added to admins", ephemeral=True
            )

    @app_commands.command(name="owner")
    @app_commands.describe(user="the user to add/remove")
    @require(Authority.HOST)
    async def owner(self, interaction: Interaction, user: discord.Member) -> None:
        """to add/remove a user to owners"""
        if roles.has_role(Role.LEADER, user.id):
            roles.remove(Role.LEADER, user.id)
            await interaction.response.send_message(
                f"{user.name} has been removed from owners", ephemeral=True
            )
        else:
            roles.add(Role.LEADER, user.id)
            await interaction.response.send_message(
                f"{user.name} has been added to owners", ephemeral=True
            )

class TournamentCommands(
    commands.GroupCog,
    group_name="tournament",
    group_description="Commands to manage tournaments.",
):
    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(name="create")
    @app_commands.describe(type="Tournament Type", series="Series Type")
    @require(authority=Authority.LEADER)
    async def create_season(
        self, interaction: Interaction, type: TournamentType, series: SeriesType
    ) -> None:
        """creates a tournament season"""
        if int(tournament.active_season):
            await interaction.response.send_message(
                "Cannot create! a season is going on."
            )
            return

        from datetime import datetime, timedelta, timezone

        ist = timezone(timedelta(hours=5, minutes=30))

        schema = SeasonSchema(
            series=series, type=type, created_at=datetime.now(ist).isoformat()
        )
        tournament.create_season(schema=schema)
        await interaction.response.send_message(
            f"The {type.lower()} season has been created with series: {series.lower()}"
        )
        # make the participant role if it doesn't exist.
        if not discord.utils.get(interaction.guild.roles, name="Participant"):
            await interaction.guild.create_role(
                name="Participant", mentionable=True,
            )

    @app_commands.command(name="register")
    async def register(self, interaction: Interaction) -> None:
        """registers a player to the tournament"""
        season_id = tournament.active_season
        if not int(season_id):
            await interaction.response.send_message(
                "There is no tournament season opened currently.", ephemeral=True
            )
            return

        if not tournament.are_registrations_open:
            await interaction.response.send_message(
                "Registrations have been closed", ephemeral=True
            )
            return

        season_data = tournament.get_season(season_id=season_id)
        size = season_data.type.count
        if size > 1:
            # for not-solo seasons
            await interaction.response.send_modal(
                CaptainRegistrationModal(season_id=season_id, size=size - 1)
            )
        else:
            # for solo seasons
            await interaction.response.send_modal(SoloRegistrationModal(season_id=season_id))

    @app_commands.command(name="registrations")
    @app_commands.describe(option="Open or close the registrations")
    @require(Authority.LEADER)
    async def registrations(self, interaction: Interaction, option: bool) -> None:
        """open/close the registrations"""
        if option:
            if tournament.are_registrations_open:
                await interaction.response.send_message(
                    "Cannot open the registrations! they are already open.",
                    ephemeral=True,
                )
                return
            tournament.open_registrations()
        else:
            if not tournament.are_registrations_open:
                await interaction.response.send_message(
                    "Cannot close the registrations! they are already closed.",
                    ephemeral=True,
                )
                return
            tournament.close_registrations()

        await interaction.response.send_message(
            f"{'Opened' if option else 'closed'} the registrations."
        )

    @app_commands.command(name="uuid")
    @require(Authority.LEADER)
    async def change_uuid(
        self, interaction: Interaction, user: discord.Member, uuid: str
    ) -> None:
        """changes the uuid of the registered player"""
        if not int(tournament.active_season):
            await interaction.response.send_message(
                "There is no tournament season opened currently.", ephemeral=True
            )
            return

        from tournament.registration import Registration

        registration = Registration(season_id=tournament.active_season)
        if not registration.is_registered(str(user.id)):
            await interaction.response.send_message(
                "He is not registered.", ephemeral=True
            )
            return

        registration.change_uuid(discord_id=str(user.id), new_uuid=uuid)
        await interaction.response.send_message(
            f"Changed the uuid of {user.mention}'s account."
        )

    @app_commands.command(name="win")
    @require(Authority.LEADER)
    async def give_win(self, interaction: Interaction, match_index: int, team_index: int) -> None:
        """ gives win to the team"""
        if not int(tournament.active_season):
            await interaction.response.send_message(
                "There is no tournament season opened currently.", ephemeral=True
            )
            return

        from tournament.brackets import Brackets
        brackets = Brackets(season_id=tournament.active_season)
        response = brackets.give_win_to_team(match_index=match_index, team_index=team_index)
        await interaction.response.send_message(response, ephemeral=True)

    @app_commands.command(name="list")
    @require(Authority.LEADER)
    async def list_matches(self, interaction: Interaction) -> None:
        """lists all the matches in active round."""
        from tournament.brackets import Brackets
        brackets = Brackets(season_id=tournament.active_season)
        matches = brackets.list_matches()
        if not matches:
            await interaction.response.send_message("There are no matches in the round.")
            return

        lines = ["**Round matches:**\n"]

        for match_index, (key, match) in enumerate(matches.items(), start=1):
            team1 = match["team1"] or "BYE"
            team2 = match["team2"] or "BYE"
            status = match["status"]

            line = (
                f"`Match #{match_index}` | "
                f"**(1)** `{team1}` vs **(2)** `{team2}` | "
                f"Status: `{status}`"
            )
            lines.append(line)

        message_text = "\n".join(lines)
        await interaction.response.send_message(message_text, ephemeral=True)

    
    @app_commands.command(name="start")
    @require(Authority.LEADER)
    async def start_tournament(self, interaction: Interaction) -> None:
        """starts the tournament"""
        if not int(tournament.active_season):
            await interaction.response.send_message(
                "There is no tournament season opened currently.", ephemeral=True
            )
            return

        if tournament.are_registrations_open:
            await interaction.response.send_message(
                "Cannot start the tournament! registrations are still open.",
                ephemeral=True,
            )
            return

        from tournament.brackets import Brackets

        brackets = Brackets(season_id=tournament.active_season)
        if brackets.read()["active_round"]:
            await interaction.response.send_message(
                "The tournament is already started.",
                ephemeral=True,
            )
            return
        from tournament.registration import Registration
        await interaction.response.defer(ephemeral=True)

        # we need to generate the brackets.
        registration = Registration(season_id=brackets.season_id).read()
        teams = list(registration["teams"].keys())
        try:
            brackets.generate_group_stage(teams=teams)
        except AssertionError:
            await interaction.followup.send(
                "The number of teams are either less than 4 or not divisible by 4. The tournament cannot be started.",
                ephemeral=True,
            )
            return
        await interaction.followup.send(
            "The tournament has been started!", ephemeral=True
        )
        await asyncio.sleep(30)
        pings = "These are the registered players:\n"
        for team in teams:
            pings += f"{team}: <@{registration['teams'][team]['captain']}>\n"

        await interaction.followup.send(pings)


if __name__ == "__main__":
    bot = DiscordBot()
    bot.run(token=config.discord.token, log_level=logging.WARNING)
