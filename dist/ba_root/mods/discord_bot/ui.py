"""ui components for discord bot."""

from __future__ import annotations

from discord import ButtonStyle, Interaction, ui
from discord.utils import get

from tournament import tournament
from tournament.registration import Registration

# solo registration modal.

class SoloRegistrationModal(ui.Modal, title="Tournament Solo Registration."):
    """asks for team name."""

    team_name = ui.TextInput(
            label="Team Name", required=True, placeholder="Enter an unique team name."
        )
    

    def __init__(self, season_id: str):
        super().__init__()
        self.season_id = season_id

    async def on_submit(self, interaction: Interaction):
        registration = Registration(self.season_id)

        if registration.is_registered(str(interaction.user.id)):
            await interaction.response.send_message(
                "You are already registered.", ephemeral=True
            )
            return

        code = registration.generate_code()
        success = registration.register(
            team_name=self.team_name.value,
            captain_discord_id=str(interaction.user.id),
            captain_code=code,
        )
        if not success:
            await interaction.response.send_message(
                "You are already registered in this season.", ephemeral=True
            )
            return

        role = get(interaction.guild.roles, name="Participant")
        await interaction.user.add_roles(role)
        await interaction.response.send_message(
            f"Registered as {interaction.user.display_name}! Join the game server and run `/verify {code}` to verify yourself. Your code is given below.",
            ephemeral=True,
        )
        await interaction.followup.send(f"```{code}```", ephemeral=True)


# registration modal for team-captain to input his  team-name and select team members.


class CaptainRegistrationModal(ui.Modal, title="Tournament Team Registration."):
    """asks for captain's account id and team's name"""

    team_name = ui.TextInput(
        label="Team Name", required=True, placeholder="Enter an unique team name."
    )

    def __init__(self, season_id: str, size: int):
        super().__init__()
        self.season_id = season_id
        self.select = ui.Label(
            text="Select your teammates",
            component=ui.UserSelect(
                placeholder=f"Select {size}", min_values=size, max_values=size
            ),
        )
        self.add_item(self.select)

    async def on_submit(self, interaction: Interaction):
        registration = Registration(self.season_id)

        # case: check if account-id is already registered
        if registration.is_registered(str(interaction.user.id)):
            await interaction.response.send_message(
                "You are already registered.", ephemeral=True
            )
            return

        invited_members = self.select.component.values
        code = registration.generate_code()

        team_id = registration.register(
            team_name=self.team_name.value,
            captain_discord_id=str(interaction.user.id),
            captain_code=code,
            invited_members=[str(member.id) for member in invited_members],
        )

        if team_id is None:
            await interaction.response.send_message(
                "The name you have chosen is already taken. Please choose a different name.",
                ephemeral=True,
            )
            return

        if not team_id:
            await interaction.response.send_message(
                "Failed to register your team! one of your teammates might already be registered.",
                ephemeral=True,
            )
            return

        role = get(interaction.guild.roles, name="Participant")
        await interaction.user.add_roles(role)

        view = TeamInvitationView(team_id=team_id)

        await interaction.channel.send(
            f"{' '.join(member.mention for member in invited_members)}, You have been invited to join the team: `{self.team_name.value}` by {interaction.user.mention}",
            view=view,
        )
        await interaction.response.send_message(
            f"Team **{self.team_name.value}** created! Invitation sent to your teammates.! Join the game server and run `/verify {code}` to verify yourself. Your code is given below.",
            ephemeral=True,
        )
        await interaction.followup.send(f"```{code}```", ephemeral=True)


# team invitation view for teammates to accept/reject


class TeamInvitationView(ui.LayoutView):
    """accept or reject the invitation"""

    def __init__(self, team_id: str):
        super().__init__(timeout=None)
        
        self.accept_button = ui.Button(
            label="Accept",
            style=ButtonStyle.success,
            custom_id=f"tiv;accept;{team_id}",
        )
        self.accept_button.callback = self.accept_btn

        self.decline_button = ui.Button(
            label="Decline",
            style=ButtonStyle.danger,
            custom_id=f"tiv;decline;{team_id}",
        )
        self.decline_button.callback = self.decline_btn

        self.container = ui.ActionRow(self.accept_button, self.decline_button)
        self.add_item(self.container)

    async def accept_btn(self, interaction: Interaction):
        season_id = tournament.active_season
        registration = Registration(season_id=season_id)
        db = registration.read()
        user_team_id = db["players"].get(str(interaction.user.id))
        team_id = interaction.data["custom_id"].split(";")[2]
        team = db["teams"].get(team_id)

        if not team:
            await interaction.response.send_message(
                "This team invitation is no longer active.", ephemeral=True
            )
            return

        if user_team_id != team_id:
            await interaction.response.send_message(
                "You are not on the invitation list for this team.", ephemeral=True
            )
            return

        if registration.is_registered(str(interaction.user.id)):
            await interaction.response.send_message(
                "You are already registered.", ephemeral=True
            )
            return

        code = registration.generate_code()

        success = registration.accept(discord_id=str(interaction.user.id), code=code)
        if not success:
            await interaction.response.send_message(
                "You are not registered in any team.", ephemeral=True
            )
            return

        role = get(interaction.guild.roles, name="Participant")
        await interaction.user.add_roles(role)
        await interaction.response.send_message(
            f"You have joined the team! Join the game server and run `/verify {code}` to verify yourself. Your code is given below.",
            ephemeral=True,
        )
        await interaction.followup.send(f"```{code}```", ephemeral=True)

    async def decline_btn(self, interaction: Interaction):
        season_id = tournament.active_season
        registration = Registration(season_id=season_id)
        db = registration.read()
        user_team_id = db["players"].get(str(interaction.user.id))
        team_id = interaction.data["custom_id"].split(";")[2]
        team = db["teams"].get(team_id)

        if not team:
            await interaction.response.send_message(
                "This team invitation is no longer active.", ephemeral=True
            )
            return

        if user_team_id != team_id:
            await interaction.response.send_message(
                "You are not on the invitation list for this team.", ephemeral=True
            )
            return

        role = get(interaction.guild.roles, name="Participant")

        # strip all the members of role.
        for member in team["members"]:
            discord_id = member["discord_id"]
            user = interaction.guild.get_member(int(discord_id))
            if user and role in user.roles:
                await user.remove_roles(role)

        # delete the team.
        captain = registration.delete(team_id=team_id)

        # disable the buttons inside the layout container
        self.accept_button.disabled = True
        self.decline_button.disabled = True

        await interaction.response.edit_message(
            f"**Invitation Declined**, {interaction.user.mention} declined the invitation for team {team_id}. CAPTAIN: <@{captain}>",
            view=self,
        )