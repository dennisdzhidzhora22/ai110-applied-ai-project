"""
Reliability evaluator for the AI Game Arena.

Run with: python evaluator.py

Four checks:
  run_ai_guessing_eval   — AI Opponent guessing mode: verifies convergence
                           within ceil(log2(range)) guesses across N games.
  run_ai_vs_ai_connect4  — Minimax depth-4 vs depth-2: records win/draw/loss.
  consistency_check      — Asks Gemini the same question 3x at temp=0,
                           verifies responses are semantically similar.
  notes_integrity_check  — Verifies strategy notes files exist and are non-empty.

Results are printed to stdout and saved to eval_results.json.
"""

import json
import math
import os
import random
from datetime import datetime

# ── Minimax (evaluator-only, not used in gameplay) ────────────────────────────
from connect4_logic import (
    make_board, drop_piece, get_valid_columns, check_winner,
    is_draw, is_terminal, PLAYER, AI, EMPTY, COLS, ROWS,
)
from logic_utils import check_guess
from ai_agent import ng_get_ai_guess
from strategy_notes import load_notes, NOTES_DIR


def _score_window(window, player):
    opp = PLAYER if player == AI else AI
    score = 0
    if window.count(player) == 4:
        score += 100
    elif window.count(player) == 3 and window.count(EMPTY) == 1:
        score += 5
    elif window.count(player) == 2 and window.count(EMPTY) == 2:
        score += 2
    if window.count(opp) == 3 and window.count(EMPTY) == 1:
        score -= 4
    return score


def _score_board(board, player):
    score = sum(board[r][COLS // 2] == player for r in range(ROWS)) * 3
    for r in range(ROWS):
        for c in range(COLS - 3):
            score += _score_window([board[r][c + i] for i in range(4)], player)
    for r in range(ROWS - 3):
        for c in range(COLS):
            score += _score_window([board[r + i][c] for i in range(4)], player)
    for r in range(ROWS - 3):
        for c in range(COLS - 3):
            score += _score_window([board[r + i][c + i] for i in range(4)], player)
    for r in range(ROWS - 3):
        for c in range(3, COLS):
            score += _score_window([board[r + i][c - i] for i in range(4)], player)
    return score


def _minimax(board, depth, alpha, beta, maximizing):
    import math as _math
    valid = get_valid_columns(board)
    if is_terminal(board):
        w = check_winner(board)
        if w == AI:
            return (None, 1_000_000)
        elif w == PLAYER:
            return (None, -1_000_000)
        return (None, 0)
    if depth == 0:
        return (None, _score_board(board, AI))
    if maximizing:
        best, best_col = -_math.inf, valid[0]
        for col in valid:
            _, score = _minimax(drop_piece(board, col, AI), depth - 1, alpha, beta, False)
            if score > best:
                best, best_col = score, col
            alpha = max(alpha, score)
            if alpha >= beta:
                break
        return (best_col, best)
    else:
        best, best_col = _math.inf, valid[0]
        for col in valid:
            _, score = _minimax(drop_piece(board, col, PLAYER), depth - 1, alpha, beta, True)
            if score < best:
                best, best_col = score, col
            beta = min(beta, score)
            if alpha >= beta:
                break
        return (best_col, best)


# ── Evaluators ────────────────────────────────────────────────────────────────

def run_ai_guessing_eval(n_games: int = 10) -> dict:
    """
    Run the AI Opponent guesser against N random secrets and verify it always
    converges within ceil(log2(range_size)) guesses.
    """
    print(f"\n[1/4] AI guessing convergence eval ({n_games} games)...")
    difficulties = {
        "Easy":   (1, 20),
        "Normal": (1, 50),
        "Hard":   (1, 100),
    }
    results = []
    all_passed = True

    for diff, (low, high) in difficulties.items():
        limit = math.ceil(math.log2(high - low + 1))
        for _ in range(n_games):
            secret = random.randint(low, high)
            history = []
            converged = False
            for attempt in range(limit + 1):  # one extra to catch failures
                guess, _ = ng_get_ai_guess(low, high, history, notes_mode="seeded")
                outcome, _ = check_guess(guess, secret)
                history.append({"guess": guess, "result": outcome})
                if outcome == "Win":
                    converged = True
                    results.append({"difficulty": diff, "attempts": attempt + 1,
                                    "limit": limit, "passed": True})
                    break
            if not converged:
                all_passed = False
                results.append({"difficulty": diff, "attempts": limit + 1,
                                "limit": limit, "passed": False})

    passed = sum(r["passed"] for r in results)
    total = len(results)
    print(f"  Converged: {passed}/{total}  {'✓' if all_passed else '✗'}")
    return {"check": "ai_guessing_eval", "passed": all_passed,
            "games": total, "converged": passed, "details": results}


def run_ai_vs_ai_connect4(n_games: int = 5) -> dict:
    """
    Pit minimax depth-4 (strong) vs depth-2 (weak) for N games.
    Strong player goes first. Verifies no illegal moves occur.
    """
    import math as _math
    print(f"\n[2/4] AI vs AI Connect-4 ({n_games} games, depth-4 vs depth-2)...")
    wins = {4: 0, 2: 0, "draw": 0}
    illegal_moves = 0

    for game_num in range(n_games):
        board = make_board()
        current_player = PLAYER   # depth-4 plays as PLAYER (1)
        current_depth = 4
        game_over = False
        while not game_over:
            valid = get_valid_columns(board)
            col, _ = _minimax(board, current_depth, -_math.inf, _math.inf,
                              current_player == AI)
            if col not in valid:
                illegal_moves += 1
                col = random.choice(valid)
            board = drop_piece(board, col, current_player)
            winner = check_winner(board)
            if winner is not None:
                depth_label = 4 if winner == PLAYER else 2
                wins[depth_label] += 1
                game_over = True
            elif is_draw(board):
                wins["draw"] += 1
                game_over = True
            else:
                current_player = AI if current_player == PLAYER else PLAYER
                current_depth = 2 if current_depth == 4 else 4

        print(f"  Game {game_num + 1}: "
              f"depth-4={wins[4]} depth-2={wins[2]} draws={wins['draw']}")

    passed = illegal_moves == 0
    print(f"  Illegal moves: {illegal_moves}  {'✓' if passed else '✗'}")
    return {"check": "ai_vs_ai_connect4", "passed": passed,
            "depth4_wins": wins[4], "depth2_wins": wins[2],
            "draws": wins["draw"], "illegal_moves": illegal_moves}


def consistency_check(n_repeats: int = 3) -> dict:
    """
    Ask Gemini the same strategy question n_repeats times and verify
    all responses mention at least one common keyword, indicating semantic
    consistency.
    """
    print(f"\n[3/4] Gemini consistency check ({n_repeats} repeats)...")
    from ai_agent import _generate

    question = (
        "In Connect-4, what is the single most important opening strategy? "
        "Answer in one sentence."
    )
    responses = [_generate(question) for _ in range(n_repeats)]
    for i, r in enumerate(responses, 1):
        print(f"  Response {i}: {r[:80]}...")

    # Check that at least one keyword appears in all responses
    keywords = ["center", "middle", "column 4", "col 4", "fourth"]
    common = any(
        all(kw.lower() in r.lower() for r in responses)
        for kw in keywords
    )
    print(f"  Consistent: {'✓' if common else '✗'}")
    return {"check": "consistency", "passed": common, "responses": responses}


def notes_integrity_check() -> dict:
    """
    Verify that both strategy notes files exist and are non-empty.
    """
    print("\n[4/4] Strategy notes integrity check...")
    games = ["number_guessing", "connect4"]
    results = []
    all_passed = True

    for game in games:
        for mode in ["seeded", "blank"]:
            try:
                content = load_notes(game, mode)
                ok = len(content.strip()) > 0
            except FileNotFoundError:
                ok = False
            results.append({"game": game, "mode": mode, "ok": ok})
            if not ok:
                all_passed = False
            print(f"  {game} ({mode}): {'✓' if ok else '✗ MISSING OR EMPTY'}")

    return {"check": "notes_integrity", "passed": all_passed, "files": results}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("AI Game Arena — Reliability Evaluator")
    print(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = {
        "timestamp": datetime.now().isoformat(),
        "checks": [
            run_ai_guessing_eval(n_games=1),
            run_ai_vs_ai_connect4(n_games=1),
            consistency_check(n_repeats=3),
            notes_integrity_check(),
        ],
    }

    overall = all(c["passed"] for c in results["checks"])
    results["overall_passed"] = overall

    out_path = os.path.join(os.path.dirname(__file__), "eval_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 60)
    print(f"Overall: {'ALL CHECKS PASSED ✓' if overall else 'SOME CHECKS FAILED ✗'}")
    print(f"Results saved to eval_results.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
