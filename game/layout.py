"""Window/board/panel geometry - recomputed once at startup and on every resize."""
import pygame

from . import config


class Layout:
    """Tracks the window size and derives the board/panel rects from it.

    The side panel is always pinned to exactly PANEL_RATIO of the window; the board
    fills the entire remaining space (not forced to stay square, so there's no dead
    space), inset by PANEL_MARGIN on every side so a rounded frame can be drawn around
    it without square corners poking out past the curve.
    """

    def __init__(self, width, height):
        self.width = 0
        self.height = 0
        self.resize(width, height)

    def resize(self, width, height):
        self.width = width
        self.height = height

        if width >= height:
            panel_w = int(width * config.PANEL_RATIO)
            board_w, board_h = width - panel_w, height
            self.panel_rect = pygame.Rect(width - panel_w, 0, panel_w, height)
        else:
            panel_h = int(height * config.PANEL_RATIO)
            board_w, board_h = width, height - panel_h
            self.panel_rect = pygame.Rect(0, height - panel_h, width, panel_h)

        self.board_w = board_w
        self.board_h = board_h
        self.board_rect = pygame.Rect(0, 0, board_w, board_h).inflate(
            -config.PANEL_MARGIN * 2, -config.PANEL_MARGIN * 2
        )
        self.cell_w = self.board_rect.width // 3
        self.cell_h = self.board_rect.height // 3
