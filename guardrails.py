"""
Guardrails for the AI Game Arena.

Three checks:
  notes_update_guard  — ensures a proposed notes addition is novel and
                        non-destructive before it is appended.
  validate_move       — ensures an AI-suggested move is legal for the
                        current game state.
  validate_llm_response — basic sanity check on any LLM output string.

Every accept/reject decision is appended to guardrails.log.
"""

import os
import logging
import config
from connect4_logic import get_valid_columns, COLS

LOG_PATH = os.path.join(os.path.dirname(__file__), "guardrails.log")

_log = logging.getLogger("guardrails")
if not _log.handlers:
    _log.setLevel(logging.INFO)
    _log.propagate = False
    _handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    _handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    _log.addHandler(_handler)


def _generate(prompt: str) -> str:
    return config.generate(prompt)


def _record(check: str, decision: str, detail: str) -> None:
    _log.info("[%s] %s — %s", check, decision, detail)


# ── Notes update guard ────────────────────────────────────────────────────────

def notes_update_guard(current_notes: str, proposed_addition: str) -> bool:
    """
    Ask Gemini whether proposed_addition contains genuinely new information
    not already in current_notes, and does not contradict or delete anything.
    Returns True (approved) or False (rejected). Always logs the decision.
    """
    if not proposed_addition.strip():
        _record("notes_update_guard", "REJECTED", "Empty proposed addition")
        return False

    prompt = (
        "You are a guardrail for a strategy knowledge base.\n\n"
        f"Existing notes:\n---\n{current_notes}\n---\n\n"
        f"Proposed addition:\n{proposed_addition}\n\n"
        "Reply with exactly one word:\n"
        "APPROVED — the addition is new, non-redundant, and safe to append.\n"
        "REJECTED — the addition is redundant, already covered, or would "
        "contradict or damage existing content.\n"
        "Reply with only APPROVED or REJECTED."
    )
    verdict = _generate(prompt).strip().upper()

    if verdict.startswith("APPROVED"):
        _record("notes_update_guard", "APPROVED", proposed_addition[:120])
        return True

    _record("notes_update_guard", "REJECTED", proposed_addition[:120])
    return False


# ── Move validator ────────────────────────────────────────────────────────────

def validate_move(game: str, move, board=None) -> bool:
    """
    Check that a move is structurally legal for the given game.

    connect4:        move must be an int in 0..COLS-1 and column not full.
    number_guessing: move must be parseable as an int.

    Returns True if valid. Logs rejections.
    """
    if game == "connect4":
        try:
            col = int(move)
        except (TypeError, ValueError):
            _record("validate_move", "REJECTED", f"Non-integer move: {move!r}")
            return False
        if col < 0 or col >= COLS:
            _record("validate_move", "REJECTED", f"Column {col} out of range")
            return False
        if board is not None and col not in get_valid_columns(board):
            _record("validate_move", "REJECTED", f"Column {col} is full")
            return False
        return True

    if game == "number_guessing":
        try:
            int(move)
            return True
        except (TypeError, ValueError):
            _record("validate_move", "REJECTED", f"Non-integer guess: {move!r}")
            return False

    _record("validate_move", "REJECTED", f"Unknown game: {game!r}")
    return False


# ── LLM response validator ────────────────────────────────────────────────────

def validate_llm_response(response: str, expected_type: str = "text") -> bool:
    """
    Basic sanity check on an LLM output string.

    expected_type:
      "text" — must be non-empty.
      "move" — must contain at least one digit.

    Returns True if valid. Logs rejections.
    """
    if not response or not response.strip():
        _record("validate_llm_response", "REJECTED", "Empty response")
        return False

    if expected_type == "move" and not any(ch.isdigit() for ch in response):
        _record(
            "validate_llm_response", "REJECTED",
            f"No digit in move response: {response[:80]!r}",
        )
        return False

    return True
