"""Foil Sandbox tic-tac-toe: a camera+projector tic-tac-toe game.

The package is organized by responsibility:
  config      - static constants (timings, colors, difficulty tuning)
  state       - plain mutable state containers (GameState, VisionState)
  layout      - window/board/panel geometry
  rules       - pure win-checking logic
  ai          - the bot's move-selection logic (minimax)
  flow        - game-flow transitions (reset, difficulty select, etc.)
  vision      - ArUco marker detection and homography calibration
  animation   - small reusable easing curves
  assets      - fonts/sounds/model loading
  console     - optional terminal 'r'-to-reset listener
  ui/         - all pygame drawing code (panel, board, shared widgets)
"""
