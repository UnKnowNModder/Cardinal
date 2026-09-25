""" balances team players if needed."""
import json
from bascenev1 import get_foreground_host_session, broadcastmessage

def check_team_balance():
    """ checks if team are balanced and balances them if needed."""
    teams = get_foreground_host_session().sessionteams
    diff = len(teams[0].players) - len(teams[1].players)
    if diff % 2 != 0:
        # odd number of players, balance is impossible.
        return

    moves = abs(diff) // 2
    if diff > 0:
        # team one is larger.
        for _ in range(moves):
            player_to_move = teams[0].players.pop()
            teams[1].players.append(player_to_move)
            player_to_move.setdata(teams[1], player_to_move.character, teams[1].color, player_to_move.highlight)
            icon_info = player_to_move.get_icon_info()
            player_to_move.set_icon_info(icon_info["texture"], icon_info["tint_texture"], teams[1].color, player_to_move.highlight)
            broadcastmessage(f"shifted {player_to_move.getname()} to {json.loads(teams[1].name.as_json())['t'][1]}")
    else:
        # team two is larger.
        for _ in range(moves):
            player_to_move = teams[1].players.pop()
            teams[0].players.append(player_to_move)
            player_to_move.setdata(teams[0], player_to_move.character, teams[0].color, player_to_move.highlight)
            icon_info = player_to_move.get_icon_info()
            player_to_move.set_icon_info(icon_info["texture"], icon_info["tint_texture"], teams[0].color, player_to_move.highlight)
            broadcastmessage(f"shifted {player_to_move.getname()} to {json.loads(teams[0].name.as_json())['t'][1]}")
