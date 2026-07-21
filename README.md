# ♛ Checkmate Elo

**A chess AI that actually plays at your level — and proves it.**

Most "AI chess" apps either crush you or barely resist. Checkmate Elo tracks a
chess.com-calibrated rating, adjusts the engine's depth to match it, and
grades every move you make afterward — so every game is a fair fight, and
every loss comes with a reason.

[![Platform](https://img.shields.io/badge/platform-macOS-black?logo=apple)](https://github.com/Vangaurdd/checkmate-elo/releases)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue?logo=python)](https://www.python.org/)
[![License: Pieces CC BY--SA](https://img.shields.io/badge/piece%20art-CC--BY--SA-lightgrey)](#piece-artwork)
[![Release](https://img.shields.io/github/v/release/Vangaurdd/checkmate-elo?label=latest%20release)](https://github.com/Vangaurdd/checkmate-elo/releases/latest)

![Checkmate Elo board with move list](assets/screenshot.png)

## Why you'll want this

- 🎯 **A rating that means something.** Start at 1000 and stay there — the AI's
  search depth is calibrated in bands that mirror chess.com's skill tiers, so
  a 1000 here plays like a 1000 there, not a max-strength engine in disguise.
- 📈 **Your progress is remembered.** Rating and a full game history persist
  across launches, shown right on the start screen — no more losing track of
  whether you're actually improving.
- 🔍 **Real post-game coaching, no subscription required.** Every move you
  played is analyzed by [Stockfish](https://stockfishchess.org/) and scored
  1–10 using the same win-percentage accuracy formula Lichess and chess.com
  use — blunders in red, brilliancies in green.
- 🖥️ **Looks like a real game.** Hand-picked Staunton piece art, an animated
  board with a wooden frame, a live move list, and full fullscreen support
  that actually reflows instead of stretching.
- 📦 **One download, no setup.** Grab the `.app`, drag it to Applications,
  done — no Python, no terminal, no dependencies to wrangle.

![Move review screen](assets/screenshot_review.png)

## Features

- **Full chess rules** via [python-chess](https://python-chess.readthedocs.io/) — legal move generation, check/checkmate/stalemate detection, all the way down to en passant and promotion.
- **Polished board UI** — wooden frame with rank/file coordinates, drop shadows under every piece, a last-move highlight, a live move-list sidebar, and lichess-style move indicators (a dot for a quiet move, a ring for a capture).
- **Animated moves** — pieces slide to their destination square instead of snapping.
- **Fullscreen done right** — press F11, drag to resize, or use the native macOS fullscreen button. The board stays centered at a natural size instead of stretching to the edges, and the freed-up space is used for the move list, not empty bars.
- **Minimax AI with alpha-beta pruning**, plus a move-ordering heuristic that favors captures/checks and penalizes repetitive shuffling (moving the same piece back and forth).
- **Elo rating system calibrated to chess.com's scale.** Your rating starts at 1000, and the AI's search depth scales in ~400-point bands to roughly match chess.com's skill tiers:

  | Rating range | AI depth | Tier |
  |---|---|---|
  | < 600 | 1 | Beginner |
  | 600–999 | 2 | Novice |
  | 1000–1399 | 3 | Intermediate |
  | 1400–1799 | 4 | Advanced |
  | 1800+ | 5 | Expert |

  So a genuinely 1000-rated player faces a moderate opponent (depth 3), not the AI's maximum strength.
- **Persistent rating and game history.** Your rating and a log of past games (date, result, rating before/after) are saved to disk after every game and reloaded on launch — the start screen shows a "Recent Games" card with color-coded rating deltas.
- **Two ways to start:**
  - **Continue** — resume at your saved rating.
  - **Recalibrate** — reset to the 1000 baseline and play a fresh calibration game to re-rank from scratch.
- **Replay mode** — after a game ends, replay the entire game move-by-move.
- **Game Review powered by Stockfish** — like chess.com's post-game analysis: every move you made is analyzed by a real chess engine and scored 1–10 using the Lichess/chess.com win-percentage accuracy formula, with blunders (≤3) highlighted red and excellent moves (9–10) highlighted green. Click any move to jump the board to that exact position and rewatch the game move-by-move.

## Controls

- **Mouse** — click a piece, then click a highlighted square to move it.
- **R** — reset the current game.
- **F11** — toggle fullscreen.
- On the game-over screen, click **Replay** to watch the game again, or **Review** to open Game Review.
- In Game Review, **click any move** in the list to jump the board to that exact position — a full rewatch with every move's score, not just a list. Use **◀ ▶** (or the arrow keys) to step move-by-move.

## Get it

Download the latest build from the [Releases page](https://github.com/Vangaurdd/checkmate-elo/releases/latest),
unzip it, and drag `AI Chess Elo.app` into `/Applications`.

> macOS Gatekeeper will flag it as from an unidentified developer on first
> launch (it's not notarized). Right-click the app → **Open** once to bypass
> that — you only need to do it the first time.

## Running from source

```bash
pip install -r requirements.txt
brew install stockfish   # optional but recommended — powers Game Review
python3 chess_game.py
```

Without Stockfish installed, Game Review falls back to a much weaker built-in
heuristic (still functional, just far less accurate at grading moves).

Run the rating-curve simulation (no GUI) with:

```bash
python3 chess_game.py simulate
```

## Building a standalone macOS app

```bash
pip install pyinstaller
pyinstaller --windowed --name "AI Chess Elo" --icon assets/AppIcon.icns \
  --add-data "assets/pieces:assets/pieces" \
  --add-binary "$(brew --prefix stockfish)/bin/stockfish:." \
  chess_game.py
```

This produces `dist/AI Chess Elo.app`, which you can drag into `/Applications`
and launch like any other app — no terminal, no separate Stockfish install
required (it's bundled inside the app).

## Where your rating is stored

Your rating persists at:

```
~/Library/Application Support/AI Chess Elo/ratings.json
```

Deleting this file has the same effect as choosing "Recalibrate" from the start menu.

## How the rating updates

After each game, your rating is adjusted with a standard Elo expected-score formula,
but the K-factor (how much a single result moves your rating) is scaled by how the
game went:

- Fast losses are penalized hard (K up to 600) — the system looks at how many of
  *your own* moves it took to lose and how many distinct pieces you actually moved,
  so a quick loss where you only shuffled one piece around gets hit much harder
  than a real fighting loss.
- Wins and draws use smaller K-factors that shrink further the longer the game goes.

The AI's rating is always kept equal to your own after your first (calibration) game,
so its search depth — and therefore its difficulty — tracks your rating directly.

## How move review scoring works

Game Review uses the same method [Lichess documents publicly](https://lichess.org/page/accuracy)
and chess.com is understood to use a close variant of:

1. Stockfish analyzes the position before your move and the position after it (depth 14), giving a centipawn evaluation for each, from White's perspective.
2. Each evaluation is converted to a **win percentage** with `50 + 50 * (2 / (1 + e^(-0.00368208 × centipawns)) - 1)` — this is the empirical curve both sites use to turn an engine score into "chances of winning," and it's deliberately non-linear: a swing from +50 to -50 (near equal) matters far more than +500 to +400 (already winning).
3. The drop in win% caused by your move maps to an accuracy score via `103.1668 × e^(-0.04354 × win%_lost) - 3.1669`, then scaled to this app's 1–10 range for that move's badge.

The headline **Average Move Quality** is not a plain average of those per-move
scores — like Lichess, it's a **harmonic mean**, which is dragged down much
harder by a single bad blunder than an arithmetic mean would be. A game with
one real blunder and otherwise-fine moves will show a noticeably lower average
than "sum and divide," matching the intuition that one big mistake should hurt
your overall grade more than a plain average gives it credit for.

If Stockfish isn't available, it falls back to a much weaker built-in heuristic
search that also accounts for king safety and piece development, not just
material — but a real engine is what makes the scoring trustworthy.

## Piece artwork

Pieces are the "cburnett" Staunton set created by Colin M.L. Burnett, sourced from
[Wikimedia Commons](https://commons.wikimedia.org/wiki/Category:SVG_chess_pieces)
(also used by Lichess). Licensed under CC BY-SA 3.0 / GFDL 1.2 / GPL2+; source SVGs
are included under `assets/pieces_svg/`.

## Analysis engine

Game Review is powered by [Stockfish](https://stockfishchess.org/), the free and
open-source chess engine, licensed under [GPLv3](https://github.com/official-stockfish/Stockfish/blob/master/Copying.txt).
The packaged app bundles an unmodified Stockfish binary; source is available at
[github.com/official-stockfish/Stockfish](https://github.com/official-stockfish/Stockfish).
