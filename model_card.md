# Reflection and Ethics

## Potential Limitations and Biases in the system

The system's strategy notes are seeded with conventional wisdom about each game, so the AI's advice reflects mainstream strategy rather than creative or unconventional play. If the seed notes contain an incorrect assumption, the agent will repeat and reinforce it across every game. The retrieval step also depends on Gemini to judge relevance, which means the quality of what gets retrieved varies, so the same board state can produce different excerpts across runs, making the advice inconsistent in subtle ways. In Opponent mode for number guessing, the AI occasionally ignores its own history and guesses outside the known valid range, suggesting the model sometimes fails to follow the structured prompt format reliably.

## Potential for misuse and its prevention

The system's attack surface is narrow, it plays games and writes to local markdown files, so misuse risk is low. The main concern is prompt injection: a player could craft a guess or game input designed to manipulate the AI's response. The guardrails partially address this by rejecting responses that don't match expected formats (a move must contain a digit, a notes update must be deemed novel), but they don't explicitly sanitise inputs before they enter prompts. A more robust version could strip or escape user-provided strings before including them in any LLM prompt. The notes update guardrail also prevents the AI from overwriting existing strategy knowledge, which limits one way of corrupting the knowledge base.

## What surprised me while testing my AI's reliability

The most surprising finding was how sensitive the notes update pipeline was to response formatting. The guardrail was written to check if Gemini's verdict was exactly "APPROVED", but Gemini frequently returns something like "APPROVED. This is novel and adds value.", causing valid approvals to be silently rejected. The system appeared to work (no errors, no crashes), but the strategy notes simply never grew. This kind of silent failure is much harder to catch than an exception, and it was only discovered by inspecting guardrails.log directly. It showed that testing AI-integrated systems requires checking the effects of AI calls, not just whether the calls succeed.

## My collaboration with AI during the project

I used Claude Code as a development partner throughout, handling most of the code writing and implementation while I directed architecture decisions, reviewed changes before applying them, and tested the running system manually.

One helpful suggestion was identifying that the guardrail was silently rejecting all valid notes updates. The check was written as verdict == "APPROVED", but Gemini frequently returns responses like "APPROVED. This is novel and adds value.", causing every approval to fail the exact-match check. The strategy notes never grew and no error was raised, so it was only discoverable by inspecting guardrails.log directly. Changing the check to startswith("APPROVED") unblocked the entire pipeline.

One flawed suggestion was placing st.balloons() inside the game-over block to celebrate a player win. Because that block re-renders on every Streamlit rerun while the game status is "won", balloons fired again every time the user interacted with the sidebar, such as switching notes mode or AI model. A session state flag (ng_balloons_shown) was needed to make the balloons fire exactly once per win, which should have been the design from the start.
