from bascenev1._map import Map
from tournament.session import TournamentSession
from server import config
from stats import stats
from bascenev1 import get_foreground_host_session
from . import patch_method

@patch_method(Map, "__init__", initial=True)
def new_map_init(self, *args, **kwargs):
    # if its the tournament session. we need to create the score board.
    session = get_foreground_host_session()
    if isinstance(session, TournamentSession):
        session.create_scoreboard()
    if config.stats.enable and config.stats.leaderboard:
        stats.leaderboard(self.node)
