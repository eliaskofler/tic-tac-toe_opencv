"""Pure win-checking logic, shared by real gameplay and the bot's hypothetical search."""


def check_win_condition(board, player):
    """True if player currently has three in a row on the given board."""
    row = -1
    col = -1
    dia = -1

    for i in range(3):
        if board[i][0] == board[i][1] == board[i][2] == player: row = i
        if board[0][i] == board[1][i] == board[2][i] == player: col = i

    if board[0][0] == board[1][1] == board[2][2] == player: dia = 1
    if board[0][2] == board[1][1] == board[2][0] == player: dia = 2

    return row != -1 or col != -1 or dia != -1


def get_board_winner(board):
    """Returns 'X', 'O', 'Tie', or None for a hypothetical board (used by minimax)."""
    lines = []
    for i in range(3):
        lines.append([board[i][0], board[i][1], board[i][2]])
        lines.append([board[0][i], board[1][i], board[2][i]])
    lines.append([board[0][0], board[1][1], board[2][2]])
    lines.append([board[0][2], board[1][1], board[2][0]])

    for line in lines:
        if line[0] != "" and line[0] == line[1] == line[2]:
            return line[0]

    if all(board[r][c] != "" for r in range(3) for c in range(3)):
        return "Tie"
    return None
