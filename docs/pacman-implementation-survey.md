# Pac-Man implementation survey

Reviewed before adding Scooby-Doo Pac-Man:

- [`voaneves/pacman-on-pygame`](https://github.com/voaneves/pacman-on-pygame) is MIT-licensed, but its single-file
  engine is coupled to a fixed map, menu, Pandas leaderboard, fonts, logos, and branded image resources. Pulling it
  in would add more replacement work than reusable logic.
- [`StepanTita/pacman`](https://github.com/StepanTita/pacman) is MIT-licensed and has separated model/view/controller
  folders, but includes its own fixed maps and image assets and targets a conventional keyboard activity rather
  than flashlight-controlled cooperative movement.
- [`usawa/pypacman`](https://github.com/usawa/pypacman) contains useful notes about distinct ghost behaviors, but is
  GPLv3, unfinished, and explicitly notes uncertain licensing for its sounds.
- [`vinibrahaj/Pac-man`](https://github.com/vinibrahaj/Pac-man) describes a clean maze/actor split, but the repository
  did not present a clear source license when reviewed, so no code was copied.

The local implementation therefore uses the repository's existing MIT-licensed `Maze` graph and BFS routines.
This preserves the camera-tested geometry and avoids importing unknown media. No source code or media from the
surveyed Pac-Man projects is vendored here.

The later request for the original maze uses the layout definition from
[`masonicGIT/pacman/src/maps.js`](https://github.com/masonicGIT/pacman/blob/master/src/maps.js).
`python -m scooby_doo_pac_man.classic` extracts that layout into ignored local assets. No JavaScript engine code
or maze data is vendored. The local adapter rotates the tiles clockwise and supplies the existing graph API.
