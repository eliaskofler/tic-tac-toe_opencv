"""Static configuration: timings, difficulty tuning, and the color palette."""

# --- Panel / board layout ---
PANEL_RATIO = 0.20   # side panel width as a fraction of the window
PANEL_MARGIN = 16    # gap between the panel/board "cards" and the window/each other
PANEL_RADIUS = 22    # corner radius for the panel and board frame

# --- Timings (seconds) ---
REVEAL_DELAY = 1            # hold on the finished board before clearing it for the result
RESTART_DELAY = 5           # show the win/tie screen before auto-restarting
CONFIRM_DURATION = 0.35     # button-press animation after picking a difficulty
MARK_ANIM_DURATION = 0.35   # pop-in animation for a freshly placed X/O
BOT_MOVE_DELAY = 1.0        # pause after the player's move before the bot replies

# --- Difficulty ---
LEVEL_SKILLS = {"easy": 0.15, "mid": 0.55, "hard": 0.9}  # chance the bot plays its best move
LEVEL_BUTTON_COLORS = {"easy": (34, 139, 34), "mid": (200, 140, 0), "hard": (200, 40, 40)}
FILLER_COLOR = (150, 150, 150)  # the inert 4th grid cell - not a real choice

# --- Playful flat-card palette ---
INK_COLOR = (45, 45, 60)
STATUS_ACCENT = (124, 77, 255)
STATS_ACCENT = (0, 172, 193)
WIN_COLOR = (56, 176, 0)
LOSS_COLOR = (229, 57, 53)
TIE_COLOR = (255, 160, 0)
NO_DIFFICULTY_COLOR = (33, 150, 243)  # blue, shown before a difficulty is chosen
LEVEL_COLORS = {"EASY": WIN_COLOR, "MID": TIE_COLOR, "HARD": LOSS_COLOR}
