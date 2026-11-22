"""Scooby-Doo Pac-Man: a cooperative projector maze controlled with flashlights."""
import argparse
import os
from pathlib import Path
import random
import sys
import time

import pygame
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flashlight_scripture_maze import flashlight
from scooby_doo_pac_man.characters import PLAYERS, VILLAINS, Portraits
from scooby_doo_pac_man.engine import MysteryMaze, SPEEDS

W, H = 1920, 1080
FPS = 60
BG = (6, 8, 18)
FLOOR = (12, 18, 34)
WALL = (68, 82, 118)
PELLET = (105, 94, 74)
TEXT = (190, 190, 180)
ACCENT = (145, 116, 58)


def make_arcade_sounds():
    """Short original synth cues with a classic arcade character."""
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=44100, size=-16, channels=2)

    def cue(notes, waveform="square", volume=0.22):
        rate = 44100
        total = max(start + length for _, start, length in notes) + 0.03
        audio = np.zeros(int(total * rate), np.float32)
        for frequency, start, length in notes:
            begin, count = int(start * rate), int(length * rate)
            t = np.arange(count, dtype=np.float32) / rate
            phase = 2 * np.pi * frequency * t
            wave = np.tanh(2.8 * np.sin(phase)) if waveform == "square" else np.sin(phase)
            envelope = np.minimum(1, t / 0.004) * np.exp(-5 * t / max(length, 0.02))
            audio[begin:begin + count] += wave * envelope
        peak = max(0.001, float(np.max(np.abs(audio))))
        pcm = np.int16(audio / peak * 32767 * volume)
        stereo = np.column_stack((pcm, pcm))
        return pygame.sndarray.make_sound(stereo)

    return {
        "pellet": cue(((880, 0, 0.045),), volume=0.12),
        "snack": cue(((440, 0, 0.09), (660, 0.07, 0.1), (990, 0.14, 0.16))),
        'power_loop': cue(tuple((260 + (i % 4) * 100, i * 0.09, 0.09)
                                for i in range(8)), 'sine', 0.28),
        "villain": cue(((740, 0, 0.08), (980, 0.06, 0.11)), volume=0.18),
        "tag": cue(((330, 0, 0.12), (247, 0.1, 0.17), (196, 0.22, 0.24)), "sine"),
        "solved": cue(((523, 0, 0.18), (659, 0.13, 0.18), (784, 0.26, 0.18),
                       (1047, 0.39, 0.45)), "sine", 0.25),
    }


class Activity:
    def __init__(self, args):
        self.args = args
        pygame.init()
        self.window = self._open_window(not args.window)
        pygame.display.set_caption("Scooby-Doo Pac-Man")
        self.canvas = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.music_on = False
        self._start_music()
        try:
            self.sounds = make_arcade_sounds()
        except pygame.error:
            self.sounds = {}
        self.power_channel = None
        if self.sounds:
            pygame.mixer.set_reserved(1)
            self.power_channel = pygame.mixer.Channel(0)
        self.font = pygame.font.SysFont("arial", 31)
        self.big_font = pygame.font.SysFont("arial", 52, bold=True)
        self.portraits = Portraits(Path(__file__).with_name("local_assets"))
        self.snack_image = None
        snack_path = Path(__file__).with_name('local_assets') / 'scooby-snack.png'
        if snack_path.exists():
            self.snack_image = pygame.image.load(str(snack_path)).convert_alpha()
            self.snack_image.fill((145, 145, 145, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self.snack_sprite = None
        self.random = random.Random(args.seed)
        self.camera = None
        self.mouse_seen = -10.0
        self.visible_lights = 0
        self.selected = 0
        self.player_roster = list(range(args.players))
        self.villain_roster = list(range(args.villains))
        self.message = "Shine a light near an investigator, then lead them through the corridors."
        self.message_until = time.time() + 8
        self.mode = "play"
        self.menu_dwell = 0.0
        self.menu_choice = None
        self.menu_latched = None
        self.new_round()
        self._start_camera()
        if self.mode != 'calibrate':
            self.mode = 'players'

    def _start_music(self):
        music_dir = Path(__file__).with_name("local_assets") / "music"
        theme = next((music_dir / name for name in ("interim.ogg", "theme.ogg", "theme.mp3", "theme.wav")
                      if (music_dir / name).exists()), None)
        if theme is None:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(str(theme))
            pygame.mixer.music.set_volume(0.24)
            pygame.mixer.music.play(-1)
            self.music_on = True
        except pygame.error:
            self.music_on = False

    def _open_window(self, fullscreen):
        sizes = pygame.display.get_desktop_sizes()
        display = self.args.display if self.args.display is not None else len(sizes) - 1
        display = max(0, min(display, len(sizes) - 1))
        self.display = display
        if fullscreen:
            return pygame.display.set_mode(sizes[display], pygame.FULLSCREEN, display=display)
        return pygame.display.set_mode((W // 2, H // 2), pygame.RESIZABLE, display=display)

    def new_round(self):
        if self.power_channel:
            self.power_channel.stop()
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(0.24)
        if self.args.layout == 'classic':
            from scooby_doo_pac_man.classic import LAYOUT
            if not LAYOUT.exists():
                self.args.layout = 'generated'
        seed = self.args.seed if self.args.seed is not None else self.random.randrange(2**31)
        cols, rows = map(int, self.args.size.lower().split("x"))
        self.session = MysteryMaze(cols, rows, self.args.players, self.args.villains, seed,
                                   classic=self.args.layout == 'classic', difficulty=self.args.difficulty)
        cols, rows = self.session.maze.cols, self.session.maze.rows
        margin, top, bottom = 35, 95, 95
        self.cell = min((W - margin * 2) / cols, (H - top - bottom) / rows)
        self.cell_x = (W - margin * 2) / cols if self.args.layout == 'classic' else self.cell
        self.cell_y = self.cell
        self.wall_layer = None
        if self.snack_image is not None:
            side = max(36, int(self.cell * 1.35))
            self.snack_sprite = pygame.transform.smoothscale(self.snack_image, (side, int(side * 2 / 3)))
        self.board = pygame.Rect(
            (W - self.cell_x * cols) / 2,
            top + (H - top - bottom - self.cell_y * rows) / 2,
            self.cell_x * cols,
            self.cell_y * rows,
        )
        if self.camera and self.camera.detector:
            self.camera.detector.reset()

    def _start_camera(self):
        if self.args.mouse:
            return
        cap = flashlight.open_camera(self.args.camera)
        if cap is None:
            self.say(f"No camera {self.args.camera} found; using mouse and arrow keys.", 10)
            return
        self.camera = flashlight.Camera(cap)
        self.camera.start()
        corners = flashlight.load_calibration(self.args.calibration)
        if corners is None:
            self.begin_calibration(4.0 if not self.args.window else 0.9)
        else:
            self.camera.detector = flashlight.SpotDetector(corners, (W, H))

    def say(self, message, seconds=4):
        self.message = message
        self.message_until = time.time() + seconds

    def begin_calibration(self, wait=0.9, tries=3):
        if not self.camera:
            return
        self.mode = "calibrate"
        self.cal_phase = "black"
        self.cal_t0 = time.time()
        self.cal_frames = {"black": [], "white": []}
        self.cal_wait = wait
        self.cal_tries = tries

    def update_calibration(self):
        import numpy as np

        elapsed = time.time() - self.cal_t0
        wait = self.cal_wait if self.cal_phase == "black" else 0.9
        if elapsed <= wait:
            return
        frame = self.camera.latest_frame()
        if frame is not None:
            self.cal_frames[self.cal_phase].append(frame.astype(np.float32))
        if elapsed <= wait + 0.6:
            return
        if self.cal_phase == "black":
            self.cal_phase = "white"
            self.cal_t0 = time.time()
            return
        black = np.mean(self.cal_frames["black"], 0).astype(np.uint8)
        white = np.mean(self.cal_frames["white"], 0).astype(np.uint8)
        corners = flashlight.find_markers(black, white, (W, H))
        if corners is None and self.cal_tries > 1:
            self.begin_calibration(2.0, self.cal_tries - 1)
        elif corners is None:
            self.mode = "play"
            self.say("Calibration failed. Make sure the camera sees the picture, then press C.", 10)
        else:
            flashlight.save_calibration(self.args.calibration, corners, black.shape)
            self.camera.detector = flashlight.SpotDetector(corners, (W, H))
            self.mode = "play"
            self.say("Calibrated. More than one flashlight can now steer more than one investigator.", 7)

    def light_spots(self):
        if self.camera is None or time.time() - self.mouse_seen < 2:
            if not pygame.mouse.get_focused():
                return []
            x, y = pygame.mouse.get_pos()
            width, height = self.window.get_size()
            return [(x * W / width, y * H / height)]
        return self.camera.recent_spots()

    def screen_to_cell(self, point):
        x = int((point[0] - self.board.left) // self.cell_x)
        y = int((point[1] - self.board.top) // self.cell_y)
        return x, y

    def center(self, cell):
        return (int(self.board.left + (cell[0] + 0.5) * self.cell_x),
                int(self.board.top + (cell[1] + 0.5) * self.cell_y))

    def update(self, dt):
        spots = self.light_spots()
        self.visible_lights = len(spots)
        targets = [self.screen_to_cell(spot) for spot in spots]
        self.session.aim(targets)
        self.session.update(dt)
        while self.session.events:
            event = self.session.events.pop(0)
            if event in self.sounds:
                self.sounds[event].play()
        self.update_power_audio()

    def update_power_audio(self):
        if not self.power_channel:
            return
        powered = self.session.frightened > 0 and not self.session.finished and not self.session.restart_in
        if powered and not self.power_channel.get_busy():
            self.power_channel.play(self.sounds['power_loop'], loops=-1)
            pygame.mixer.music.set_volume(0.09)
        elif not powered and self.power_channel.get_busy():
            self.power_channel.stop()
            pygame.mixer.music.set_volume(0.24)

    def player_buttons(self):
        return [pygame.Rect(470 + i * 205, 240, 180, 110) for i in range(5)]

    def setup_buttons(self):
        buttons = [(rect, 'players', i + 1, str(i + 1)) for i, rect in enumerate(self.player_buttons())]
        buttons += [(pygame.Rect(470 + i * 205, 420, 180, 110), 'villains', i, str(i))
                    for i in range(5)]
        buttons += [(pygame.Rect(470 + i * 340, 600, 310, 110), 'difficulty', value, value.title())
                    for i, value in enumerate(SPEEDS)]
        buttons.append((pygame.Rect(710, 820, 500, 120), 'start', None, 'Start'))
        buttons.append((pygame.Rect(1250, 820, 420, 120), 'cast', None, 'Characters'))
        return buttons

    def resize_roster(self, roster, count, total):
        return (roster + [i for i in range(total) if i not in roster])[:count]

    def roster_buttons(self):
        buttons = []
        for group, cast, y in [('player_roster', PLAYERS, 280), ('villain_roster', VILLAINS, 590)]:
            for i, character in enumerate(cast):
                buttons.append((pygame.Rect(210 + i * 305, y, 280, 230), group, i, character.name))
        buttons.append((pygame.Rect(710, 880, 500, 110), 'back', None, 'Done'))
        return buttons

    def menu_buttons(self):
        return self.roster_buttons() if self.mode == 'roster' else self.setup_buttons()

    def apply_setup(self, setting, value):
        if setting == 'start':
            self.choose_players(self.args.players)
        elif setting in ('cast', 'back'):
            self.mode = 'roster' if setting == 'cast' else 'players'
        elif setting in ('player_roster', 'villain_roster'):
            roster = getattr(self, setting)
            if value in roster:
                if setting != 'player_roster' or len(roster) > 1:
                    roster.remove(value)
            else:
                roster.append(value)
            self.args.players = len(self.player_roster)
            self.args.villains = len(self.villain_roster)
        else:
            setattr(self.args, setting, value)
            if setting == 'players':
                self.player_roster = self.resize_roster(self.player_roster, value, len(PLAYERS))
            elif setting == 'villains':
                self.villain_roster = self.resize_roster(self.villain_roster, value, len(VILLAINS))
        self.menu_dwell = 0.0

    def choose_players(self, count):
        self.args.players = count
        self.selected = 0
        self.new_round()
        self.mode = 'play'

    def update_player_menu(self, dt):
        spots = self.light_spots()
        buttons = self.menu_buttons()
        choice = next((i for i, (rect, _, _, _) in enumerate(buttons)
                       if any(rect.collidepoint(p) for p in spots)), None)
        self.menu_dwell = self.menu_dwell + dt if choice == self.menu_choice else 0.0
        self.menu_choice = choice
        if choice != self.menu_latched:
            self.menu_latched = None
        if choice is not None and self.menu_dwell > 1.6 and choice != self.menu_latched:
            _, setting, value, _ = buttons[choice]
            self.apply_setup(setting, value)
            self.menu_latched = choice

    def draw_roster_menu(self):
        self.canvas.fill(BG)
        for text, y in [('Choose your investigators', 170), ('Choose your villains', 540)]:
            label = self.big_font.render(text, True, TEXT)
            self.canvas.blit(label, label.get_rect(center=(W // 2, y)))
        for i, (rect, group, value, name) in enumerate(self.roster_buttons()):
            selected = group != 'back' and value in getattr(self, group)
            pygame.draw.rect(self.canvas, ACCENT if selected else WALL, rect, border_radius=16)
            if group != 'back':
                character = (PLAYERS if group == 'player_roster' else VILLAINS)[value]
                image = self.portraits.get(character, 135)
                self.canvas.blit(image, image.get_rect(center=(rect.centerx, rect.top + 85)))
            label = self.font.render(name, True, TEXT)
            self.canvas.blit(label, label.get_rect(center=(rect.centerx, rect.bottom - 35)))
            if i == self.menu_choice:
                pygame.draw.rect(self.canvas, TEXT, rect, 3, border_radius=16)

    def draw_player_menu(self):
        self.canvas.fill(BG)
        label = self.big_font.render('Set up your mystery', True, TEXT)
        self.canvas.blit(label, label.get_rect(center=(W // 2, 110)))
        for text, y in [('Players', 295), ('Villains', 475), ('Speed', 655)]:
            label = self.font.render(text, True, TEXT)
            self.canvas.blit(label, label.get_rect(midright=(410, y)))
        for i, (rect, setting, value, text) in enumerate(self.setup_buttons()):
            selected = setting in ('players', 'villains', 'difficulty') and getattr(self.args, setting) == value
            pygame.draw.rect(self.canvas, ACCENT if selected else WALL, rect, border_radius=20)
            if i == self.menu_choice:
                pygame.draw.rect(self.canvas, TEXT, rect, 3, border_radius=20)
            label = self.big_font.render(text, True, TEXT)
            self.canvas.blit(label, label.get_rect(center=rect.center))
        label = self.font.render('Light or click to choose. Enter starts. P opens setup.', True, TEXT)
        self.canvas.blit(label, label.get_rect(center=(W // 2, 1000)))

    def draw(self):
        surface = self.canvas
        surface.fill(BG)
        title = self.big_font.render("Scooby-Doo Pac-Man", True, TEXT)
        surface.blit(title, (55, 26))
        status = self.font.render(
            f"Scooby Snacks: {self.session.score:,}    Pellets left: {len(self.session.pellets)}    "
            f"Ruh-rohs: {self.session.tags}    Lights: {self.visible_lights}", True, TEXT)
        surface.blit(status, (W - status.get_width() - 55, 45))
        pygame.draw.rect(surface, FLOOR, self.board)
        self._draw_maze(surface)
        for cell in self.session.pellets:
            if cell in self.session.snacks and self.snack_sprite is not None:
                surface.blit(self.snack_sprite, self.snack_sprite.get_rect(center=self.center(cell)))
                continue
            radius = max(3, int(self.cell * (0.25 if cell in self.session.snacks else 0.075)))
            pygame.draw.circle(surface, ACCENT if cell in self.session.snacks else PELLET, self.center(cell), radius)
        size = max(64, int(self.cell * 2.25))
        for index, actor in enumerate(self.session.players):
            if actor.out:
                continue
            moving = actor.moving_for > 0
            mouth = 'open' if moving and int(actor.animation_time * 12) % 2 == 0 else 'closed'
            image = self.portraits.get(PLAYERS[self.player_roster[index]], size, mouth=mouth,
                                       facing=actor.facing)
            rect = image.get_rect(center=self.center(actor.cell))
            surface.blit(image, rect)
            if index == self.selected:
                pygame.draw.circle(surface, (135, 125, 78), rect.center, size // 2, 3)
        for index, actor in enumerate(self.session.villains):
            center = self.center(actor.cell)
            if actor.out:
                for dx in (-size // 7, size // 7):
                    pygame.draw.circle(surface, (135, 145, 165), (center[0] + dx, center[1]), size // 9)
                    pygame.draw.circle(surface, (35, 55, 120), (center[0] + dx, center[1]), size // 18)
            else:
                image = self.portraits.get(VILLAINS[self.villain_roster[index]], size, self.session.frightened > 0)
                surface.blit(image, image.get_rect(center=center))
                if self.session.frightened > 0:
                    pygame.draw.circle(surface, (60, 95, 165), center, size // 2, 4)
        if self.session.frightened > 0:
            label = self.font.render(f'Scooby power: {self.session.frightened:.1f}s - catch the blue villains!', True, TEXT)
            surface.blit(label, label.get_rect(midtop=(W // 2, 76)))
        if self.session.finished:
            message = self.big_font.render("Mystery solved! Press R for another maze.", True, TEXT)
            panel = pygame.Surface((message.get_width() + 80, message.get_height() + 50), pygame.SRCALPHA)
            panel.fill((4, 6, 14, 225))
            panel.blit(message, (40, 25))
            surface.blit(panel, panel.get_rect(center=(W // 2, H // 2)))
        elif self.session.restart_in > 0:
            message = self.big_font.render('Everyone is out! Get ready...', True, TEXT)
            self.canvas.blit(message, message.get_rect(center=(W // 2, H - 55)))
        elif time.time() < self.message_until:
            message = self.font.render(self.message, True, TEXT)
            surface.blit(message, message.get_rect(center=(W // 2, H - 48)))

    def _draw_maze(self, surface):
        if self.args.layout == 'classic':
            if self.wall_layer is None:
                self.wall_layer = self._classic_walls()
            surface.blit(self.wall_layer, self.board.topleft)
            for y, row in enumerate(self.session.maze.tiles):
                for x, tile in enumerate(row):
                    if tile == '-':
                        pygame.draw.line(surface, ACCENT, self.center((x, y)),
                                         (self.center((x, y))[0], self.center((x, y))[1] + int(self.cell_y)), 2)
            return
        width = max(3, int(self.cell * 0.11))
        cols, rows = self.session.maze.cols, self.session.maze.rows
        for y in range(rows):
            for x in range(cols):
                left = self.board.left + x * self.cell
                top = self.board.top + y * self.cell
                cell = (x, y)
                if y == 0 or not self.session.maze.is_open(cell, (x, y - 1)):
                    pygame.draw.line(surface, WALL, (left, top), (left + self.cell, top), width)
                if x == 0 or not self.session.maze.is_open(cell, (x - 1, y)):
                    pygame.draw.line(surface, WALL, (left, top), (left, top + self.cell), width)
                if y == rows - 1:
                    pygame.draw.line(surface, WALL, (left, top + self.cell),
                                     (left + self.cell, top + self.cell), width)
                if x == cols - 1:
                    pygame.draw.line(surface, WALL, (left + self.cell, top),
                                     (left + self.cell, top + self.cell), width)

    def _classic_walls(self):
        import cv2
        mask = np.zeros((self.board.height, self.board.width), np.uint8)
        for y, row in enumerate(self.session.maze.tiles):
            for x, tile in enumerate(row):
                if tile == '|':
                    mask[int(y * self.cell_y):int((y + 1) * self.cell_y),
                         int(x * self.cell_x):int((x + 1) * self.cell_x)] = 255
        inset_x = max(1, int(self.cell_x * 0.23))
        inset_y = max(1, int(self.cell_y * 0.32))
        mask = cv2.erode(mask, np.ones((inset_y * 2 + 1, inset_x * 2 + 1), np.uint8),
                         borderType=cv2.BORDER_CONSTANT, borderValue=0)
        stroke = max(2, int(self.cell * 0.09))
        inner = cv2.erode(mask, np.ones((stroke * 2 + 1, stroke * 2 + 1), np.uint8))
        layer = pygame.Surface(self.board.size, pygame.SRCALPHA)
        pixels = pygame.surfarray.pixels3d(layer)
        pixels[mask.T > 0] = (35, 60, 145)
        pixels[inner.T > 0] = BG
        del pixels
        alpha = pygame.surfarray.pixels_alpha(layer)
        alpha[:] = mask.T
        del alpha
        return layer

    def draw_calibration(self):
        self.canvas.fill(BG)
        if self.cal_phase == "white":
            side = int(H * flashlight.MARKER_SIZE)
            for x, y in flashlight.marker_centres((W, H)):
                rect = pygame.Rect(int(x - side / 2), int(y - side / 2), side, side)
                pygame.draw.rect(self.canvas, (255, 255, 255), rect)

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.MOUSEMOTION:
            self.mouse_seen = time.time()
        if self.mode in ('players', 'roster'):
            if event.type == pygame.KEYDOWN and pygame.K_1 <= event.key <= pygame.K_5:
                self.apply_setup('players', event.key - pygame.K_1 + 1)
                return True
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self.choose_players(self.args.players)
                return True
            if event.type == pygame.MOUSEBUTTONDOWN:
                point = (event.pos[0] * W / self.window.get_width(), event.pos[1] * H / self.window.get_height())
                for rect, setting, value, _ in self.menu_buttons():
                    if rect.collidepoint(point):
                        self.apply_setup(setting, value)
                        return True
        if event.type != pygame.KEYDOWN:
            return True
        if event.key == pygame.K_ESCAPE:
            return False
        if event.key == pygame.K_r:
            self.new_round()
        elif event.key == pygame.K_p:
            self.mode = 'players'
            if self.power_channel:
                self.power_channel.stop()
                pygame.mixer.music.set_volume(0.24)
        elif event.key == pygame.K_c:
            self.begin_calibration()
        elif event.key == pygame.K_d and self.camera:
            self.camera.show_debug = not self.camera.show_debug
        elif event.key == pygame.K_m and pygame.mixer.get_init():
            self.music_on = not self.music_on
            pygame.mixer.music.unpause() if self.music_on else pygame.mixer.music.pause()
        elif pygame.K_1 <= event.key <= pygame.K_5:
            self.selected = min(event.key - pygame.K_1, len(self.session.players) - 1)
        elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
            directions = {pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0),
                          pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1)}
            self.session.steer(self.selected, directions[event.key])
        return True

    def run(self):
        running = True
        previous = time.time()
        while running:
            for event in pygame.event.get():
                running = running and self.handle_event(event)
            now = time.time()
            dt, previous = min(0.1, now - previous), now
            if self.mode == "calibrate":
                self.update_calibration()
                self.draw_calibration()
            elif self.mode in ('players', 'roster'):
                self.update_player_menu(dt)
                if self.mode == 'roster':
                    self.draw_roster_menu()
                elif self.mode == 'players':
                    self.draw_player_menu()
                else:
                    self.draw()
            else:
                self.update(dt)
                self.draw()
            size = self.window.get_size()
            self.window.blit(self.canvas if size == (W, H) else pygame.transform.smoothscale(self.canvas, size), (0, 0))
            pygame.display.flip()
            self.clock.tick(FPS)
        if self.camera:
            self.camera.stop()
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
        pygame.quit()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", type=int, default=int(os.environ.get("PROJECTOR_CAMERA", 0)))
    parser.add_argument("--display", type=int)
    local_calibration = Path(__file__).with_name("calibration.yaml")
    shared_calibration = ROOT / "calibration.yaml"
    default_calibration = shared_calibration if shared_calibration.exists() else local_calibration
    parser.add_argument("--calibration", default=str(default_calibration))
    parser.add_argument("--mouse", action="store_true", help="use the mouse instead of a camera")
    parser.add_argument("--window", action="store_true")
    parser.add_argument("--size", choices=("15x9", "19x11", "23x13"), default="19x11")
    parser.add_argument('--layout', choices=('classic', 'generated'), default='classic')
    parser.add_argument("--players", type=int, choices=range(1, 6), default=5)
    parser.add_argument("--villains", type=int, choices=range(5), default=4)
    parser.add_argument('--difficulty', choices=tuple(SPEEDS), default='normal')
    parser.add_argument("--seed", type=int)
    return parser.parse_args(argv)


if __name__ == "__main__":
    Activity(parse_args()).run()
