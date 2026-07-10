"""Fonts, sounds, and the trained ink-classifier model.

Must be constructed after pygame.init()/pygame.mixer.init()/pygame.font.init() have run.
"""
import pygame
import tensorflow as tf


class Fonts:
    def __init__(self):
        self.countdown = pygame.font.SysFont(None, 56)
        self.result = pygame.font.SysFont(None, 140)
        self.panel_header = pygame.font.SysFont(None, 34)
        self.panel = pygame.font.SysFont(None, 26)
        self.panel_title = pygame.font.SysFont(None, 44)


class Assets:
    def __init__(self):
        self.fonts = Fonts()
        self.x_place_sound = pygame.mixer.Sound("data/sounds/x_place.wav")
        self.model = tf.keras.models.load_model("data/model.keras")
