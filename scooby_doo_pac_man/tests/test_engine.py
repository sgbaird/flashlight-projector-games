from scooby_doo_pac_man.engine import MysteryMaze


def test_zero_villains_practice_and_speed_controls():
    relaxed = MysteryMaze(players=1, villains=0, seed=5, difficulty='relaxed')
    fast = MysteryMaze(players=1, villains=0, seed=5, difficulty='fast')
    assert not relaxed.villains
    target = relaxed.maze.neighbors(relaxed.players[0].cell)[0]
    for session in (relaxed, fast):
        session.aim([target])
        session.update(0.1)
    assert relaxed.players[0].cell != target
    assert fast.players[0].cell == target


def test_round_has_connected_actors_and_pellets():
    activity = MysteryMaze(cols=15, rows=9, players=5, villains=4, seed=7)
    assert len(activity.players) == 5
    assert len(activity.villains) == 4
    assert activity.pellets
    for actor in activity.players + activity.villains:
        assert len(activity.maze.bfs(actor.cell)[0]) == 15 * 9


def test_light_near_an_investigator_leads_them_to_target():
    activity = MysteryMaze(cols=15, rows=9, players=2, villains=1, seed=8)
    player = activity.players[0]
    target = activity.maze.neighbors(player.cell)[0]
    activity.aim([target])
    activity.update(0.14)
    assert player.cell == target
    assert player.facing == (target[0] - player.home[0], target[1] - player.home[1])
    assert player.moving_for > 0
    facing = player.facing
    activity.update(0.2)
    assert player.moving_for == 0
    assert player.facing == facing


def test_auto_forward_stops_at_corner_and_only_turns_with_input():
    activity = MysteryMaze(cols=15, rows=9, players=1, villains=0, seed=8)
    player = activity.players[0]
    player.cell = (0, 0)
    player.facing = (1, 0)
    activity.maze.passages = {activity.maze._edge((x, 0), (x + 1, 0)) for x in range(14)}
    activity.maze.passages.add(activity.maze._edge((14, 0), (14, 1)))
    activity.pellets = {(14, 1)}
    activity.snacks = set()
    activity.aim([(14, 0)])
    assert not player.route
    for _ in range(16):
        activity.update(0.131)
    assert player.cell == (14, 0)
    assert player.facing == (1, 0)
    assert player.moving_for == 0
    activity.aim([(14, 1)])
    activity.update(0.131)
    assert player.cell == (14, 1)
    assert player.facing == (0, 1)


def test_a_single_steering_input_keeps_moving_after_beam_leaves():
    activity = MysteryMaze(players=1, villains=0, seed=8)
    player = activity.players[0]
    player.cell = (0, 0)
    activity.maze.passages = {activity.maze._edge((x, 0), (x + 1, 0)) for x in range(5)}
    activity.aim([(1, 0)])
    for _ in range(3):
        activity.update(0.131)
    assert player.cell == (3, 0)


def test_tagged_player_stays_out_and_cannot_be_steered_or_tagged_again():
    activity = MysteryMaze(cols=15, rows=9, players=1, villains=1, seed=9)
    player, villain = activity.players[0], activity.villains[0]
    player.cell = activity.maze.neighbors(player.home)[0]
    villain.cell = player.cell
    activity._collisions()
    assert player.out
    activity.aim([player.home])
    activity.steer(0, (1, 0))
    activity._collisions()
    assert not player.route
    assert activity.tags == 1


def test_team_reset_waits_for_everyone_and_preserves_collectibles_and_score():
    activity = MysteryMaze(players=2, villains=1, seed=12)
    player, other = activity.players
    villain = activity.villains[0]
    activity._collect(next(iter(activity.pellets)))
    pellets, snacks, score = activity.pellets.copy(), activity.snacks.copy(), activity.score
    villain.cell = player.cell
    activity.update(0.01)
    assert player.out and not other.out
    assert activity.restart_in == 0
    villain.cell = other.cell
    activity.update(0.01)
    assert all(actor.out for actor in activity.players)
    assert activity.restart_in == 2.0
    activity.update(1.0)
    assert all(actor.out for actor in activity.players)
    activity.update(1.0)
    assert all(not actor.out and actor.cell == actor.home and not actor.route
               for actor in activity.players + activity.villains)
    assert activity.pellets == pellets
    assert activity.snacks == snacks
    assert activity.score == score
    assert activity.tags == 2


def test_scooby_snack_capture_returns_as_eyes_and_cannot_score_twice():
    activity = MysteryMaze(cols=15, rows=9, players=1, villains=1, seed=10)
    player, villain = activity.players[0], activity.villains[0]
    meeting = activity.maze.neighbors(villain.home)[0]
    player.cell = villain.cell = meeting
    activity.frightened = 1
    activity._collisions()
    assert villain.out
    assert activity.score == 200
    assert activity.events == ["villain"]
    activity._collisions()
    assert activity.score == 200
    while villain.route:
        activity._move_villain(villain)
    assert villain.cell == villain.home
    villain.cooldown = 0
    activity._move_villain(villain)
    assert not villain.out


def test_power_pellet_activates_for_every_player_and_expires():
    activity = MysteryMaze(players=2, villains=1, seed=17)
    snack = next(iter(activity.snacks))
    activity._collect(snack)
    assert snack not in activity.pellets and snack not in activity.snacks
    assert activity.frightened == 8
    player = activity.players[1]
    villain = activity.villains[0]
    villain.cell = player.cell
    activity._collisions()
    assert villain.out and not player.out
    activity.frightened = 0.01
    activity.update(0.02)
    assert activity.frightened == 0


def test_capture_when_player_moves_before_villain_moves_away():
    activity = MysteryMaze(players=1, villains=1, seed=20)
    player, villain = activity.players[0], activity.villains[0]
    target = activity.maze.neighbors(player.cell)[0]
    villain.cell = target
    activity.steer(0, (target[0] - player.cell[0], target[1] - player.cell[1]))
    activity.frightened = 2
    activity._villain_timer = 0.6
    activity.update(0.14)
    assert villain.out
    assert activity.score >= 200
