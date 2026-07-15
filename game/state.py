"""Plain mutable state containers shared across the app.

These are deliberately dumb data holders - the transitions between states (starting a
new round, entering difficulty select, scoring a finished game, ...) live in flow.py so
the "what changes together" logic stays in one place instead of being scattered across
whichever module happens to touch a given field.
"""
import random

from . import config


class GameState:
    """Tic-tac-toe board/turn state, bot difficulty, and session stats."""

    def __init__(self):
        self.board = [["" for _ in range(3)] for _ in range(3)]
        self.current_player = "X" if random.random() < 0.5 else "O"
        self.bot_opens = self.current_player == "O"
        self.winner = None
        self.game_over = False
        self.game_over_time = None
        self.last_countdown_tick = None  # last restart-countdown value a tick sound played for

        self.game_phase = "LEVEL_SELECT"  # "LEVEL_SELECT", "LEVEL_CONFIRM", or "PLAYING"
        self.bot_skill = config.LEVEL_SKILLS["mid"]
        self.current_level_label = None  # no difficulty chosen yet
        self.confirm_level = None
        self.confirm_start_time = None

        self.mark_anim_start = {}  # (row, col) -> time.time() of when that mark was placed
        self.bot_move_ready_time = None  # scheduled time.time() for the bot's next move, or None

        self.stats = {"games": 0, "wins": 0, "losses": 0, "ties": 0}

        self.status_msg = "Checking corner tracking tags..."
        self.status_color = (200, 0, 0)


class VisionState:
    """Camera calibration and ink-motion-detection state."""

    def __init__(self):
        self.homography_matrix = None
        self.homography_locked = False
        self.prev_gray = None
        self.reference_gray = None
        self.motion_detected = False
        self.stable_frames = 0
