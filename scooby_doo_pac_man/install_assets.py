"""Install local character headshots from a folder or user-supplied URLs."""
import argparse
import json
from pathlib import Path
import shutil
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    from .characters import PLAYERS, VILLAINS
except ImportError:  # direct `python install_assets.py`
    from characters import PLAYERS, VILLAINS


def install_folder(source, destination):
    installed = []
    for character in PLAYERS + VILLAINS:
        match = next((source / f"{character.slug}{ext}" for ext in (".png", ".jpg", ".jpeg")
                      if (source / f"{character.slug}{ext}").exists()), None)
        if match:
            target = destination / match.name
            shutil.copy2(match, target)
            installed.append(target.name)
    return installed


def install_urls(manifest, destination):
    installed = []
    known = {character.slug for character in PLAYERS + VILLAINS}
    data = json.loads(manifest.read_text(encoding="utf-8"))
    for slug, url in data.items():
        if slug not in known or urlparse(url).scheme not in ("http", "https"):
            raise ValueError(f"Unsupported asset entry: {slug}")
        suffix = Path(urlparse(url).path).suffix.lower()
        suffix = suffix if suffix in (".png", ".jpg", ".jpeg") else ".jpg"
        target = destination / f"{slug}{suffix}"
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=30) as response, target.open("wb") as output:
            shutil.copyfileobj(response, output)
        installed.append(target.name)
    return installed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--from-folder", type=Path)
    source.add_argument("--from-urls", type=Path, metavar="MANIFEST.json")
    parser.add_argument("--destination", type=Path, default=Path(__file__).with_name("local_assets"))
    args = parser.parse_args(argv)
    args.destination.mkdir(parents=True, exist_ok=True)
    installed = (install_folder(args.from_folder, args.destination) if args.from_folder
                 else install_urls(args.from_urls, args.destination))
    print(f"Installed {len(installed)} portraits in {args.destination}")
    missing = [c.slug for c in PLAYERS + VILLAINS
               if not any((args.destination / f"{c.slug}{ext}").exists() for ext in (".png", ".jpg", ".jpeg"))]
    if missing:
        print("Still using drawn fallbacks for: " + ", ".join(missing))


if __name__ == "__main__":
    main()
