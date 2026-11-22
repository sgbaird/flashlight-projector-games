"""Pure Pac-Man-style simulation; no pygame or camera dependencies."""
from dataclasses import dataclass
import random

from flashlight_scripture_maze.maze import Maze

SPEEDS = {'relaxed': 0.6, 'normal': 1.0, 'fast': 1.5}
FOLLOW_DISTANCE = 18


@dataclass
class Actor:
    cell: tuple[int, int]
    home: tuple[int, int]
    route: list[tuple[int, int]]
    cooldown: float = 0.0
    out: bool = False
    facing: tuple[int, int] = (1, 0)
    moving_for: float = 0.0
    animation_time: float = 0.0


class MysteryMaze:
    """Cooperative pellet maze controlled by one or more screen-space light spots."""

    def __init__(self, cols=19, rows=11, players=5, villains=4, seed=None, classic=False,
                 difficulty='normal'):
        self.speed = SPEEDS[difficulty]
        self.rng = random.Random(seed)
        self.maze = Maze(cols, rows, seed=seed, loops=0.28)
        cells = [(x, y) for y in range(rows) for x in range(cols)]
        if classic:
            from scooby_doo_pac_man.classic import ClassicMaze
            self.maze = ClassicMaze()
            cells = sorted(self.maze.cells)
        starts = self._spread(cells, players, reverse=False)
        homes = self._spread(cells, villains, reverse=True)
        self.players = [Actor(cell, cell, []) for cell in starts]
        self.villains = [Actor(cell, cell, []) for cell in homes]
        occupied = set(starts + homes)
        self.pellets = set(cells) - occupied
        self.snacks = set(self._spread(list(self.pellets), min(4, len(self.pellets)), reverse=True))
        if classic:
            starts = [(13, 23), (16, 23), (10, 23), (19, 23), (7, 23)][:players]
            homes = [(12, 11), (15, 11), (9, 11), (18, 11)][:villains]
            starts = [self.maze.rotate(cell) for cell in starts]
            homes = [self.maze.rotate(cell) for cell in homes]
            self.players = [Actor(cell, cell, []) for cell in starts]
            for player in self.players:
                player.facing = (0, -1)
            self.villains = [Actor(cell, cell, []) for cell in homes]
            self.pellets = {(x, y) for y, row in enumerate(self.maze.tiles)
                            for x, tile in enumerate(row) if tile in '.o'}
            self.snacks = {(x, y) for y, row in enumerate(self.maze.tiles)
                           for x, tile in enumerate(row) if tile == 'o'}
        self.score = 0
        self.tags = 0
        self.frightened = 0.0
        self.capture_chain = 0
        self.finished = False
        self.events = []
        self._player_timer = 0.0
        self._villain_timer = 0.0
        self.restart_in = 0.0

    def _spread(self, cells, count, reverse):
        if count <= 0:
            return []
        origin = self.maze.goal if reverse else self.maze.start
        distances, _ = self.maze.bfs(origin)
        ordered = sorted(cells, key=lambda c: distances.get(c, 0), reverse=True)
        chosen = []
        for cell in ordered:
            if all(abs(cell[0] - other[0]) + abs(cell[1] - other[1]) >= 3 for other in chosen):
                chosen.append(cell)
                if len(chosen) == count:
                    break
        return chosen

    def aim(self, targets):
        """A light requests one direction; it never schedules a route of turns."""
        if self.restart_in or self.finished:
            return
        unclaimed = {i for i, player in enumerate(self.players) if not player.out}
        for target in targets:
            if not unclaimed:
                continue
            # A beam often lands on the inside wall of a corner. Snap it to a
            # nearby corridor instead of dropping control at that point.
            if not self.maze.inside(target):
                options = [(target[0] + dx, target[1] + dy)
                           for dx in range(-2, 3) for dy in range(-2, 3)
                           if abs(dx) + abs(dy) <= 2
                           and self.maze.inside((target[0] + dx, target[1] + dy))]
                if not options:
                    continue
                target = min(options, key=lambda cell: (
                    abs(cell[0] - target[0]) + abs(cell[1] - target[1]),
                    min(self._distance(self.players[i].cell, cell) for i in unclaimed)))
            nearest = min(unclaimed, key=lambda i: self._distance(self.players[i].cell, target))
            if self._distance(self.players[nearest].cell, target) <= FOLLOW_DISTANCE:
                player = self.players[nearest]
                dx, dy = target[0] - player.cell[0], target[1] - player.cell[1]
                if dx or dy:
                    direction = ((1 if dx > 0 else -1), 0) if abs(dx) > abs(dy) else (0, (1 if dy > 0 else -1))
                    self.steer(nearest, direction)
                unclaimed.remove(nearest)

    def next_cell(self, actor, direction):
        for target in self.maze.neighbors(actor.cell):
            dx, dy = target[0] - actor.cell[0], target[1] - actor.cell[1]
            if abs(dx) > 1:
                dx = -dx
            if abs(dy) > 1:
                dy = -dy
            step = ((1 if dx > 0 else -1), 0) if dx else (0, (1 if dy > 0 else -1))
            if step == direction:
                return target
        return None

    def steer(self, player_index, direction):
        actor = self.players[player_index]
        if actor.out or self.restart_in or self.finished:
            return
        if self.next_cell(actor, direction) is not None:
            actor.facing = direction

    def update(self, dt):
        if self.finished:
            return
        if self.restart_in > 0:
            self.restart_in = max(0.0, self.restart_in - dt)
            if self.restart_in == 0:
                self._reset_actors()
            return
        was_finished = self.finished
        self.frightened = max(0.0, self.frightened - dt)
        for actor in self.players + self.villains:
            actor.cooldown = max(0.0, actor.cooldown - dt)
            actor.moving_for = max(0.0, actor.moving_for - dt)
            if actor.moving_for > 0 or actor.route:
                actor.animation_time += dt * self.speed
        self._player_timer += dt * self.speed
        self._villain_timer += dt * self.speed
        while self._player_timer >= 0.13:
            self._player_timer -= 0.13
            for player in self.players:
                if player.out or player.cooldown > 0:
                    continue
                target = self.next_cell(player, player.facing)
                if target is None:
                    player.moving_for = 0.0
                    continue
                player.cell = target
                player.moving_for = 0.16 / self.speed
                self._collect(player.cell)
            self._collisions()
        villain_period = 0.42 if self.frightened <= 0 else 0.62
        while self._villain_timer >= villain_period:
            self._villain_timer -= villain_period
            for villain in self.villains:
                self._move_villain(villain)
            self._collisions()
        self._collisions()
        self.finished = not self.pellets
        if self.finished and not was_finished:
            self.events.append("solved")
        elif all(player.out for player in self.players):
            self.restart_in = 2.0

    def _reset_actors(self):
        """Start another team attempt without replacing the maze or collectibles."""
        for actor in self.players + self.villains:
            actor.cell = actor.home
            actor.route.clear()
            actor.cooldown = 0.0
            actor.out = False
            actor.facing = (0, -1) if hasattr(self.maze, 'tiles') else (1, 0)
            actor.moving_for = actor.animation_time = 0.0
        self.frightened = 0.0
        self.capture_chain = 0
        self._player_timer = self._villain_timer = 0.0

    def _collect(self, cell):
        snack = cell in self.snacks
        if cell in self.pellets:
            self.pellets.remove(cell)
            self.score += 10
            self.events.append("snack" if snack else "pellet")
        if snack:
            self.snacks.remove(cell)
            self.frightened = 8.0
            self.capture_chain = 0
            self.score += 50

    def _move_villain(self, villain):
        if villain.out:
            if villain.route:
                villain.cell = villain.route.pop(0)
            elif villain.cooldown <= 0:
                villain.out = False
            return
        active = [player for player in self.players if not player.out]
        if not active:
            return
        available = self.maze.neighbors(villain.cell)
        if not available:
            return
        distances = [(min(self._distance(cell, player.cell) for player in active), cell)
                     for cell in available]
        if self.frightened > 0:
            villain.cell = max(distances, key=lambda item: item[0])[1]
        else:
            villain.cell = min(distances, key=lambda item: item[0])[1]

    def _collisions(self):
        for villain in self.villains:
            if villain.out:
                continue
            for player in self.players:
                if player.out or villain.cell != player.cell or player.cooldown > 0:
                    continue
                if self.frightened > 0:
                    villain.out = True
                    villain.route = (self.maze.path(villain.cell, villain.home) or [villain.home])[1:]
                    villain.cooldown = 2.0
                    self.score += 200 * 2 ** min(self.capture_chain, 3)
                    self.capture_chain += 1
                    self.events.append("villain")
                    break
                else:
                    player.out = True
                    player.route.clear()
                    self.tags += 1
                    self.events.append("tag")

    def _distance(self, a, b):
        dist, _ = self.maze.bfs(a)
        return dist.get(b, self.maze.cols * self.maze.rows)
