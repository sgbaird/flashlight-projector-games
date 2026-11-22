# Scooby-Doo Pac-Man

The default is the original Pac-Man layout rotated clockwise to 31×28, with outlined walls,
wider visible corridors, and larger circular character icons. The maze fills the landscape projection;
corridor spacing expands horizontally while character icons stay round. Its tunnel connects the top and bottom edges.
The layout is installed locally with
`python -m scooby_doo_pac_man.classic` from the repository root. The layout data comes from
[masonicGIT/pacman](https://github.com/masonicGIT/pacman/blob/master/src/maps.js) and stays in ignored local assets.
If the local layout has not been installed, startup uses a generated maze automatically.
Use `--layout generated` for the earlier generated maze. The opening setup screen selects 1–5 players,
0–4 villains (zero is practice mode), and Relaxed, Normal, or Fast movement (0.6×, 1×, or 1.5×).
Choose Start when ready; **P** returns to setup. Command-line defaults can be set with
`--players N --villains N --difficulty relaxed|normal|fast`. Speed changes movement for both teams;
power-up duration and the team-reset pause still use real seconds.

Choose **Characters** on setup to toggle specific investigators and villains. At least one investigator is
required; no villains is allowed. The selected portraits determine the counts; changing a count keeps the
chosen characters first and fills any extra slots from the remaining cast.

Scooby Snacks power up the entire team for eight seconds. Villains turn blue and flee, and the screen shows a
countdown. Touch a blue villain to capture it: its eyes return to its starting cell before it rejoins the chase.
An original looping power sound plays throughout the eight seconds, with background music lowered so it is audible.
Captures during one power-up earn 200, 400, 800, then 1600 points. Captured villains cannot tag players or score
again during the return trip. Eating another snack renews the timer and starts a new capture chain.

Investigators move continuously straight ahead until a wall stops them. They never choose a turn automatically.
A flashlight within 18 corridor steps requests a direction toward the beam; a legal turn takes effect immediately,
and the investigator continues in that direction after the beam leaves. Arrow keys steer the selected investigator
the same way. A beam just on a wall snaps to a corridor within two tiles. There is no automatic route around corners.

The locally downloaded 8 Bit Composer track, “Scooby-Doo! Main Theme | 8 Bit,” loops from
`local_assets/music/interim.ogg` when present. Source: https://www.youtube.com/watch?v=Kpw35aMasEI.
The supplied two-frame cast sheet is loaded from `local_assets/crew-mouth-sprite-sheet.png` (five columns in
cast order, open mouths above closed mouths). Both frames share a crop and scale to prevent jitter. Walking
figures alternate mouth frames and face their actual movement direction: left is flipped, and up/down are
rotated. Idle figures hold their direction with their mouths closed. Individual overrides can be installed as
`local_assets/<character>-open.png` and `local_assets/<character>-closed.png`; portraits are the fallback.

A cooperative projector activity: Scooby-Doo and the Mystery Inc. team gather pellets and Scooby Snacks while
classic villains patrol a generated maze. A flashlight controls whichever investigator it is touching. With two
visible flashlight spots, two different investigators can move at once; no brightness-based identity is required.

```powershell
python activity.py --mouse --window
python activity.py --camera 0
```

The mouse and arrow keys make projector-free testing possible. Press **1**–**5** to select an investigator for
the arrow keys, **R** for a new maze, **C** to recalibrate, **D** for the local camera diagnostic, and **Esc** to
quit. A tagged investigator is out for the current team attempt and no longer attracts villains. Once everyone
is out, a two-second pause resets all investigators and villains to their starting positions, preserving the
remaining pellets, remaining Scooby Snacks, and score. A Scooby Snack temporarily
sends tagged villains back to their own starting cells.

Press **M** to pause or resume the local soundtrack. Generate the original, copyright-safe “Mystery Maze Mix”
fallback with:

```powershell
python make_theme.py
```

The ignored output is `local_assets/music/theme.wav`. Audio preference is `interim.ogg`, then `theme.ogg`,
`theme.mp3`, and `theme.wav`.

## Local character portraits

The public repository does not contain Scooby-Doo or Pac-Man media. The activity looks for these files in the
ignored `local_assets/` folder:

| Mystery Inc. | Villains |
|---|---|
| `scooby-doo`, `shaggy`, `velma`, `daphne`, `fred` | `black-knight`, `space-kook`, `creeper`, `captain-cutler` |

Each name may end in `.png`, `.jpg`, or `.jpeg`. Images are center-cropped into circular, detector-safe portraits.
Missing images become colored initial icons, so setup is optional.

To install files already downloaded into another folder:

```powershell
python install_assets.py --from-folder C:\path\to\headshots
```

Or create a private JSON file mapping slugs to direct image URLs and download them locally:

```json
{
  "scooby-doo": "https://example.test/scooby.png",
  "space-kook": "https://example.test/space-kook.jpg"
}
```

```powershell
python install_assets.py --from-urls my-private-asset-urls.json
```

Keep that URL file and downloaded media private. Only use sources you are comfortable using for your personal,
noncommercial setup.

## Design notes

The activity reuses the Scripture Maze's generated-maze graph, calibration, background learning, camera thread,
and flashlight detector. The detector now retains every qualifying bright blob while preserving its original
single-brightest-spot API. It never draws a marker at a detected spot, which would create feedback.

See [the implementation survey](../docs/pacman-implementation-survey.md) for the Pac-Man codebases considered.
