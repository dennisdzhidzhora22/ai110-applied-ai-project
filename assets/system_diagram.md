# AI Game Arena — System Diagram

```mermaid
%%{init: {'flowchart': {'curve': 'linear'}}}%%
flowchart LR
    Human(["Human Player"])

    subgraph UI["Streamlit UI — app.py"]
        direction TB
        GameTab["Game: Number Guessing or Connect-4"]
        ModeTab["AI Mode: Teacher / Opponent / Off"]
    end

    subgraph Games["Game Logic"]
        direction TB
        NG["Number Guessing"]
        C4["Connect-4"]
    end

    subgraph Agent["AI Agent — ai_agent.py"]
        direction TB
        A1["① Retrieve relevant strategy notes"]
        A2["② Build prompt + game state"]
        A3["③ Call Gemini → move or hint"]
        A4["④ Validate response"]
        A5["⑤ Post-game: generate insight"]
        A1 --> A2 --> A3 --> A4
    end

    subgraph LLM["Gemini 1.5 Flash — Google AI API"]
        GeminiCall["LLM Inference"]
    end

    subgraph RAG["RAG Layer — strategy_notes.py"]
        direction TB
        Retrieve["Retrieve relevant section"]
        UpdateNotes["Append new insight"]
        NotesDB[("strategy_notes/*.md")]
        Retrieve <--> NotesDB
        UpdateNotes --> NotesDB
    end

    subgraph Guard["Guardrails — guardrails.py"]
        direction TB
        ValidMove["Validate move is legal"]
        ValidNotes["Validate insight is novel"]
        GuardLog[("guardrails.log")]
        ValidMove --> GuardLog
        ValidNotes --> GuardLog
    end

    subgraph Eval["Testing & Evaluation"]
        direction TB
        Pytest["pytest (tests/)"]
        Evaluator["evaluator.py"]
        EvalOut[("eval_results.json")]
        Evaluator --> EvalOut
    end

    %% Human drives the UI
    Human --> UI
    UI --> Games
    ModeTab --> Agent

    %% Agent RAG retrieval
    A1 <--> Retrieve

    %% Agent and RAG both call Gemini
    A3 <--> GeminiCall
    Retrieve <--> GeminiCall

    %% Guardrail on move output
    A4 --> ValidMove
    ValidMove -->|"Valid — display to user"| UI
    ValidMove -->|"Invalid — retry once"| GeminiCall

    %% Post-game notes update
    A5 --> ValidNotes
    ValidNotes -->|"Novel"| UpdateNotes
    ValidNotes -->|"Redundant — discard"| GuardLog

    %% Testing hooks
    Pytest --> Games
    Pytest --> Guard
    Evaluator --> Games
    Evaluator --> GeminiCall
    Evaluator --> RAG

    %% Human reviews outputs (labelled distinctly to avoid overlay)
    Human -. "reviews eval results" .-> EvalOut
    Human -. "reviews guard log" .-> GuardLog
```

## Component Summary

| Component | File | Role |
|---|---|---|
| Streamlit UI | `app.py` | Entry point; game tabs, AI mode toggle, display |
| Number Guessing Logic | `logic_utils.py` | Parse guesses, check result, score |
| Connect-4 Logic | `connect4_logic.py` | Board, drop piece, win detection |
| AI Agent | `ai_agent.py` | Orchestrates RAG → Gemini → guardrail workflow |
| RAG Layer | `strategy_notes.py` | Load, retrieve, and update persistent strategy notes |
| Strategy Notes | `strategy_notes/*.md` | Accumulated game knowledge (seed + updates) |
| Guardrails | `guardrails.py` | Validate moves and notes updates; log all decisions |
| Gemini API | Google AI | LLM for move decisions, hints, insights, retrieval |
| Evaluator | `evaluator.py` | Reliability: AI-vs-AI, convergence, consistency, integrity |
| Tests | `tests/` | Unit tests for game logic and guardrails |

## Data Flow Summary

1. **Human** selects game and AI mode in the Streamlit UI
2. **Agent** retrieves relevant strategy notes from the RAG layer (which queries Gemini to extract the most relevant section)
3. **Agent** builds a prompt combining the persona, retrieved notes, and current game state, then calls **Gemini**
4. **Gemini** returns a move (Opponent) or hint (Teacher); **Guardrails** validate it before it reaches the user
5. If the move is invalid, the agent retries once then falls back to a random legal move
6. After the game ends, **Gemini** generates an insight; **Guardrails** check it is novel before appending it to the strategy notes
7. **Evaluator** and **pytest** run independently to verify correctness and reliability; human reviews the output files
