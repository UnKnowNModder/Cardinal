from bascenev1lib.game.elimination import Player, EliminationGame

def balance_lives(self: EliminationGame, player: Player):
    """ balance lives of a player across his teammates."""
    team = player.team
    players_count = len(team.players)
    if players_count < 1:
        return
    for index in range(player.lives):
        teammate = team.players[index % players_count]
        if teammate.lives == 0:
            # need to spawn him as well as update color of his icon and opacity of his name.
            self.spawn_player(teammate)
            teammate.icons[0].node.color = (1, 1, 1)
            teammate.icons[0]._name_text.opacity = 1.0
        teammate.lives += 1
    self._update_icons()