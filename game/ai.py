"""The bot's move-selection logic: a minimax search, weakened by BOT_SKILL so it
doesn't play a perfect (unbeatable) game at lower difficulties."""
import random

from .rules import get_board_winner


def minimax(board, depth, is_maximizing):
    result = get_board_winner(board)
    if result == "O": return 10 - depth
    if result == "X": return depth - 10
    if result == "Tie": return 0

    if is_maximizing:
        best_score = float("-inf")
        for r in range(3):
            for c in range(3):
                if board[r][c] == "":
                    board[r][c] = "O"
                    best_score = max(best_score, minimax(board, depth + 1, False))
                    board[r][c] = ""
        return best_score
    else:
        best_score = float("inf")
        for r in range(3):
            for c in range(3):
                if board[r][c] == "":
                    board[r][c] = "X"
                    best_score = min(best_score, minimax(board, depth + 1, True))
                    board[r][c] = ""
        return best_score


def get_computer_move(board, bot_skill):
    """Picks the bot's next move. With probability (1 - bot_skill) it plays a random
    empty cell instead of the minimax-optimal one, so easier difficulties are beatable."""
    empty_cells = [(r, c) for r in range(3) for c in range(3) if board[r][c] == ""]
    if not empty_cells:
        return None

    if random.random() > bot_skill:
        return random.choice(empty_cells)

    best_score = float("-inf")
    best_moves = []
    for r, c in empty_cells:
        board[r][c] = "O"
        score = minimax(board, 0, False)
        board[r][c] = ""
        if score > best_score:
            best_score = score
            best_moves = [(r, c)]
        elif score == best_score:
            best_moves.append((r, c))
    return random.choice(best_moves)
