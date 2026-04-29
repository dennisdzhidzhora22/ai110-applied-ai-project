# Connect-4 Strategy Notes

## Core Principles

- **Control the center.** Pieces in the middle columns participate in more potential four-in-a-rows than edge columns. Prioritize column 4 (center) early.
- **Build threats, not just pieces.** Aim to create open threes — three of your pieces in a row with an open space on at least one end.
- **Forced wins come from double threats.** If you create two separate winning threats at once, your opponent can only block one. Setting up this fork is the primary winning strategy.

## Defense

- **Block immediately when your opponent has three in a row** with an open end. A missed block almost always leads to a loss.
- Watch for diagonal threats — they are easier to miss than horizontal or vertical ones.
- Do not fill columns your opponent needs to complete a diagonal trap.

## Trap Patterns

- **Seven trap:** Drop pieces to force your opponent to fill a column that gives you a winning diagonal on either side.
- **Odd/even row strategy:** In certain endgame positions, the parity of the row where a winning piece would land determines who wins. Controlling which rows get filled matters.

## Opening Moves

- First move: column 4 (center) is strongest.
- If opponent plays center, play an adjacent column (3 or 5) rather than a mirrored edge.
