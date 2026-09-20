from bascenev1._map import Map

from server import config
from stats import stats
from utilities import server_text

from . import patch_method


@patch_method(Map, "__init__", initial=True)
def new_map_init(self, *args, **kwargs):
    if config.stats.enable and config.stats.leaderboard:
        stats.leaderboard(self.node)
    server_text.make_server_text(self.node)
