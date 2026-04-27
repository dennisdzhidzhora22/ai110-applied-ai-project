import pytest
from connect4_logic import (
    ROWS, COLS, EMPTY, PLAYER, AI,
    make_board, drop_piece, get_valid_columns,
    check_winner, is_draw, is_terminal, board_to_str,
)


# --- make_board ---

def test_make_board_dimensions():
    board = make_board()
    assert len(board) == ROWS
    assert all(len(row) == COLS for row in board)


def test_make_board_all_empty():
    board = make_board()
    assert all(cell == EMPTY for row in board for cell in row)


# --- drop_piece ---

def test_drop_piece_lands_on_bottom():
    board = make_board()
    board = drop_piece(board, 0, PLAYER)
    assert board[ROWS - 1][0] == PLAYER


def test_drop_piece_stacks():
    board = make_board()
    board = drop_piece(board, 3, PLAYER)
    board = drop_piece(board, 3, AI)
    assert board[ROWS - 1][3] == PLAYER
    assert board[ROWS - 2][3] == AI


def test_drop_piece_does_not_mutate_original():
    board = make_board()
    new_board = drop_piece(board, 0, PLAYER)
    assert board[ROWS - 1][0] == EMPTY
    assert new_board[ROWS - 1][0] == PLAYER


def test_drop_piece_full_column_raises():
    board = make_board()
    for _ in range(ROWS):
        board = drop_piece(board, 0, PLAYER)
    with pytest.raises(ValueError):
        drop_piece(board, 0, PLAYER)


def test_drop_piece_out_of_range_raises():
    board = make_board()
    with pytest.raises(ValueError):
        drop_piece(board, COLS, PLAYER)
    with pytest.raises(ValueError):
        drop_piece(board, -1, PLAYER)


# --- get_valid_columns ---

def test_get_valid_columns_empty_board():
    assert get_valid_columns(make_board()) == list(range(COLS))


def test_get_valid_columns_excludes_full():
    board = make_board()
    for _ in range(ROWS):
        board = drop_piece(board, 2, PLAYER)
    assert 2 not in get_valid_columns(board)


# --- check_winner ---

def test_check_winner_horizontal():
    board = make_board()
    for c in range(4):
        board = drop_piece(board, c, PLAYER)
    assert check_winner(board) == PLAYER


def test_check_winner_vertical():
    board = make_board()
    for _ in range(4):
        board = drop_piece(board, 0, AI)
    assert check_winner(board) == AI


def test_check_winner_diagonal_down_left():
    board = make_board()
    # col i gets i filler AI pieces so PLAYER lands at row (ROWS-1-i):
    # positions (5,0),(4,1),(3,2),(2,3) — row decreases as col increases → down-left.
    for i in range(4):
        for _ in range(i):
            board = drop_piece(board, i, AI)
        board = drop_piece(board, i, PLAYER)
    assert check_winner(board) == PLAYER


def test_check_winner_diagonal_down_right():
    board = make_board()
    # col (3-i) gets i filler AI pieces so PLAYER lands at row (ROWS-1-i):
    # positions (5,3),(4,2),(3,1),(2,0) — row decreases as col decreases → down-right.
    for i in range(4):
        col = 3 - i
        for _ in range(i):
            board = drop_piece(board, col, AI)
        board = drop_piece(board, col, PLAYER)
    assert check_winner(board) == PLAYER


def test_check_winner_no_winner_empty():
    assert check_winner(make_board()) is None


def test_check_winner_no_winner_partial():
    board = make_board()
    board = drop_piece(board, 0, PLAYER)
    board = drop_piece(board, 1, AI)
    assert check_winner(board) is None


# --- is_draw and is_terminal ---

def test_is_draw_empty_board():
    assert not is_draw(make_board())


def test_is_terminal_winner():
    board = make_board()
    for c in range(4):
        board = drop_piece(board, c, AI)
    assert is_terminal(board)


def test_is_terminal_empty():
    assert not is_terminal(make_board())


# --- board_to_str ---

def test_board_to_str_contains_column_numbers():
    s = board_to_str(make_board())
    for c in range(1, COLS + 1):
        assert str(c) in s


def test_board_to_str_reflects_pieces():
    board = make_board()
    board = drop_piece(board, 0, PLAYER)
    board = drop_piece(board, 1, AI)
    s = board_to_str(board)
    assert "X" in s
    assert "O" in s


def test_board_to_str_empty_board_has_no_pieces():
    s = board_to_str(make_board())
    assert "X" not in s
    assert "O" not in s
