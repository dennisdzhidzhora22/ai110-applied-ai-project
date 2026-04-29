"""
Unit tests for guardrails.py.

notes_update_guard calls Gemini via guardrails._generate, so those tests
mock that function. validate_move and validate_llm_response are pure logic
and tested directly without any mocking.
"""

from unittest.mock import patch
import pytest
from connect4_logic import make_board, drop_piece, PLAYER, COLS, ROWS
import guardrails


# ── validate_move — connect4 ──────────────────────────────────────────────────

def test_validate_move_c4_valid():
    assert guardrails.validate_move("connect4", 0) is True


def test_validate_move_c4_valid_all_columns():
    board = make_board()
    for col in range(COLS):
        assert guardrails.validate_move("connect4", col, board) is True


def test_validate_move_c4_out_of_range_high():
    assert guardrails.validate_move("connect4", COLS) is False


def test_validate_move_c4_out_of_range_low():
    assert guardrails.validate_move("connect4", -1) is False


def test_validate_move_c4_full_column():
    board = make_board()
    for _ in range(ROWS):
        board = drop_piece(board, 0, PLAYER)
    assert guardrails.validate_move("connect4", 0, board) is False


def test_validate_move_c4_non_integer():
    assert guardrails.validate_move("connect4", "left") is False


def test_validate_move_c4_string_digit_accepted():
    assert guardrails.validate_move("connect4", "3") is True


# ── validate_move — number_guessing ──────────────────────────────────────────

def test_validate_move_ng_valid():
    assert guardrails.validate_move("number_guessing", 42) is True


def test_validate_move_ng_string_digit():
    assert guardrails.validate_move("number_guessing", "25") is True


def test_validate_move_ng_non_integer():
    assert guardrails.validate_move("number_guessing", "banana") is False


# ── validate_move — unknown game ──────────────────────────────────────────────

def test_validate_move_unknown_game():
    assert guardrails.validate_move("chess", 1) is False


# ── validate_llm_response ─────────────────────────────────────────────────────

def test_validate_llm_response_valid_text():
    assert guardrails.validate_llm_response("Try the center column.") is True


def test_validate_llm_response_empty_string():
    assert guardrails.validate_llm_response("") is False


def test_validate_llm_response_whitespace_only():
    assert guardrails.validate_llm_response("   ") is False


def test_validate_llm_response_move_with_digit():
    assert guardrails.validate_llm_response("I'll play column 4.", "move") is True


def test_validate_llm_response_move_no_digit():
    assert guardrails.validate_llm_response("I'll play center.", "move") is False


# ── notes_update_guard (mocked) ───────────────────────────────────────────────

@patch("guardrails._generate", return_value="APPROVED")
def test_notes_update_guard_approved(mock_gen):
    result = guardrails.notes_update_guard("Existing notes.", "- A new insight.")
    assert result is True


@patch("guardrails._generate", return_value="REJECTED")
def test_notes_update_guard_rejected(mock_gen):
    result = guardrails.notes_update_guard("Existing notes.", "- A redundant insight.")
    assert result is False


def test_notes_update_guard_empty_addition():
    # Rejected immediately without calling Gemini
    result = guardrails.notes_update_guard("Some notes.", "")
    assert result is False


def test_notes_update_guard_whitespace_addition():
    result = guardrails.notes_update_guard("Some notes.", "   ")
    assert result is False
