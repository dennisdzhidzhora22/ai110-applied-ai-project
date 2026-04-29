import random
import streamlit as st
import config
import ai_agent
from logic_utils import get_range_for_difficulty, parse_guess, check_guess, update_score
from connect4_logic import (
    make_board, drop_piece, get_valid_columns,
    check_winner, is_draw, board_to_str, PLAYER, AI, EMPTY, COLS,
)
from ai_agent import (
    c4_get_ai_move, c4_get_teacher_hint,
    ng_get_ai_guess, ng_get_teacher_hint,
    run_post_game,
)

st.set_page_config(page_title="AI Game Arena", page_icon="🎮")
st.title("🎮 AI Game Arena")

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.header("Settings")

ai_mode = st.sidebar.radio("AI Mode", ["Off", "Teacher", "Opponent"], horizontal=True)

notes_mode = "seeded"
if ai_mode != "Off":
    notes_label = st.sidebar.radio(
        "Strategy Notes",
        ["Seeded", "Blank"],
        horizontal=True,
        help="Seeded: AI starts with built-in knowledge. Blank: watch knowledge build from scratch.",
    )
    notes_mode = notes_label.lower()

    model_label = st.sidebar.radio(
        "AI Model",
        ["Flash Lite (fast)", "Flash (accurate)"],
        horizontal=True,
        help="Flash Lite: faster responses. Flash: higher quality reasoning.",
    )
    config.GEMINI_MODEL = (
        "gemini-2.5-flash" if model_label == "Flash (accurate)" else "gemini-2.5-flash-lite"
    )

difficulty = st.sidebar.selectbox(
    "Difficulty (Number Guessing)",
    ["Easy", "Normal", "Hard"],
    index=1,
)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["🔢 Number Guessing", "🔴 Connect-4"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — NUMBER GUESSING
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    # FIX: attempt numbers were not in logical order, normal count (8) was larger
    # than easy count (6). refactored with claude code
    attempt_limit_map = {"Easy": 8, "Normal": 6, "Hard": 5}
    attempt_limit = attempt_limit_map[difficulty]

    low, high = get_range_for_difficulty(difficulty)

    st.sidebar.caption(f"Range: {low} to {high}")
    st.sidebar.caption(f"Attempts allowed: {attempt_limit}")

    # FIX: switching difficulty didn't reset the game state. found by me,
    # difficulty tracking added by claude code
    if "difficulty" not in st.session_state:
        st.session_state.difficulty = difficulty

    if st.session_state.difficulty != difficulty:
        st.session_state.difficulty = difficulty
        st.session_state.secret = random.randint(low, high)
        st.session_state.attempts = 0
        st.session_state.score = 0
        st.session_state.status = "playing"
        st.session_state.history = []
        st.session_state.ng_eff_low = low
        st.session_state.ng_eff_high = high
        st.session_state.ng_teacher_hint = ""
        st.session_state.ng_ai_history = []
        st.session_state.ng_ai_score = 0
        st.session_state.ng_round_display = []
        st.session_state.ng_post_game_run = False
        st.session_state.ng_balloons_shown = False

    if "secret" not in st.session_state:
        st.session_state.secret = random.randint(low, high)

    # FIX: number of attempts set to 1 instead of 0 on the very first game.
    # issue noticed by me and claude code found the exact location of the bug
    if "attempts" not in st.session_state:
        st.session_state.attempts = 0
    if "score" not in st.session_state:
        st.session_state.score = 0
    if "status" not in st.session_state:
        st.session_state.status = "playing"
    if "history" not in st.session_state:
        st.session_state.history = []

    # ── AI mode session state ─────────────────────────────────────────────────
    if "ng_stored_ai_mode" not in st.session_state:
        st.session_state.ng_stored_ai_mode = ai_mode
    if "ng_ai_history" not in st.session_state:
        st.session_state.ng_ai_history = []       # competitive: AI's guess history
    if "ng_ai_score" not in st.session_state:
        st.session_state.ng_ai_score = 0
    if "ng_round_display" not in st.session_state:
        st.session_state.ng_round_display = []    # competitive: per-round results
    if "ng_teacher_hint" not in st.session_state:
        st.session_state.ng_teacher_hint = ""
    if "ng_post_game_run" not in st.session_state:
        st.session_state.ng_post_game_run = False
    if "ng_balloons_shown" not in st.session_state:
        st.session_state.ng_balloons_shown = False
    if "ng_eff_low" not in st.session_state:
        st.session_state.ng_eff_low = low
    if "ng_eff_high" not in st.session_state:
        st.session_state.ng_eff_high = high

    # Reset AI state when mode changes
    if st.session_state.ng_stored_ai_mode != ai_mode:
        st.session_state.ng_stored_ai_mode = ai_mode
        st.session_state.ng_ai_history = []
        st.session_state.ng_ai_score = 0
        st.session_state.ng_round_display = []
        st.session_state.ng_teacher_hint = ""
        st.session_state.ng_post_game_run = False

    # ── UI ────────────────────────────────────────────────────────────────────
    st.subheader("Make a guess")

    if ai_mode == "Opponent":
        score_col1, score_col2 = st.columns(2)
        score_col1.metric("Your Score", st.session_state.score)
        score_col2.metric("AI Score", st.session_state.ng_ai_score)

    with st.expander("Developer Debug Info"):
        st.write("Secret:", st.session_state.secret)
        st.write("Attempts:", st.session_state.attempts)
        st.write("Score:", st.session_state.score)
        st.write("Difficulty:", difficulty)
        st.write("History:", st.session_state.history)

    raw_guess = st.text_input("Enter your guess:", key=f"guess_input_{difficulty}")

    col1, col2, col3 = st.columns(3)
    with col1:
        submit = st.button("Submit Guess 🚀")
    with col2:
        new_game = st.button("New Game 🔁")
    with col3:
        show_hint = st.checkbox("Show hint", value=True)

    if new_game:
        ai_agent._trace.clear()
        st.session_state.ng_balloons_shown = False
        st.session_state.attempts = 0
        # FIX: had a hardcoded randint(1, 100). spotted and fixed by myself
        st.session_state.secret = random.randint(low, high)
        # FIX: status is not being reset, leading to game stopping instead of
        # restarting. spotted by claude code and fixed by me
        st.session_state.status = "playing"
        st.session_state.history = []
        st.session_state.score = 0
        st.session_state.ng_ai_history = []
        st.session_state.ng_ai_score = 0
        st.session_state.ng_round_display = []
        st.session_state.ng_teacher_hint = ""
        st.session_state.ng_post_game_run = False
        st.session_state.ng_eff_low = low
        st.session_state.ng_eff_high = high
        st.success("New game started.")
        st.rerun()

    if st.session_state.status != "playing":
        # Game already finished — show result and skip the active-game UI.
        # (Replaced original st.stop() which would have blocked tab 2 from rendering.)
        if st.session_state.status == "won":
            if not st.session_state.ng_balloons_shown:
                st.balloons()
                st.session_state.ng_balloons_shown = True
            st.success(
                f"You won! The secret was {st.session_state.secret}. "
                f"Final score: {st.session_state.score}. Start a new game to play again."
            )
        elif st.session_state.status == "ai_won":
            st.error("AI guessed it first! Start a new game to try again.")
        else:
            if ai_mode == "Opponent":
                if st.session_state.score > st.session_state.ng_ai_score:
                    st.warning("Out of attempts — but you had the higher score! 🏆")
                elif st.session_state.score < st.session_state.ng_ai_score:
                    st.error("Out of attempts — AI had the higher score.")
                else:
                    st.warning("Out of attempts — it's a tie on score!")
            else:
                st.error("Game over. Start a new game to try again.")

        # Post-game insight (runs once after game ends)
        if ai_mode != "Off" and not st.session_state.ng_post_game_run:
            outcome_str = (
                "Human won" if st.session_state.status == "won"
                else "AI won" if st.session_state.status == "ai_won"
                else "Nobody guessed correctly"
            )
            summary = (
                f"{outcome_str}. Secret was {st.session_state.secret}. "
                f"Human took {st.session_state.attempts} attempts "
                f"(score {st.session_state.score}). "
                f"AI score: {st.session_state.ng_ai_score}."
            )
            try:
                with st.spinner("Reflecting on this game..."):
                    updated = run_post_game("number_guessing", summary, notes_mode)
                if updated:
                    st.info("📝 Strategy notes updated with a new insight from this game.")
            except Exception:
                st.warning("Could not generate post-game insight — AI service temporarily unavailable.")
            st.session_state.ng_post_game_run = True

    else:
        # ── Active game ───────────────────────────────────────────────────────
        if submit:
            st.session_state.attempts += 1

            ok, guess_int, err = parse_guess(raw_guess)

            if not ok:
                st.session_state.history.append(raw_guess)
                st.error(err)
            else:
                st.session_state.history.append(guess_int)

                # FIX: sets up an issue with secret becoming a string, causing
                # incorrect lexicographical comparison in check_guess().
                # reported by me, found and fixed by claude code.
                secret = st.session_state.secret
                outcome, message = check_guess(guess_int, secret)

                if show_hint:
                    st.warning(message)

                st.session_state.score = update_score(
                    current_score=st.session_state.score,
                    outcome=outcome,
                    attempt_number=st.session_state.attempts,
                )

                # Update effective bounds for teacher hint
                if outcome == "Too High":
                    st.session_state.ng_eff_high = min(
                        st.session_state.ng_eff_high, guess_int - 1
                    )
                elif outcome == "Too Low":
                    st.session_state.ng_eff_low = max(
                        st.session_state.ng_eff_low, guess_int + 1
                    )

                # Teacher mode: get coaching hint
                if ai_mode == "Teacher" and outcome != "Win":
                    try:
                        with st.spinner("AI coach thinking..."):
                            hint = ng_get_teacher_hint(
                                guess_int, outcome,
                                st.session_state.ng_eff_low,
                                st.session_state.ng_eff_high,
                                st.session_state.attempts,
                                notes_mode,
                            )
                        st.session_state.ng_teacher_hint = hint
                    except Exception:
                        st.warning("AI Coach is temporarily unavailable — please try again.")

                # Opponent mode: AI also makes a guess this round
                if ai_mode == "Opponent" and outcome != "Win":
                    try:
                        with st.spinner("AI is guessing..."):
                            ai_guess, ai_explanation = ng_get_ai_guess(
                                low, high,
                                st.session_state.ng_ai_history,
                                notes_mode,
                            )
                    except Exception:
                        st.error("AI service unavailable — using midpoint fallback.")
                        ai_guess = (st.session_state.ng_eff_low + st.session_state.ng_eff_high) // 2
                        ai_explanation = f"[Unavailable] Falling back to {ai_guess}."
                    ai_outcome, _ = check_guess(ai_guess, secret)
                    st.session_state.ng_ai_score = update_score(
                        current_score=st.session_state.ng_ai_score,
                        outcome=ai_outcome,
                        attempt_number=st.session_state.attempts,
                    )
                    st.session_state.ng_ai_history.append(
                        {"guess": ai_guess, "result": ai_outcome}
                    )
                    st.session_state.ng_round_display.append({
                        "round": st.session_state.attempts,
                        "human_guess": guess_int,
                        "human_result": outcome,
                        "ai_guess": ai_guess,
                        "ai_result": ai_outcome,
                        "ai_explanation": ai_explanation,
                    })
                    if ai_outcome == "Win":
                        st.session_state.status = "ai_won"

                # Check human win / loss
                if outcome == "Win":
                    st.session_state.status = "won"
                    st.rerun()
                elif st.session_state.status != "ai_won":
                    if st.session_state.attempts >= attempt_limit:
                        st.session_state.status = "lost"
                        st.rerun()

                if st.session_state.status == "ai_won":
                    st.rerun()

        # Teacher hint display (persists until next guess)
        if ai_mode == "Teacher" and st.session_state.ng_teacher_hint:
            st.info(f"🧑‍🏫 Coach: {st.session_state.ng_teacher_hint}")

        # Competitive round history display
        if ai_mode == "Opponent" and st.session_state.ng_round_display:
            st.markdown("**Round history:**")
            h_col, a_col = st.columns(2)
            h_col.markdown("**You**")
            a_col.markdown("**AI**")
            for rd in st.session_state.ng_round_display:
                h_col.write(
                    f"Round {rd['round']}: guessed **{rd['human_guess']}** — {rd['human_result']}"
                )
                a_col.write(
                    f"Round {rd['round']}: guessed **{rd['ai_guess']}** — {rd['ai_result']}"
                )
                a_col.caption(rd["ai_explanation"])

        # FIX: number of attempts left was updated only after it was displayed,
        # causing games to end with 1 remaining attempt displayed. moved past
        # submit handler to display after updating. reported by me, found and
        # fixed by claude code
        st.info(
            # FIX: was hardcoded as "between 1 and 100" regardless of difficulty.
            # spotted and fixed by claude code
            f"Guess a number between {low} and {high}. "
            f"Attempts left: {attempt_limit - st.session_state.attempts}"
        )

    if ai_mode != "Off" and ai_agent._trace.get("game") == "number_guessing":
        with st.expander("🔍 Agent Trace"):
            t = ai_agent._trace
            st.markdown("**Step 1 — RAG retrieval**")
            if t.get("retrieval_query"):
                st.caption(f"Query: {t['retrieval_query']}")
            retrieved = t.get("retrieved_notes", "")
            if retrieved:
                st.info(retrieved)
            else:
                st.warning("No notes retrieved — notes are empty or not yet populated.")
            st.markdown(f"**Step 2 — Persona:** {t.get('persona', '—')} mode")
            if t.get("persona_text"):
                st.caption(t["persona_text"])
            st.markdown("**Step 3 — Gemini called** (response shown above)")
            st.markdown(f"**Step 4 — Validation:** {t.get('validation', 'pending')}")
            if "notes_updated" in t:
                st.markdown(f"**Step 5 — Notes update:** {t.get('post_game', '—')}")
                if t.get("post_game_insight"):
                    st.caption(f"Insight: {t['post_game_insight'][:200]}")

    st.divider()
    st.caption("Built by an AI that claims this code is production-ready.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CONNECT-4
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    # c4_ prefix on all session state keys to avoid collisions with tab 1
    if "c4_board" not in st.session_state:
        st.session_state.c4_board = make_board()
    if "c4_turn" not in st.session_state:
        st.session_state.c4_turn = PLAYER
    if "c4_status" not in st.session_state:
        st.session_state.c4_status = "playing"
    if "c4_last_commentary" not in st.session_state:
        st.session_state.c4_last_commentary = ""
    if "c4_post_game_run" not in st.session_state:
        st.session_state.c4_post_game_run = False
    if "c4_ai_thinking" not in st.session_state:
        st.session_state.c4_ai_thinking = False
    if "c4_pending_hint_col" not in st.session_state:
        st.session_state.c4_pending_hint_col = None
    if "c4_stored_ai_mode" not in st.session_state:
        st.session_state.c4_stored_ai_mode = ai_mode

    if st.session_state.c4_stored_ai_mode != ai_mode:
        st.session_state.c4_stored_ai_mode = ai_mode
        st.session_state.c4_last_commentary = ""

    board = st.session_state.c4_board

    # Narrow container so the 7-column board grid doesn't stretch full page width.
    # Adjust the [2, 3] ratio if the board looks too narrow or too wide.
    board_col, _ = st.columns([2, 3])
    with board_col:
        # Board display — header and rows share the same column grid as the
        # drop buttons so all three layers are pixel-aligned.
        symbols = {EMPTY: "⚫", PLAYER: "🔴", AI: "🟡"}
        header_cols = st.columns(COLS)
        for i, hcol in enumerate(header_cols):
            hcol.markdown(
                f"<div style='text-align:center'><b>{i + 1}</b></div>",
                unsafe_allow_html=True,
            )
        for row in board:
            row_cols = st.columns(COLS)
            for cell, rcol in zip(row, row_cols):
                rcol.markdown(
                    f"<div style='text-align:center'>{symbols[cell]}</div>",
                    unsafe_allow_html=True,
                )

        if st.session_state.c4_status == "playing":
            if st.session_state.c4_turn == PLAYER:
                st.write("**Your turn** 🔴 — pick a column:")
                valid = get_valid_columns(board)
                clicked_col = None
                btn_cols = st.columns(COLS)
                for i, bcol in enumerate(btn_cols):
                    with bcol:
                        if st.button(str(i + 1), key=f"c4_col_{i}", disabled=(i not in valid)):
                            clicked_col = i

                if clicked_col is not None:
                    new_board = drop_piece(board, clicked_col, PLAYER)
                    st.session_state.c4_board = new_board
                    winner = check_winner(new_board)
                    if winner == PLAYER:
                        st.session_state.c4_status = "player_won"
                    elif is_draw(new_board):
                        st.session_state.c4_status = "draw"
                    else:
                        st.session_state.c4_turn = AI
                        if ai_mode == "Teacher":
                            st.session_state.c4_ai_thinking = True
                            st.session_state.c4_pending_hint_col = clicked_col
                    st.rerun()
            else:
                # AI's turn — column buttons are hidden here, safe to call API
                if st.session_state.c4_ai_thinking and ai_mode == "Teacher":
                    try:
                        with st.spinner("AI Coach is thinking..."):
                            hint = c4_get_teacher_hint(
                                board, st.session_state.c4_pending_hint_col, notes_mode
                            )
                        st.session_state.c4_last_commentary = hint
                    except Exception:
                        st.warning("AI Coach is temporarily unavailable — please try again.")
                    st.session_state.c4_ai_thinking = False
                    st.session_state.c4_pending_hint_col = None

                if ai_mode == "Opponent":
                    try:
                        with st.spinner("AI thinking..."):
                            ai_col, explanation = c4_get_ai_move(board, notes_mode)
                        st.session_state.c4_last_commentary = explanation
                    except Exception:
                        st.error("AI service unavailable — making a random move.")
                        ai_col = random.choice(get_valid_columns(board))
                        st.session_state.c4_last_commentary = ""
                else:
                    # Teacher or Off mode — random move
                    valid = get_valid_columns(board)
                    ai_col = random.choice(valid)
                    if ai_mode != "Teacher":
                        st.session_state.c4_last_commentary = ""

                new_board = drop_piece(st.session_state.c4_board, ai_col, AI)
                st.session_state.c4_board = new_board
                winner = check_winner(new_board)
                if winner == AI:
                    st.session_state.c4_status = "ai_won"
                elif is_draw(new_board):
                    st.session_state.c4_status = "draw"
                else:
                    st.session_state.c4_turn = PLAYER
                st.rerun()

    # AI commentary (teacher hint or opponent move explanation)
    if st.session_state.c4_last_commentary:
        icon = "🧑‍🏫" if ai_mode == "Teacher" else "🟡"
        st.info(f"{icon} {st.session_state.c4_last_commentary}")

    # Game-over messages
    if st.session_state.c4_status == "player_won":
        st.success("You win! 🎉")
    elif st.session_state.c4_status == "ai_won":
        st.error("AI wins! Better luck next time.")
    elif st.session_state.c4_status == "draw":
        st.warning("It's a draw!")

    # Post-game insight (runs once)
    if st.session_state.c4_status != "playing" and ai_mode != "Off" and not st.session_state.c4_post_game_run:
        num_moves = sum(cell != EMPTY for row in board for cell in row)
        player_moves = sum(cell == PLAYER for row in board for cell in row)
        ai_moves = sum(cell == AI for row in board for cell in row)
        outcome_str = (
            "Player won" if st.session_state.c4_status == "player_won"
            else "AI won" if st.session_state.c4_status == "ai_won"
            else "Draw"
        )
        summary = (
            f"{outcome_str} in {num_moves} total moves "
            f"(player: {player_moves}, AI: {ai_moves}). "
            f"Final board:\n{board_to_str(board)}"
        )
        try:
            with st.spinner("Reflecting on this game..."):
                updated = run_post_game("connect4", summary, notes_mode)
            if updated:
                st.info("📝 Strategy notes updated with a new insight from this game.")
        except Exception:
            st.warning("Could not generate post-game insight — AI service temporarily unavailable.")
        st.session_state.c4_post_game_run = True

    if ai_mode != "Off" and ai_agent._trace.get("game") == "connect4":
        with st.expander("🔍 Agent Trace"):
            t = ai_agent._trace
            st.markdown("**Step 1 — RAG retrieval**")
            if t.get("retrieval_query"):
                st.caption(f"Query: {t['retrieval_query']}")
            retrieved = t.get("retrieved_notes", "")
            if retrieved:
                st.info(retrieved)
            else:
                st.warning("No notes retrieved — notes are empty or not yet populated.")
            st.markdown(f"**Step 2 — Persona:** {t.get('persona', '—')} mode")
            if t.get("persona_text"):
                st.caption(t["persona_text"])
            st.markdown("**Step 3 — Gemini called** (response shown above)")
            st.markdown(f"**Step 4 — Validation:** {t.get('validation', 'pending')}")
            if "notes_updated" in t:
                st.markdown(f"**Step 5 — Notes update:** {t.get('post_game', '—')}")
                if t.get("post_game_insight"):
                    st.caption(f"Insight: {t['post_game_insight'][:200]}")

    if st.button("New Game", key="c4_new_game"):
        ai_agent._trace.clear()
        st.session_state.c4_board = make_board()
        st.session_state.c4_turn = PLAYER
        st.session_state.c4_status = "playing"
        st.session_state.c4_last_commentary = ""
        st.session_state.c4_post_game_run = False
        st.session_state.c4_ai_thinking = False
        st.session_state.c4_pending_hint_col = None
        st.rerun()

    st.divider()
    st.caption("🔴 You   🟡 AI")
