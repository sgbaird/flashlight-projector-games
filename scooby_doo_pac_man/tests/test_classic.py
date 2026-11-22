import pytest
from scooby_doo_pac_man.classic import LAYOUT
from scooby_doo_pac_man.engine import MysteryMaze


@pytest.mark.skipif(not LAYOUT.exists(), reason='Classic layout is installed locally')
def test_classic_collectibles_and_tunnel_are_reachable():
    session = MysteryMaze(players=2, classic=True)
    assert len(session.players) == 2
    assert len(session.pellets) == 244
    assert len(session.snacks) == 4
    reachable, _ = session.maze.bfs(session.players[0].cell)
    assert session.pellets <= reachable.keys()
    assert (16, 27) in session.maze.neighbors((16, 0))
    assert (session.maze.cols, session.maze.rows) == (31, 28)
    assert all(actor.home in reachable for actor in session.players + session.villains)


@pytest.mark.skipif(not LAYOUT.exists(), reason='Classic layout is installed locally')
def test_sprite_direction_stays_consistent_through_rotated_tunnel():
    session = MysteryMaze(players=1, villains=0, classic=True)
    player = session.players[0]
    player.cell = (16, 0)
    player.facing = (0, -1)
    session.update(0.14)
    assert player.facing == (0, -1)
