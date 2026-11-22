"""Local classic layout import and a graph adapter for the activity engine."""
import json
from pathlib import Path
import re
from urllib.request import urlopen

from flashlight_scripture_maze.maze import Maze, DIRS

LAYOUT = Path(__file__).with_name('local_assets') / 'classic-layout.json'
SOURCE = 'https://raw.githubusercontent.com/masonicGIT/pacman/master/src/maps.js'


def download():
    text = urlopen(SOURCE, timeout=30).read().decode('utf-8')
    section = text.split('var mapPacman = new Map(28, 36, (', 1)[1].split('));', 1)[0]
    rows = re.findall(r'"([^"\n]+)"', section)[3:34]
    if len(rows) != 31 or any(len(row) != 28 for row in rows):
        raise ValueError('Unexpected classic layout format')
    LAYOUT.parent.mkdir(parents=True, exist_ok=True)
    LAYOUT.write_text(json.dumps(rows), encoding='utf-8')


class ClassicMaze(Maze):
    def __init__(self):
        self.tiles = json.loads(LAYOUT.read_text(encoding='utf-8'))
        # Rotate the original clockwise; keep all corridor connections intact.
        self.tiles = [''.join(row[x] for row in reversed(self.tiles)) for x in range(28)]
        self.cols, self.rows = 31, 28
        self.cells = {(x, y) for y, row in enumerate(self.tiles) for x, tile in enumerate(row)
                      if tile in '.o '}
        self.start, self.goal = self.rotate((13, 23)), self.rotate((13, 11))
        self.passages = {self._edge(cell, (cell[0] + dx, cell[1] + dy))
                         for cell in self.cells for dx, dy in DIRS
                         if (cell[0] + dx, cell[1] + dy) in self.cells}

    def inside(self, cell):
        return cell in self.cells

    @staticmethod
    def rotate(cell):
        return 30 - cell[1], cell[0]

    def neighbors(self, cell):
        result = super().neighbors(cell)
        if cell == (16, 0):
            result.append((16, 27))
        elif cell == (16, 27):
            result.append((16, 0))
        return result

    def is_open(self, a, b):
        return (a, b) in (((16, 0), (16, 27)), ((16, 27), (16, 0))) or super().is_open(a, b)


if __name__ == '__main__':
    download()
