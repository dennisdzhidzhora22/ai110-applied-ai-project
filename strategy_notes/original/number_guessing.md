# Number Guessing Strategy Notes

## Core Strategy

- **Binary search is optimal.** Always guess the midpoint of your remaining range. This guarantees finding any number in at most ceil(log2(range_size)) guesses.
- After each "Too High" result, your new upper bound is (guess - 1). After "Too Low", your new lower bound is (guess + 1).
- On Easy (1–20), optimal play finishes in at most 5 guesses. On Normal (1–50), 6. On Hard (1–100), 7.

## Common Mistakes

- Guessing near the edges of the range early wastes information — a midpoint guess eliminates half the range regardless of the answer.
- Ignoring previous feedback: every past result constrains the range; always update your mental bounds after each guess.
- Repeating a guess that was already ruled out will always fail.

## Scoring Notes

- Winning early (low attempt count) yields a higher score. Each wrong guess deducts 5 points.
- Even a late win scores at least 10 points. Losing scores 0 for that game.
