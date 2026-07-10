# Tic-Tac-Toe OpenCV

A physical tic-tac-toe game you play by drawing with a real pen. A projector (or
monitor) displays the board, a webcam watches the surface, and a small CNN plus some
classic computer-vision heuristics figure out what you drew and where.

## How it works

1. **Calibration.** Four ArUco markers are drawn at the corners of the play area.
   The webcam looks for them, and once all four are found, OpenCV computes a
   homography that warps future camera frames back into "board pixel" space. This is
   a fully digital loop — the markers are rendered by pygame, not printed on paper —
   so it re-calibrates automatically whenever the window is resized or a marker is
   briefly lost.
2. **Difficulty select.** Before each round, the board shows four boxes in a 2x2
   grid: EASY, MID, HARD, and one inert filler (just there so all three real choices
   are the same size — otherwise the biggest box was nearly impossible to fill
   properly). Draw an X over one to pick it; a difficulty is chosen by whichever box
   has the most fresh ink on it once your hand goes still.
3. **Playing.** On your turn, draw an X in an empty cell and hold still. Once the
   camera sees ~20 stable frames with no motion, it thresholds the ink and — for each
   empty cell — crops, resizes to 32x32, and runs it through a small CNN
   (`data/model.keras`) that scores how "X-like" that cell looks. The most confident
   cell above a threshold wins. The bot then replies after a short pause, with its
   move chosen by a minimax search that's deliberately weakened (`BOT_SKILL`) at
   lower difficulties so it's beatable.
4. **Game over.** The finished board is held on screen for a second, then replaced
   with a win/lose/tie banner and a countdown before the game automatically returns
   to difficulty select.

Session stats (games played, wins/losses/ties, win rate) are tracked in a side panel
alongside the current status message, for as long as the program keeps running.

## Project structure

```
play.py             Entry point: camera/pygame setup and the main loop
game/
  config.py          Constants: timings, difficulty tuning, color palette
  state.py            GameState / VisionState - plain mutable state containers
  layout.py           Window/board/panel geometry, recomputed on resize
  rules.py             Pure win-checking logic
  ai.py                 The bot's minimax move selection
  flow.py               Game-flow transitions (new round, difficulty select, scoring)
  vision.py             ArUco marker detection + homography calibration
  animation.py           Small easing curves used by the UI
  assets.py                Fonts, sounds, and the ink-classifier model
  console.py                Optional terminal 'r'-to-reset listener
  ui/
    widgets.py               Generic "floating card" drawing primitives
    panel.py                  The side panel (status + statistics)
    board.py                   The grid, difficulty buttons, and win/result overlay
utils/
  train_model.py       Trains the ink classifier from data/images/{train,test}
data/
  model.keras          The trained classifier used at runtime
  images/               Training/test images (blank / X / O cell crops)
  sounds/                Sound effects
```

## Requirements

- Python 3.12+
- A webcam
- `opencv-python`, `pygame`, `tensorflow`, `numpy`

Install into a virtualenv, e.g.:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install opencv-python pygame tensorflow numpy
```

## Running it

```bash
python play.py
```

The window opens fullscreen. Point the webcam at the projected/displayed board;
calibration markers appear automatically until all four are detected.

### Controls

- Draw with a real pen/marker on the physical surface to place your X or pick a
  difficulty.
- Press `r` (either in the pygame window or in the terminal it was launched from) to
  abandon the current round and return to difficulty select.

## Training the classifier

`utils/train_model.py` trains the CNN used to recognize ink strokes from the images
in `data/images/train` and `data/images/test` (three classes: blank, X, O), saving
the result to `data/model.keras`. `kerastest.py` is a small standalone script for
sanity-checking a trained model against one image.
