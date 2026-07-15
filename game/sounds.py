"""The game's sound-effect library. Everything except the recorded pen-tap sample is
synthesized on the fly, so the game can have sound everywhere without a pile of
external audio files."""
import pygame

from . import sound_synth as synth


class Sounds:
    def __init__(self):
        self.x_place = pygame.mixer.Sound("data/sounds/x_place.wav")

        self.o_place = synth.to_sound(synth.sweep(320, 200, 0.09), volume=0.5)

        self.button_confirm = synth.to_sound(synth.sweep(500, 950, 0.08), volume=0.5)

        self.calibration_locked = synth.to_sound(synth.sweep(600, 1100, 0.16), volume=0.4)

        self.error = synth.to_sound(synth.tone(180, 0.15, wave="square"), volume=0.35)

        self.tick = synth.to_sound(synth.tone(880, 0.04, wave="square"), volume=0.25)

        self.win = synth.to_sound(
            synth.tone(523.25, 0.10),  # C5
            synth.tone(659.25, 0.10),  # E5
            synth.tone(783.99, 0.22),  # G5
            volume=0.55,
        )

        self.lose = synth.to_sound(synth.sweep(380, 140, 0.5), volume=0.5)

        self.tie = synth.to_sound(
            synth.tone(440, 0.09),
            synth.silence(0.04),
            synth.tone(440, 0.14),
            volume=0.45,
        )
