"""Character metadata and local portrait loading."""
from dataclasses import dataclass
from pathlib import Path

import pygame


@dataclass(frozen=True)
class Character:
    slug: str
    name: str
    color: tuple[int, int, int]


PLAYERS = (
    Character("scooby-doo", "Scooby-Doo", (118, 82, 48)),
    Character("shaggy", "Shaggy", (105, 145, 66)),
    Character("velma", "Velma", (190, 88, 42)),
    Character("daphne", "Daphne", (116, 76, 145)),
    Character("fred", "Fred", (72, 112, 158)),
)

VILLAINS = (
    Character("black-knight", "Black Knight", (82, 88, 105)),
    Character("space-kook", "Space Kook", (76, 145, 165)),
    Character("creeper", "Creeper", (85, 135, 78)),
    Character("captain-cutler", "Captain Cutler", (86, 116, 118)),
)


class Portraits:
    """Loads ignored local images and supplies dim circular fallback portraits."""

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.cache = {}
        self.sheet_frames = {}
        sheet_path = self.directory / 'crew-mouth-sprite-sheet.png'
        if sheet_path.exists():
            sheet = pygame.image.load(str(sheet_path)).convert_alpha()
            # This supplied sheet has five cast columns, open above closed.
            for column, character in enumerate(PLAYERS):
                frames = []
                for row in range(2):
                    x0, x1 = column * sheet.get_width() // 5, (column + 1) * sheet.get_width() // 5
                    y0, y1 = row * sheet.get_height() // 2, (row + 1) * sheet.get_height() // 2
                    frames.append(sheet.subsurface((x0, y0, x1 - x0, y1 - y0)).copy())
                # Identical crop and scale for both frames prevents animation jitter.
                bounds = frames[0].get_bounding_rect(min_alpha=128).union(
                    frames[1].get_bounding_rect(min_alpha=128))
                for mouth, frame in zip(('open', 'closed'), frames):
                    self.sheet_frames[(character.slug, mouth)] = frame.subsurface(bounds).copy()

    def get(self, character: Character, size: int, frightened: bool = False, mouth=None, facing=(1, 0)):
        key = (character.slug, size, frightened, mouth, facing)
        if key not in self.cache:
            variant = self.directory / f'{character.slug}-{mouth}.png'
            sprite = self.sheet_frames.get((character.slug, mouth))
            if mouth and variant.exists():
                sprite = pygame.image.load(str(variant)).convert_alpha()
            if sprite is not None:
                scale = (size - 4) / max(sprite.get_size())
                fitted = pygame.transform.smoothscale(sprite, (max(1, round(sprite.get_width() * scale)),
                                                               max(1, round(sprite.get_height() * scale))))
                sprite = pygame.Surface((size, size), pygame.SRCALPHA)
                sprite.blit(fitted, fitted.get_rect(center=(size // 2, size // 2)))
                sprite.fill((150, 150, 158, 255), special_flags=pygame.BLEND_RGBA_MULT)
                if facing == (-1, 0):
                    sprite = pygame.transform.flip(sprite, True, False)
                elif facing == (0, -1):
                    sprite = pygame.transform.rotate(sprite, 90)
                elif facing == (0, 1):
                    sprite = pygame.transform.rotate(sprite, -90)
                self.cache[key] = sprite
            else:
                self.cache[key] = self._make(character, size, frightened)
        return self.cache[key]

    def _make(self, character, size, frightened):
        source = next((self.directory / f"{character.slug}{ext}" for ext in (".png", ".jpg", ".jpeg")
                       if (self.directory / f"{character.slug}{ext}").exists()), None)
        if source:
            try:
                image = pygame.image.load(str(source)).convert_alpha()
                side = min(image.get_size())
                area = pygame.Rect((image.get_width() - side) // 2, (image.get_height() - side) // 2, side, side)
                image = pygame.transform.smoothscale(image.subsurface(area), (size, size))
            except pygame.error:
                image = self._fallback(character, size)
        else:
            image = self._fallback(character, size)

        mask = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (size // 2, size // 2), size // 2 - 2)
        image.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        # Keep portraits below the detector's absolute-brightness threshold without
        # making the fallback initials unreadable on a dark wall.
        shade = pygame.Surface((size, size), pygame.SRCALPHA)
        shade.fill((105, 135, 190, 255) if frightened else (150, 150, 158, 255))
        image.blit(shade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        if frightened:
            blue = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(blue, (35, 65, 145, 190), (size // 2, size // 2), size // 2 - 2)
            image.blit(blue, (0, 0))
        return image

    @staticmethod
    def _fallback(character, size):
        image = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(image, character.color, (size // 2, size // 2), size // 2 - 2)
        pygame.draw.circle(image, (185, 180, 160), (size // 2, size // 2), size // 2 - 2, max(2, size // 18))
        initials = "".join(word[0] for word in character.name.replace("-", " ").split())[:2]
        font = pygame.font.Font(None, int(size * 0.48))
        label = font.render(initials, True, (220, 215, 190))
        image.blit(label, label.get_rect(center=(size // 2, size // 2)))
        return image
