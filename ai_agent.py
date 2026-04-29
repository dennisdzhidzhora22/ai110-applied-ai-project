"""
AI Agent for the AI Game Arena.

Provides four public functions — one per game/mode combination:
  c4_get_ai_move        — Connect-4 Opponent: Gemini picks a column + explains
  c4_get_teacher_hint   — Connect-4 Teacher: commentary on the human's last move
  ng_get_ai_guess       — Number Guessing Opponent: Gemini picks a guess + explains
  ng_get_teacher_hint   — Number Guessing Teacher: feedback after a human guess

And one post-game function:
  run_post_game         — generates insight, guards it, updates strategy notes

Each move/hint function follows the agentic workflow:
  1. Retrieve relevant strategy notes (RAG)
  2. Build prompt: persona + retrieved notes + current game state
  3. Call Gemini
  4. Validate response via guardrails
  5. If invalid: retry once, then fall back gracefully
"""

import random
import re

import config
import strategy_notes
import guardrails
from connect4_logic import get_valid_columns, board_to_str, COLS

# Populated by each public function; read by app.py for the Agent Trace expander.
_trace: dict = {}


def _generate(prompt: str) -> str:
    return config.generate(prompt)


# ── Prompt builders ───────────────────────────────────────────────────────────

_TEACHER_PERSONA = (
    "You are a patient, educational game coach. "
    "Give concise, Socratic hints — guide the player toward the right idea "
    "without just telling them the answer. Keep responses under 3 sentences."
)

_OPPONENT_PERSONA = (
    "You are a competitive but fair AI opponent. "
    "Briefly explain your reasoning in 1-2 sentences. Be direct."
)


def _notes_context(game: str, situation: str, notes_mode: str) -> str:
    """Return a formatted block of retrieved notes, or empty string if none."""
    snippet = strategy_notes.retrieve_relevant(game, situation, notes_mode)
    _trace["retrieval_query"] = situation
    _trace["retrieved_notes"] = snippet
    if not snippet:
        return ""
    return f"\nRelevant strategy notes:\n{snippet}\n"


# ── Connect-4 Opponent ────────────────────────────────────────────────────────

def c4_get_ai_move(board, notes_mode: str = "seeded") -> tuple[int, str]:
    """
    Ask Gemini to pick a Connect-4 column and explain why.
    Returns (column_index, explanation). Falls back to a random valid column
    if both Gemini attempts return an invalid move.
    """
    _trace.clear()
    _trace.update({"persona": "Opponent", "persona_text": _OPPONENT_PERSONA, "game": "connect4"})
    valid = get_valid_columns(board)
    board_str = board_to_str(board)
    situation = f"AI must pick a column. Valid columns (0-indexed): {valid}."
    notes_ctx = _notes_context("connect4", situation, notes_mode)
    valid_1indexed = [c + 1 for c in valid]

    prompt = (
        f"{_OPPONENT_PERSONA}\n{notes_ctx}\n"
        f"Current board (X=player, O=AI):\n{board_str}\n\n"
        f"Valid columns to drop a piece: {valid_1indexed} (1-indexed).\n"
        "Choose one column number and briefly explain your choice.\n"
        "Start your response with the column number on its own line, "
        "then your explanation. Example:\n4\nI'm threatening a diagonal."
    )

    for attempt in range(2):
        raw = _generate(prompt)
        if not guardrails.validate_llm_response(raw, "move"):
            continue
        col = _parse_c4_column(raw, valid)
        if col is not None and guardrails.validate_move("connect4", col, board):
            _trace["validation"] = f"passed — column {col + 1} is legal"
            explanation = _strip_leading_number(raw)
            return col, explanation

    # Both attempts failed — fall back silently
    _trace["validation"] = "fallback — both Gemini attempts returned an invalid move"
    fallback_col = random.choice(valid)
    return fallback_col, f"I'll play column {fallback_col + 1}."


def c4_get_teacher_hint(board, last_player_col: int, notes_mode: str = "seeded") -> str:
    """
    Return a short coaching comment on the human's last move in Connect-4.
    """
    _trace.clear()
    _trace.update({"persona": "Teacher", "persona_text": _TEACHER_PERSONA, "game": "connect4"})
    board_str = board_to_str(board)
    situation = (
        f"Human just dropped a piece in column {last_player_col + 1}. "
        "Evaluate whether it was a good move."
    )
    notes_ctx = _notes_context("connect4", situation, notes_mode)

    prompt = (
        f"{_TEACHER_PERSONA}\n{notes_ctx}\n"
        f"Current board after the human played column {last_player_col + 1}:\n"
        f"{board_str}\n\n"
        "Give brief coaching feedback on that move. Was it strategically sound? "
        "What should the player watch out for next?"
    )
    raw = _generate(prompt)
    if guardrails.validate_llm_response(raw):
        _trace["validation"] = "passed"
        return raw
    _trace["validation"] = "fallback — empty LLM response"
    return "Good move — keep thinking about threats and blocks!"


# ── Number Guessing Opponent ──────────────────────────────────────────────────

def ng_get_ai_guess(low: int, high: int, history: list[dict],
                    notes_mode: str = "seeded") -> tuple[int, str]:
    """
    Ask Gemini to guess the human's secret number given the current known range.
    history is a list of {"guess": int, "result": "Too High"|"Too Low"} dicts.
    Returns (guess, reasoning). Falls back to midpoint if Gemini fails.

    The effective range is derived from history internally so the fallback
    midpoint is always correct regardless of what low/high the caller passes.
    """
    _trace.clear()
    _trace.update({"persona": "Opponent", "persona_text": _OPPONENT_PERSONA, "game": "number_guessing"})
    # Narrow the range based on past results so the prompt and fallback
    # reflect the actual remaining search space, not just the initial bounds.
    eff_low, eff_high = low, high
    for h in history:
        if h["result"] == "Too High":
            eff_high = min(eff_high, h["guess"] - 1)
        elif h["result"] == "Too Low":
            eff_low = max(eff_low, h["guess"] + 1)

    situation = f"AI is guessing a number between {eff_low} and {eff_high}."
    notes_ctx = _notes_context("number_guessing", situation, notes_mode)

    history_str = "\n".join(
        f"  Guessed {h['guess']}: {h['result']}" for h in history
    ) or "  (no guesses yet)"

    prompt = (
        f"{_OPPONENT_PERSONA}\n{notes_ctx}\n"
        f"You are guessing a secret number. Current known range: {eff_low} to {eff_high}.\n"
        f"Previous guesses:\n{history_str}\n\n"
        "Pick the best next guess and explain your reasoning in one sentence.\n"
        "Start your response with just the number on its own line, "
        "then your explanation. Example:\n37\nI'm splitting the range in half."
    )

    for _ in range(2):
        raw = _generate(prompt)
        if not guardrails.validate_llm_response(raw, "move"):
            continue
        guess = _parse_number(raw)
        if guess is not None and guardrails.validate_move("number_guessing", guess):
            _trace["validation"] = f"passed — guess {guess} is a valid integer"
            explanation = _strip_leading_number(raw)
            return guess, explanation

    _trace["validation"] = "fallback — both Gemini attempts returned an invalid guess"
    midpoint = (eff_low + eff_high) // 2
    return midpoint, f"I'll try {midpoint} — the midpoint of my remaining range."


def ng_get_teacher_hint(guess: int, outcome: str, low: int, high: int,
                        attempt_num: int, notes_mode: str = "seeded") -> str:
    """
    Return coaching feedback after a human guess in number guessing.
    outcome is "Too High", "Too Low", or "Win".
    """
    _trace.clear()
    _trace.update({"persona": "Teacher", "persona_text": _TEACHER_PERSONA, "game": "number_guessing"})
    situation = (
        f"Player guessed {guess} (attempt {attempt_num}). "
        f"Result: {outcome}. Remaining range: {low} to {high}."
    )
    notes_ctx = _notes_context("number_guessing", situation, notes_mode)

    prompt = (
        f"{_TEACHER_PERSONA}\n{notes_ctx}\n"
        f"The player guessed {guess} on attempt {attempt_num}. "
        f"The result was: {outcome}. "
        f"The answer is somewhere between {low} and {high}.\n\n"
        "Give a short coaching tip. Focus on whether they're using an efficient "
        "strategy and what range they should be thinking about next."
    )
    raw = _generate(prompt)
    if guardrails.validate_llm_response(raw):
        _trace["validation"] = "passed"
        return raw
    _trace["validation"] = "fallback — empty LLM response"
    return "Think about which guess would eliminate the most possibilities!"


# ── Post-game insight pipeline ────────────────────────────────────────────────

def run_post_game(game: str, game_summary: str, notes_mode: str = "seeded") -> bool:
    """
    Full post-game agentic workflow:
      1. Ask Gemini to generate an insight from the game summary.
      2. Pass it through the notes guardrail.
      3. Append to strategy notes if approved.
    Returns True if the notes were updated, False otherwise.
    """
    insight = strategy_notes.generate_insight(game, game_summary, notes_mode)
    if not insight:
        _trace["post_game"] = "No new insight generated (Gemini returned NO_NEW_INSIGHT)"
        _trace["notes_updated"] = False
        return False

    _trace["post_game_insight"] = insight
    current_notes = strategy_notes.load_notes(game, notes_mode)
    approved = guardrails.notes_update_guard(current_notes, insight)
    updated = strategy_notes.update_notes(game, insight, approved, notes_mode)
    _trace["notes_updated"] = updated
    _trace["post_game"] = "Notes updated ✓" if updated else "Guardrail rejected — insight not novel enough"
    return updated


# ── Parsing helpers ───────────────────────────────────────────────────────────

def _parse_c4_column(text: str, valid: list[int]) -> int | None:
    """
    Extract the first digit(s) from text and convert from 1-indexed to
    0-indexed. Return None if no valid column is found.
    """
    for match in re.finditer(r"\d+", text):
        col_1indexed = int(match.group())
        col_0indexed = col_1indexed - 1
        if col_0indexed in valid:
            return col_0indexed
    return None


def _parse_number(text: str) -> int | None:
    """Return the first integer found in text, or None."""
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None


def _strip_leading_number(text: str) -> str:
    """Remove a leading standalone number line from Gemini's response."""
    lines = text.strip().splitlines()
    if lines and re.fullmatch(r"\d+", lines[0].strip()):
        return "\n".join(lines[1:]).strip()
    return text.strip()
