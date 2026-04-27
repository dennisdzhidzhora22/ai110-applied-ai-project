ROWS = 6
COLS = 7
EMPTY = 0
PLAYER = 1
AI = 2


def make_board():
    return [[EMPTY] * COLS for _ in range(ROWS)]


def drop_piece(board, col, player):
    """Return new board with piece dropped in col. Raises ValueError if full."""
    if col < 0 or col >= COLS:
        raise ValueError(f"Column {col} out of range (0-{COLS - 1})")
    for row in range(ROWS - 1, -1, -1):
        if board[row][col] == EMPTY:
            new_board = [r[:] for r in board]
            new_board[row][col] = player
            return new_board
    raise ValueError(f"Column {col} is full")


def get_valid_columns(board):
    return [c for c in range(COLS) if board[0][c] == EMPTY]


def check_winner(board):
    """Return winning player (1 or 2), or None if no winner yet."""
    # Horizontal
    for r in range(ROWS):
        for c in range(COLS - 3):
            window = [board[r][c + i] for i in range(4)]
            if window[0] != EMPTY and len(set(window)) == 1:
                return window[0]
    # Vertical
    for r in range(ROWS - 3):
        for c in range(COLS):
            window = [board[r + i][c] for i in range(4)]
            if window[0] != EMPTY and len(set(window)) == 1:
                return window[0]
    # Diagonal down-right
    for r in range(ROWS - 3):
        for c in range(COLS - 3):
            window = [board[r + i][c + i] for i in range(4)]
            if window[0] != EMPTY and len(set(window)) == 1:
                return window[0]
    # Diagonal down-left
    for r in range(ROWS - 3):
        for c in range(3, COLS):
            window = [board[r + i][c - i] for i in range(4)]
            if window[0] != EMPTY and len(set(window)) == 1:
                return window[0]
    return None


def is_draw(board):
    return len(get_valid_columns(board)) == 0


def is_terminal(board):
    return check_winner(board) is not None or is_draw(board)


def board_to_str(board):
    """Return a text representation suitable for display and LLM prompts."""
    symbols = {EMPTY: ".", PLAYER: "X", AI: "O"}
    lines = ["  " + " ".join(str(c + 1) for c in range(COLS))]
    for row in board:
        lines.append("  " + " ".join(symbols[cell] for cell in row))
    return "\n".join(lines)
