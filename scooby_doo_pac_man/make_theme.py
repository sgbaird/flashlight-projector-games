"""Create the original local "Mystery Maze Mix" soundtrack as a looping WAV."""
import argparse
import math
from pathlib import Path
import wave

import numpy as np

RATE = 22050
BPM = 132
BEAT = 60.0 / BPM
BARS = 16
BEATS = BARS * 4


def frequency(midi_note):
    return 440.0 * 2 ** ((midi_note - 69) / 12)


def add_note(track, beat, length, note, volume, voice="organ", pan=0.0):
    start = int(beat * BEAT * RATE)
    count = max(1, int(length * BEAT * RATE))
    t = np.arange(count, dtype=np.float32) / RATE
    freq = frequency(note)
    phase = 2 * np.pi * freq * t
    if voice == "square":
        sound = np.tanh(2.6 * np.sin(phase)) * 0.72
    elif voice == "triangle":
        sound = 2 / np.pi * np.arcsin(np.sin(phase))
    elif voice == "pluck":
        sound = (np.sin(phase) + 0.35 * np.sin(2 * phase) + 0.18 * np.sin(3 * phase))
        sound *= np.exp(-4.2 * t / max(0.08, length * BEAT))
    elif voice == "theremin":
        vibrato = 0.018 * np.sin(2 * np.pi * 5.2 * t)
        sound = np.sin(phase + vibrato * phase) + 0.12 * np.sin(2 * phase)
    else:
        sound = np.sin(phase) + 0.32 * np.sin(2 * phase) + 0.12 * np.sin(3 * phase)
    attack = np.minimum(1.0, t / 0.012)
    release = np.minimum(1.0, (count - np.arange(count)) / max(1, int(RATE * 0.045)))
    envelope = attack * release
    samples = sound * envelope * volume
    left = math.sqrt((1 - pan) / 2)
    right = math.sqrt((1 + pan) / 2)
    end = min(len(track), start + count)
    if end > start:
        track[start:end, 0] += samples[:end - start] * left
        track[start:end, 1] += samples[:end - start] * right


def add_drums(track, rng):
    for beat in np.arange(0, BEATS, 0.5):
        start = int(beat * BEAT * RATE)
        count = int(0.055 * RATE)
        t = np.arange(count, dtype=np.float32) / RATE
        noise = rng.standard_normal(count).astype(np.float32)
        hat = noise * np.exp(-55 * t) * (0.055 if beat % 1 else 0.075)
        end = min(len(track), start + count)
        track[start:end] += hat[:end - start, None]
    for beat in range(BEATS):
        start = int(beat * BEAT * RATE)
        if beat % 4 in (0, 2):
            count = int(0.18 * RATE)
            t = np.arange(count, dtype=np.float32) / RATE
            phase = 2 * np.pi * (78 * t - 38 * t * t)
            kick = np.sin(phase) * np.exp(-20 * t) * 0.23
            end = min(len(track), start + count)
            track[start:end] += kick[:end - start, None]
        if beat % 4 in (1, 3):
            count = int(0.14 * RATE)
            t = np.arange(count, dtype=np.float32) / RATE
            snare = rng.standard_normal(count).astype(np.float32) * np.exp(-25 * t) * 0.12
            end = min(len(track), start + count)
            track[start:end] += snare[:end - start, None]


def compose():
    total = int(BEATS * BEAT * RATE)
    track = np.zeros((total, 2), dtype=np.float32)
    rng = np.random.default_rng(1969)
    progression = (
        ((55, 58, 62), 43),  # G minor
        ((51, 55, 58), 39),  # E-flat
        ((48, 51, 55), 36),  # C minor
        ((50, 54, 57, 60), 38),  # D7
    )
    for bar in range(BARS):
        chord, bass = progression[bar % len(progression)]
        base = bar * 4
        for note in chord:
            add_note(track, base, 3.75, note, 0.075, "organ", pan=(note % 3 - 1) * 0.35)
        for step in range(8):
            note = chord[step % len(chord)] + 24
            add_note(track, base + step * 0.5, 0.28, note, 0.055, "square", pan=0.35)
        for step, offset in enumerate((0, 12, 7, 12)):
            add_note(track, base + step, 0.72, bass + offset, 0.13, "triangle", pan=-0.22)

    # An original call-and-response hook, varied on the repeat.
    motif = (67, 70, 74, 72, 70, 67, 65, 66, 67, 74, 75, 74, 70, 69, 67)
    rhythm = (0.0, 0.5, 1.0, 1.75, 2.25, 3.0, 3.5, 4.0, 4.5, 5.0, 5.75, 6.25, 7.0, 7.5, 7.75)
    for section in (0, 8):
        for phrase in (0, 4):
            shift = 12 if section == 8 and phrase == 4 else 0
            for index, (note, offset) in enumerate(zip(motif, rhythm)):
                length = 0.38 if index not in (3, 10, 14) else 0.65
                add_note(track, (section + phrase) * 4 + offset, length, note + shift,
                         0.095, "pluck", pan=-0.4 + 0.1 * (index % 3))
    for bar in (3, 7, 11, 15):
        add_note(track, bar * 4 + 2.5, 1.35, 79 if bar % 8 == 3 else 82,
                 0.075, "theremin", pan=0.55)
    add_drums(track, rng)

    # A short boundary blend keeps the repeated WAV click-free.
    blend = int(0.025 * RATE)
    fade = np.linspace(0, 1, blend, dtype=np.float32)[:, None]
    middle = track[-blend:] * (1 - fade) + track[:blend] * fade
    track[-blend:] = middle
    peak = max(0.001, float(np.max(np.abs(track))))
    return np.int16(np.clip(track * (0.86 / peak), -1, 1) * 32767)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, nargs="?",
                        default=Path(__file__).with_name("local_assets") / "music" / "theme.wav")
    args = parser.parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    audio = compose()
    with wave.open(str(args.output), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(RATE)
        output.writeframes(audio.tobytes())
    print(f"Wrote {len(audio) / RATE:.1f}s Mystery Maze Mix to {args.output}")


if __name__ == "__main__":
    main()
