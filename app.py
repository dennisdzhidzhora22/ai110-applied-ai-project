import random
import streamlit as st
from logic_utils import get_range_for_difficulty, parse_guess, check_guess, update_score
from connect4_logic import (
    make_board, drop_piece, get_valid_columns,
    check_winner, is_draw, PLAYER, AI, EMPTY, COLS,
)

st.set_page_config(page_title="AI Game Arena", page_icon="🎮")
st.title("🎮 AI Game Arena")

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.header("Settings")
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

    st.subheader("Make a guess")

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
        st.session_state.attempts = 0
        # FIX: had a hardcoded randint(1, 100). spotted and fixed by myself
        st.session_state.secret = random.randint(low, high)
        # FIX: status is not being reset, leading to game stopping instead of
        # restarting. spotted by claude code and fixed by me
        st.session_state.status = "playing"
        st.success("New game started.")
        st.rerun()

    if st.session_state.status != "playing":
        # Game already finished — show result and skip the active-game UI.
        # Replaced original st.stop() here, which would have blocked tab 2
        # from rendering.
        if st.session_state.status == "won":
            st.success("You already won. Start a new game to play again.")
        else:
            st.error("Game over. Start a new game to try again.")
    else:
        if submit:
            st.session_state.attempts += 1

            ok, guess_int, err = parse_guess(raw_guess)

            if not ok:
                st.session_state.history.append(raw_guess)
                st.error(err)
            else:
                st.session_state.history.append(guess_int)

                # FIX: sets up an issue further down the line with secret
                # becoming a string, causing incorrect lexicographical comparison
                # in check_guess(). reported by me, found and fixed by claude code.
                secret = st.session_state.secret

                outcome, message = check_guess(guess_int, secret)

                if show_hint:
                    st.warning(message)

                st.session_state.score = update_score(
                    current_score=st.session_state.score,
                    outcome=outcome,
                    attempt_number=st.session_state.attempts,
                )

                if outcome == "Win":
                    st.balloons()
                    st.session_state.status = "won"
                    st.success(
                        f"You won! The secret was {st.session_state.secret}. "
                        f"Final score: {st.session_state.score}"
                    )
                else:
                    if st.session_state.attempts >= attempt_limit:
                        st.session_state.status = "lost"
                        st.error(
                            f"Out of attempts! "
                            f"The secret was {st.session_state.secret}. "
                            f"Score: {st.session_state.score}"
                        )

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
            hcol.markdown(f"<div style='text-align:center'><b>{i + 1}</b></div>", unsafe_allow_html=True)
        for row in board:
            row_cols = st.columns(COLS)
            for cell, rcol in zip(row, row_cols):
                rcol.markdown(f"<div style='text-align:center'>{symbols[cell]}</div>", unsafe_allow_html=True)

        if st.session_state.c4_status == "playing":
            if st.session_state.c4_turn == PLAYER:
                st.write("**Your turn** 🔴 — pick a column:")
                valid = get_valid_columns(board)
                btn_cols = st.columns(COLS)
                for i, bcol in enumerate(btn_cols):
                    with bcol:
                        if st.button(str(i + 1), key=f"c4_col_{i}", disabled=(i not in valid)):
                            st.session_state.c4_board = drop_piece(board, i, PLAYER)
                            winner = check_winner(st.session_state.c4_board)
                            if winner == PLAYER:
                                st.session_state.c4_status = "player_won"
                            elif is_draw(st.session_state.c4_board):
                                st.session_state.c4_status = "draw"
                            else:
                                st.session_state.c4_turn = AI
                            st.rerun()
            else:
                # AI turn — random placeholder until ai_agent is wired in
                valid = get_valid_columns(board)
                if valid:
                    ai_col = random.choice(valid)
                    st.session_state.c4_board = drop_piece(board, ai_col, AI)
                    winner = check_winner(st.session_state.c4_board)
                    if winner == AI:
                        st.session_state.c4_status = "ai_won"
                    elif is_draw(st.session_state.c4_board):
                        st.session_state.c4_status = "draw"
                    else:
                        st.session_state.c4_turn = PLAYER
                    st.rerun()

    if st.session_state.c4_status == "player_won":
        st.success("You win! 🎉")
    elif st.session_state.c4_status == "ai_won":
        st.error("AI wins! Better luck next time.")
    elif st.session_state.c4_status == "draw":
        st.warning("It's a draw!")

    if st.button("New Game", key="c4_new_game"):
        st.session_state.c4_board = make_board()
        st.session_state.c4_turn = PLAYER
        st.session_state.c4_status = "playing"
        st.rerun()

    st.divider()
    st.caption("🔴 You   🟡 AI")
