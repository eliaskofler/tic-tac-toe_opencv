"""Game-flow transitions: scoring a finished game, starting a new round, entering
difficulty select, and confirming a difficulty pick.

Several of these span both GameState and VisionState (e.g. starting a new round also
has to reset the ink-motion-detection debounce), which is why they're free functions
here rather than methods hung off either state class.
"""
import random
import time

from . import config
from .rules import check_win_condition


def check_game_status(state):
    if check_win_condition(state.board, "X"):
        state.winner = "X"; state.game_over = True; state.game_over_time = time.time()
        state.stats["games"] += 1; state.stats["wins"] += 1
        print("Game over: X (player) wins!")
        return
    if check_win_condition(state.board, "O"):
        state.winner = "O"; state.game_over = True; state.game_over_time = time.time()
        state.stats["games"] += 1; state.stats["losses"] += 1
        print("Game over: O (bot) wins!")
        return
    if all(state.board[r][c] != "" for r in range(3) for c in range(3)):
        state.winner = "Tie"; state.game_over = True; state.game_over_time = time.time()
        state.stats["games"] += 1; state.stats["ties"] += 1
        print("Game over: Tie.")


def place_mark(state, row, col, mark):
    """Places a mark and kicks off its pop-in animation."""
    state.board[row][col] = mark
    state.mark_anim_start[(row, col)] = time.time()


def reset_game(state, vision):
    state.board = [["" for _ in range(3)] for _ in range(3)]
    state.current_player = "X" if random.random() < 0.5 else "O"
    state.bot_opens = state.current_player == "O"
    state.winner = None
    state.game_over = False
    state.game_over_time = None
    vision.reference_gray = None
    vision.motion_detected = False
    vision.stable_frames = 0
    state.mark_anim_start = {}
    state.bot_move_ready_time = time.time() + config.BOT_MOVE_DELAY if state.bot_opens else None
    print(f"New round: {'player' if state.current_player == 'X' else 'bot'} moves first.")


def enter_level_select(state, vision):
    state.game_phase = "LEVEL_SELECT"
    vision.motion_detected = False
    vision.stable_frames = 0
    state.current_level_label = None
    print("Entering difficulty select.")


def start_level_confirm(state, level_name):
    state.game_phase = "LEVEL_CONFIRM"
    state.confirm_level = level_name
    state.confirm_start_time = time.time()
