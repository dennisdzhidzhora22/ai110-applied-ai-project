"""
RAG layer for strategy notes.

Each game has two note files in strategy_notes/:
  <game>.md       — seeded with known strategy (best AI quality)
  <game>_blank.md — scaffold headers only (best demo visibility of RAG growth)

Pass notes_mode="seeded" or notes_mode="blank" to switch between them.
Accumulated "Learned" entries are always written to the active file.
"""

import os
from datetime import datetime
import config

NOTES_DIR = os.path.join(os.path.dirname(__file__), "strategy_notes")
VALID_GAMES = {"number_guessing", "connect4"}


def _generate(prompt: str) -> str:
    return config.generate(prompt)


def _notes_path(game: str, notes_mode: str = "seeded") -> str:
    if game not in VALID_GAMES:
        raise ValueError(f"Unknown game '{game}'. Valid: {VALID_GAMES}")
    suffix = "_blank" if notes_mode == "blank" else ""
    return os.path.join(NOTES_DIR, f"{game}{suffix}.md")


def load_notes(game: str, notes_mode: str = "seeded") -> str:
    """Return the full text of the strategy notes for a game."""
    path = _notes_path(game, notes_mode)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def retrieve_relevant(game: str, context_description: str, notes_mode: str = "seeded") -> str:
    """
    Ask Gemini to extract the most relevant section of the strategy notes
    given the current game situation. Returns a short excerpt (the retrieval
    step of RAG). Returns empty string if the notes have no content yet.
    """
    notes = load_notes(game, notes_mode)

    # Skip retrieval if all sections are empty (blank mode, no learned entries)
    lines_with_content = [l for l in notes.splitlines() if l.strip() and not l.startswith("#")]
    if not lines_with_content:
        return ""

    prompt = (
        f"You are a strategy assistant. Below are strategy notes for {game}.\n\n"
        f"---\n{notes}\n---\n\n"
        f"Current situation: {context_description}\n\n"
        "Extract and return only the most relevant 2-4 bullet points from the "
        "notes above that apply to this situation. Do not add new information. "
        "Return only the bullet points, nothing else."
    )
    return _generate(prompt)


def generate_insight(game: str, game_summary: str, notes_mode: str = "seeded") -> str:
    """
    Ask Gemini to produce a concise insight from a completed game.
    Returns the proposed insight text, or an empty string if nothing new was learned.
    """
    notes = load_notes(game, notes_mode)
    prompt = (
        f"You are a strategy analyst for the game {game}.\n\n"
        f"Existing strategy notes:\n---\n{notes}\n---\n\n"
        f"Game summary: {game_summary}\n\n"
        "Does this game reveal any new strategic insight not already covered "
        "in the notes above? If yes, write a single concise bullet point "
        "(starting with '-') capturing the new insight. "
        "If nothing new was learned, reply with exactly: NO_NEW_INSIGHT"
    )
    text = _generate(prompt)
    return "" if text == "NO_NEW_INSIGHT" else text


def update_notes(game: str, new_insight: str, approved: bool, notes_mode: str = "seeded") -> bool:
    """
    Append a new insight to the active strategy notes file.
    approved should be the result of guardrails.notes_update_guard().
    Returns True if the file was updated, False if skipped.
    """
    if not approved or not new_insight.strip():
        return False
    path = _notes_path(game, notes_mode)
    timestamp = datetime.now().strftime("%Y-%m-%d")
    entry = f"\n## Learned {timestamp}\n\n{new_insight.strip()}\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(entry)
    return True
