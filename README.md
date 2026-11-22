# Flashlight Projector Games

Projector activities controlled by flashlights. A camera watches the projected picture and maps bright flashlight
spots back into screen coordinates.

## Activities

- [Flashlight Scripture Maze](flashlight_scripture_maze/README.md) — the original Sunday family activity.
- [Scooby-Doo Pac-Man](scooby_doo_pac_man/README.md) — guide the Mystery Inc. team through a pellet maze while
  classic villains patrol the corridors.

## Setup

```powershell
python -m pip install -r requirements.txt
python flashlight_scripture_maze/activity.py --mouse --window
python scooby_doo_pac_man/activity.py --mouse --window
```

Replace `--mouse --window` with `--camera 0` for a projector/camera session. Both activities use the same
calibration file format, so `--calibration path/to/calibration.yaml` can point them at one shared calibration.

The repository contains no Church, Scooby-Doo, or Pac-Man media. Each activity works with drawn fallbacks;
copyrighted pictures and audio are downloaded or installed only on the family's computer into ignored folders.

## Development

```powershell
python -m pytest
python -m py_compile flashlight_scripture_maze/*.py scooby_doo_pac_man/*.py
```

The projector/camera loop needs local hardware and is not exercised by CI.
