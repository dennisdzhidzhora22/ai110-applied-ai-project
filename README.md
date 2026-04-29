# AI Game Arena

[Video Link](https://youtu.be/AMSFDhRkjqk)

This project extends **Game Glitch Investigator: The Impossible Guesser**, a Streamlit number guessing game that was intentionally shipped with multiple bugs. The original goal was to find and fix those bugs, covering incorrect hint directions, broken scoring, state reset failures, and difficulty inconsistencies, while learning how Streamlit session state works and practicing AI-assisted debugging.

## Title and Summary

**AI Game Arena** is a two-game AI-powered platform built on top of the fixed number guessing game. It adds a fully playable Connect-4 game and integrates a Gemini-powered AI agent that can act as either a **Teacher** (giving Socratic coaching hints after each move) or an **Opponent** (competing directly against the player). The agent uses a persistent strategy knowledge base that grows from game to game, making it a live demonstration of Retrieval-Augmented Generation, agentic workflows, and LLM guardrails working together in a real application.

## Architecture Overview

These are the main layers of the system:

- **Streamlit UI (`app.py`)** - tab-based interface for both games. Sidebar controls AI mode, notes mode, and model selection.
- **Game Logic (`logic_utils.py`, `connect4_logic.py`)** - pure Python, no AI. Handles board state, move validation, win detection, and scoring.
- **AI Agent (`ai_agent.py`)** - orchestrates a five-step agentic workflow per move: 1. retrieve relevant strategy notes, 2. build a persona-specific prompt, 3. call Gemini, 4. validate the response via guardrails, 5. post-game: generate an insight and update the notes if approved.
- **RAG Layer (`strategy_notes.py`)** - loads and retrieves from per-game markdown knowledge bases (`strategy_notes/*.md`). Notes are seeded with strategy content and grow as the agent learns from completed games. A "blank" mode starts from empty headers to make the growth visible.
- **Guardrails (`guardrails.py`)** - validates that AI-suggested moves are legal and that proposed note additions are novel and non-destructive before accepting them. All decisions are logged to `guardrails.log`.
- **Config (`config.py`)** - centralises the Gemini client, model selection (Flash Lite or Flash), and automatic retry logic for transient API errors.
- **Evaluator (`evaluator.py`)** - standalone reliability script: tests AI guessing convergence, minimax AI-vs-AI correctness, Gemini response consistency, and notes file integrity.

An **Agent Trace** expander in the UI makes every intermediate step visible during gameplay - the retrieved notes excerpt, the active persona, the validation result, and the post-game insight, directly demonstrating the RAG and agentic workflow in action.

## Setup Instructions

1. **Clone the repo and install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Add your Gemini API key** — create a `.env` file in the project root:
   ```
   GEMINI_API_KEY=your_key_here
   ```

3. **Run the app:**
   ```bash
   streamlit run app.py
   ```

4. **Run the test suite:**
   ```bash
   pytest tests/
   ```

5. **Run the reliability evaluator** (requires API key):
   ```bash
   python evaluator.py
   ```
   Results are saved to `eval_results.json`.

## Sample Interactions

**Example 1 — Number Guessing, Teacher mode, Seeded notes**

> Player guesses 50 on attempt 1 (range 1–100). Result: Too High.
>
> 🧑‍🏫 Coach: *"Good start using the midpoint - that's binary search thinking. Now that you know the answer is below 50, what's the midpoint of your new range? Try to always cut the remaining possibilities in half."*
>
> Agent Trace — Step 1 retrieved: *"Binary search is optimal: always guess the midpoint of the remaining range to halve possibilities each turn."*

**Example 2 — Connect-4, Opponent mode**

> AI plays column 4 (centre).
>
> 🟡 *"I'm taking the centre column — controlling the middle maximises the number of winning lines I can build in all four directions."*
>
> Agent Trace — Step 4 Validation: passed — column 4 is legal.

**Example 3 — Post-game Agent Trace, Blank notes mode**

> Game ends. Reflecting spinner runs.
>
> Agent Trace — Step 5 Notes update: *Notes updated ✓*
>
> Insight: *"- Playing defensively in the first three moves limited the opponent's options but left the centre uncontrolled; consider balancing blocking with centre occupation early."*
>
> `connect4_blank.md` gains a new `## Learned` section.

## Design Decisions

**Seeded vs. blank notes mode** - Two versions of each notes file are kept: one pre-seeded with correct strategy for quality AI responses, one with empty headers to make RAG growth visible during demos. This avoids the problem of needing prior games before RAG is useful.

**Gemini for retrieval** - The retrieval step calls Gemini to extract the most relevant excerpt from the notes rather than using keyword search. This is a slower method, but requires no additional infrastructure and produces more contextually appropriate excerpts.

**Guardrail design** - The notes update guard calls Gemini to judge novelty rather than using string similarity. This is more semantically accurate but adds a second API call per post-game cycle. The trade-off was accepted because correctness matters more than latency in a post-game step.

**Centralised config** - After the model name appeared in three separate files, it was moved to `config.py` with a retry wrapper to handle API errors. This also enables the sidebar model selector to switch models at runtime without touching agent code.

**No minimax in gameplay** - The Connect-4 opponent is Gemini-powered, not minimax. Minimax exists only in `evaluator.py` as a benchmark. This keeps the gameplay AI consistent with the rest of the system and allows the agent's reasoning to be demonstrated, at the cost of a weaker opponent.

## Testing Summary

**What worked:** The 57-test pytest suite (15 original + 27 Connect-4 logic tests + 15 guardrail tests) caught real issues, most notably a type-coercion bug in `check_guess` and an off-by-one in the attempt counter. The evaluator's convergence check confirmed that Gemini's number guessing reliably stays within the binary search bound across all three difficulty levels.

**What didn't:** The notes update pipeline was initially silent, the guardrail was rejecting valid APPROVED responses because Gemini sometimes returns "APPROVED. This is novel." rather than the bare word. The fix (`startswith("APPROVED")` instead of `== "APPROVED"`) was only discoverable by inspecting `guardrails.log`. Unit tests for LLM-dependent behaviour are inherently limited because the output is non-deterministic.

**What I learned:** Testing AI-integrated systems requires a different approach than testing pure logic. The guardrail unit tests use mocked Gemini responses, which validated the decision logic but couldn't catch the response format mismatch. Integration tests, or at least careful log inspection, are necessary for anything that depends on LLM output format.

## Reflection

Building this project made the gap between "AI can write code" and "AI can build a reliable system" very concrete. The agentic workflow, RAG layer, and guardrails each work individually, but getting them to compose correctly required understanding how they interact, especially around timing (Streamlit rerenders), state persistence, and the non-determinism of LLM outputs. A very important skill wasn't just prompting, it was also knowing when to trust the AI's output and when to verify it independently. Working with Claude Code as a development partner also changed how I think about oversight. The AI caught bugs faster than I could have manually, but it also introduced subtle issues, like the balloon animation firing on every rerender, or the agent trace showing across game tabs, that required human observation to notice. The best results came from treating AI suggestions as a starting point for review, not a definitive answer.
