import cv2
import pygame
import numpy as np
import time
import sys
import select
import termios
import tty
import tensorflow as tf
import random

pygame.init()
pygame.mixer.init()
pygame.font.init()
x_place_sound = pygame.mixer.Sound("data/sounds/x_place.wav")
model = tf.keras.models.load_model("data/model.keras")
countdown_font = pygame.font.SysFont(None, 56)
result_font = pygame.font.SysFont(None, 140)
panel_header_font = pygame.font.SysFont(None, 34)
panel_font = pygame.font.SysFont(None, 26)
panel_title_font = pygame.font.SysFont(None, 44)

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

#if width == 0 or height == 0:

display_info = pygame.display.Info()
width, height = display_info.current_w, display_info.current_h  # Fullscreen size

kernel = np.ones((5, 5), np.uint8)

screen = pygame.display.set_mode((width, height), pygame.FULLSCREEN)
pygame.display.set_caption("Foil Sandbox (OBS Capture Target)")

aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
aruco_params = cv2.aruco.DetectorParameters()
aruco_params.adaptiveThreshWinSizeMin = 3
aruco_params.adaptiveThreshWinSizeMax = 25
aruco_params.adaptiveThreshWinSizeStep = 10
aruco_params.minMarkerPerimeterRate = 0.02 

detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

MARKER_SIZE = 140  
markers_surf = {}

def generate_marker_surfaces():
    """Generates visual asset markers matching our current scaling bounds."""
    global markers_surf
    for m_id in range(4):
        core = cv2.aruco.generateImageMarker(aruco_dict, m_id, MARKER_SIZE - 30)
        padded = cv2.copyMakeBorder(core, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=255)
        rgb_marker = cv2.cvtColor(padded, cv2.COLOR_GRAY2RGB)
        surf = pygame.image.frombuffer(rgb_marker.tobytes(), (MARKER_SIZE, MARKER_SIZE), "RGB")
        markers_surf[m_id] = surf

generate_marker_surfaces()

# game
REVEAL_DELAY = 1  # seconds to hold on the finished board before clearing it for the result
RESTART_DELAY = 5  # seconds to show the win screen before auto-restarting

LEVEL_SKILLS = {"easy": 0.15, "mid": 0.55, "hard": 0.9}  # chance the bot plays its best move
LEVEL_BUTTON_COLORS = {"easy": (34, 139, 34), "mid": (200, 140, 0), "hard": (200, 40, 40)}
FILLER_COLOR = (150, 150, 150)  # the inert 4th grid cell - not a real choice

CONFIRM_DURATION = 0.35  # seconds for the button-press animation after picking a difficulty

MARK_ANIM_DURATION = 0.35  # seconds for a placed X/O to pop into place
BOT_MOVE_DELAY = 1.0  # seconds to pause (showing the player's move) before the bot replies
mark_anim_start = {}  # (row, col) -> time.time() of when that mark was placed
bot_move_ready_time = None  # scheduled time.time() for the bot's next move, or None

game_phase = "LEVEL_SELECT"  # "LEVEL_SELECT", "LEVEL_CONFIRM", or "PLAYING"
BOT_SKILL = LEVEL_SKILLS["mid"]
confirm_level = None
confirm_start_time = None
current_level_label = None  # no difficulty chosen yet

board = [["" for _ in range(3)] for _ in range(3)]
current_player = "X" if random.random() < 0.5 else "O"
bot_opens = current_player == "O"
winner = None
game_over = False
game_over_time = None

stats = {"games": 0, "wins": 0, "losses": 0, "ties": 0}

# The side panel is always pinned to exactly PANEL_RATIO of the window; the board fills
# the entire remaining 80% (no longer forced to stay square, so there's no dead space).
PANEL_RATIO = 0.20

def compute_layout(w, h):
    if w >= h:
        panel_w = int(w * PANEL_RATIO)
        board_w, board_h = w - panel_w, h
        panel = pygame.Rect(w - panel_w, 0, panel_w, h)
    else:
        panel_h = int(h * PANEL_RATIO)
        board_w, board_h = w, h - panel_h
        panel = pygame.Rect(0, h - panel_h, w, panel_h)
    return board_w, board_h, panel

# Shared "floating card" trim used for both the side panel and the board frame.
PANEL_MARGIN = 16
PANEL_RADIUS = 22

BOARD_W, BOARD_H, panel_rect = compute_layout(width, height)
board_rect = pygame.Rect(0, 0, BOARD_W, BOARD_H).inflate(-PANEL_MARGIN * 2, -PANEL_MARGIN * 2)

cell_w = board_rect.width // 3
cell_h = board_rect.height // 3

# cv
homography_matrix = None
homography_locked = False
prev_gray = None
reference_gray = None
motion_detected = False
stable_frames = 0
status_msg = "Checking corner tracking tags..."
status_color = (200, 0, 0)

def find_homography(video_frame, current_w, current_h):
    """Computes layout positioning warped strictly to match modern window scaling bounds."""
    gray_img = cv2.cvtColor(video_frame, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = detector.detectMarkers(gray_img)
    
    if ids is not None and len(ids) >= 4:
        id_list = ids.flatten().tolist()
        if all(i in id_list for i in [0, 1, 2, 3]):
            src_pts = np.zeros((4, 2), dtype=np.float32)
            src_pts[0] = corners[id_list.index(0)][0][0]  # Top-Left
            src_pts[1] = corners[id_list.index(1)][0][1]  # Top-Right
            src_pts[2] = corners[id_list.index(2)][0][2]  # Bottom-Right
            src_pts[3] = corners[id_list.index(3)][0][3]  # Bottom-Left
            
            # Map dynamic targets relative to the current live window size
            dst_pts = np.array([[0, 0], [current_w, 0], [current_w, current_h], [0, current_h]], dtype=np.float32)
            return cv2.getPerspectiveTransform(src_pts, dst_pts)
    return None

def check_win_condition(player):
    row = -1
    col = -1
    dia = -1

    for i in range(3):
        if board[i][0] == board[i][1] == board[i][2] == player: row = i
        if board[0][i] == board[1][i] == board[2][i] == player: col = i

    if board[0][0] == board[1][1] == board[2][2] == player: dia = 1
    if board[0][2] == board[1][1] == board[2][0] == player: dia = 2

    return row != -1 or col != -1 or dia != -1

def render_board_surface(include_result=True):
    """Renders the grid/marks onto a fresh board-local surface, ready to be clipped and
    blitted at board_rect.topleft. Once the round is over, the grid is cleared away and
    only the result banner + restart countdown are shown."""
    board_surf = pygame.Surface(board_rect.size, pygame.SRCALPHA)
    board_surf.fill((255, 255, 255, 255))

    revealing = game_over and game_over_time is not None and time.time() - game_over_time < REVEAL_DELAY

    if not game_over or revealing:
        for r in range(3):
            for c in range(3):
                if board[r][c] == "X":
                    cell_rect = pygame.Rect(c * cell_w, r * cell_h, cell_w, cell_h)
                    board_surf.fill((150, 220, 150), cell_rect)
                elif board[r][c] == "O":
                    cell_rect = pygame.Rect(c * cell_w, r * cell_h, cell_w, cell_h)
                    board_surf.fill((150, 190, 230), cell_rect)

        for i in range(1, 3):
            pygame.draw.line(board_surf, (70, 70, 70), (i * cell_w, 0), (i * cell_w, board_rect.height), 3)
            pygame.draw.line(board_surf, (70, 70, 70), (0, i * cell_h), (board_rect.width, i * cell_h), 3)

        for r in range(3):
            for c in range(3):
                if board[r][c] == "":
                    continue

                center_x = c * cell_w + cell_w // 2
                center_y = r * cell_h + cell_h // 2
                offset = min(cell_w, cell_h) // 4

                anim_start = mark_anim_start.get((r, c))
                if anim_start is not None:
                    t = min(1.0, (time.time() - anim_start) / MARK_ANIM_DURATION)
                    offset = int(offset * pop_in_scale(t))

                if board[r][c] == "X":
                    pygame.draw.line(board_surf, (34, 139, 34), (center_x - offset, center_y - offset), (center_x + offset, center_y + offset), 5)
                    pygame.draw.line(board_surf, (34, 139, 34), (center_x + offset, center_y - offset), (center_x - offset, center_y + offset), 5)
                elif board[r][c] == "O":
                    pygame.draw.circle(board_surf, (30, 100, 220), (center_x, center_y), offset, 6)

    if include_result and game_over and game_over_time is not None and not revealing:
        if winner == "Tie":
            result_text, result_color = "TIE!", (100, 100, 100)
        elif winner == "X":
            result_text, result_color = "YOU WIN!", (34, 139, 34)
        else:
            result_text, result_color = "YOU LOSE!", (200, 40, 40)

        result_surf = result_font.render(result_text, True, result_color)
        board_surf.blit(result_surf, result_surf.get_rect(center=(board_rect.width // 2, board_rect.height // 2 - 80)))

        remaining = max(0, RESTART_DELAY - int(time.time() - game_over_time - REVEAL_DELAY))
        countdown_surf = countdown_font.render(str(remaining), True, (40, 40, 40))
        board_surf.blit(countdown_surf, countdown_surf.get_rect(center=(board_rect.width // 2, board_rect.height // 2 + 60)))

    return board_surf

def clip_to_board_radius(surf):
    mask_surf = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(mask_surf, (255, 255, 255, 255), mask_surf.get_rect(), border_radius=PANEL_RADIUS)
    surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)


def check_game_status():
    global winner, game_over, game_over_time
    if check_win_condition("X"):
        winner = "X"; game_over = True; game_over_time = time.time()
        stats["games"] += 1; stats["wins"] += 1
        print("Game over: X (player) wins!")
        return
    if check_win_condition("O"):
        winner = "O"; game_over = True; game_over_time = time.time()
        stats["games"] += 1; stats["losses"] += 1
        print("Game over: O (bot) wins!")
        return
    if all(board[r][c] != "" for r in range(3) for c in range(3)):
        winner = "Tie"; game_over = True; game_over_time = time.time()
        stats["games"] += 1; stats["ties"] += 1
        print("Game over: Tie.")

def get_board_winner(b):
    lines = []
    for i in range(3):
        lines.append([b[i][0], b[i][1], b[i][2]])
        lines.append([b[0][i], b[1][i], b[2][i]])
    lines.append([b[0][0], b[1][1], b[2][2]])
    lines.append([b[0][2], b[1][1], b[2][0]])

    for line in lines:
        if line[0] != "" and line[0] == line[1] == line[2]:
            return line[0]

    if all(b[r][c] != "" for r in range(3) for c in range(3)):
        return "Tie"
    return None

def minimax(b, depth, is_maximizing):
    result = get_board_winner(b)
    if result == "O": return 10 - depth
    if result == "X": return depth - 10
    if result == "Tie": return 0

    if is_maximizing:
        best_score = float("-inf")
        for r in range(3):
            for c in range(3):
                if b[r][c] == "":
                    b[r][c] = "O"
                    best_score = max(best_score, minimax(b, depth + 1, False))
                    b[r][c] = ""
        return best_score
    else:
        best_score = float("inf")
        for r in range(3):
            for c in range(3):
                if b[r][c] == "":
                    b[r][c] = "X"
                    best_score = min(best_score, minimax(b, depth + 1, True))
                    b[r][c] = ""
        return best_score

def get_computer_move():
    empty_cells = [(r, c) for r in range(3) for c in range(3) if board[r][c] == ""]
    if not empty_cells:
        return None

    if random.random() > BOT_SKILL:
        return random.choice(empty_cells)

    best_score = float("-inf")
    best_moves = []
    for r, c in empty_cells:
        board[r][c] = "O"
        score = minimax(board, 0, False)
        board[r][c] = ""
        if score > best_score:
            best_score = score
            best_moves = [(r, c)]
        elif score == best_score:
            best_moves.append((r, c))
    return random.choice(best_moves)

def reset_game():
    global board, current_player, bot_opens, winner, game_over, game_over_time, reference_gray, motion_detected, stable_frames, mark_anim_start, bot_move_ready_time
    board = [["" for _ in range(3)] for _ in range(3)]
    current_player = "X" if random.random() < 0.5 else "O"
    bot_opens = current_player == "O"
    winner = None
    game_over = False
    game_over_time = None
    reference_gray = None
    motion_detected = False
    stable_frames = 0
    mark_anim_start = {}
    bot_move_ready_time = time.time() + BOT_MOVE_DELAY if bot_opens else None
    print(f"New round: {'player' if current_player == 'X' else 'bot'} moves first.")

def enter_level_select():
    global game_phase, motion_detected, stable_frames, current_level_label
    game_phase = "LEVEL_SELECT"
    motion_detected = False
    stable_frames = 0
    current_level_label = None
    print("Entering difficulty select.")

def start_level_confirm(level_name):
    global game_phase, confirm_level, confirm_start_time
    game_phase = "LEVEL_CONFIRM"
    confirm_level = level_name
    confirm_start_time = time.time()

def get_level_zones():
    """Rects (in warped board coordinates) for the EASY / MID / HARD choices, laid out as
    a 2x2 grid of equal-sized cells. The 4th cell ("filler") isn't a real choice - it just
    fills out the grid so EASY isn't twice the area of MID/HARD (which made it nearly
    impossible to cover 25% of it with a single X)."""
    margin = 40  # keep the buttons off the board's edges, not just spaced from each other
    gap = 30
    available_w = board_rect.width - margin * 2
    available_h = board_rect.height - margin * 2

    col_w = (available_w - gap) // 2
    row_h = (available_h - gap) // 2

    grid_w = col_w * 2 + gap
    grid_h = row_h * 2 + gap
    start_x = board_rect.left + (board_rect.width - grid_w) // 2
    start_y = board_rect.top + (board_rect.height - grid_h) // 2
    right_x = start_x + col_w + gap
    bottom_y = start_y + row_h + gap

    return {
        "easy": pygame.Rect(start_x, start_y, col_w, row_h),
        "mid": pygame.Rect(right_x, start_y, col_w, row_h),
        "hard": pygame.Rect(start_x, bottom_y, col_w, row_h),
        "filler": pygame.Rect(right_x, bottom_y, col_w, row_h),
    }

def draw_zone(rect, label, color, radius=20, shadow_offset=6, scale=1.0):
    if scale != 1.0:
        rect = rect.inflate(int(rect.width * (scale - 1)), int(rect.height * (scale - 1)))
        shadow_offset = int(shadow_offset * scale)

    shadow_color = tuple(max(0, ch - 60) for ch in color)
    pygame.draw.rect(screen, shadow_color, rect.move(shadow_offset, shadow_offset), border_radius=radius)

    pygame.draw.rect(screen, tint(color, 0.65), rect, border_radius=radius)
    pygame.draw.rect(screen, color, rect, width=3, border_radius=radius)
    text_surf = countdown_font.render(label, True, color)
    screen.blit(text_surf, text_surf.get_rect(center=rect.center))

def punch_scale(t):
    """t in [0,1]: a quick squash-then-overshoot-then-settle curve for a button-press feel."""
    if t < 0.3:
        return 1.0 - 0.2 * (t / 0.3)
    elif t < 0.6:
        return 0.8 + 0.35 * ((t - 0.3) / 0.3)
    else:
        return 1.15 - 0.15 * ((t - 0.6) / 0.4)

def pop_in_scale(t):
    """t in [0,1]: grows a freshly-placed mark from small, overshoots, then settles at full size."""
    if t < 0.5:
        return 0.2 + 0.9 * (t / 0.5)
    return 1.1 - 0.1 * ((t - 0.5) / 0.5)

def wrap_text(text, font, max_width):
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

# Playful flat-card palette
INK_COLOR = (45, 45, 60)
STATUS_ACCENT = (124, 77, 255)
STATS_ACCENT = (0, 172, 193)
WIN_COLOR = (56, 176, 0)
LOSS_COLOR = (229, 57, 53)
TIE_COLOR = (255, 160, 0)
NO_DIFFICULTY_COLOR = (33, 150, 243)  # blue, shown before a difficulty is chosen
LEVEL_COLORS = {"EASY": WIN_COLOR, "MID": TIE_COLOR, "HARD": LOSS_COLOR}

def tint(color, amount):
    return tuple(int(c + (255 - c) * amount) for c in color)

def draw_card(rect, accent_color, radius=16, shadow_offset=6):
    shadow_color = tuple(max(0, ch - 50) for ch in accent_color)
    pygame.draw.rect(screen, shadow_color, rect.move(shadow_offset, shadow_offset), border_radius=radius)
    pygame.draw.rect(screen, (255, 255, 255), rect, border_radius=radius)
    pygame.draw.rect(screen, accent_color, rect, width=3, border_radius=radius)

def draw_translucent_border(rect, color, radius, width=3, alpha=110):
    border_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(border_surf, (*color, alpha), border_surf.get_rect(), width=width, border_radius=radius)
    screen.blit(border_surf, rect.topleft)

def draw_rounded_gradient(rect, color_top, color_bottom, radius):
    gradient_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    h = max(1, rect.height)
    for i in range(rect.height):
        t = i / h
        color = tuple(int(color_top[ch] + (color_bottom[ch] - color_top[ch]) * t) for ch in range(3))
        pygame.draw.line(gradient_surf, (*color, 255), (0, i), (rect.width, i))

    mask_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(mask_surf, (255, 255, 255, 255), mask_surf.get_rect(), border_radius=radius)
    gradient_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    screen.blit(gradient_surf, rect.topleft)

def draw_side_panel():
    if panel_rect.width <= 0 or panel_rect.height <= 0:
        return

    bg_rect = panel_rect.inflate(-PANEL_MARGIN * 2, -PANEL_MARGIN * 2)
    if bg_rect.width <= 0 or bg_rect.height <= 0:
        return

    difficulty_color = LEVEL_COLORS.get(current_level_label, NO_DIFFICULTY_COLOR)
    draw_rounded_gradient(bg_rect, tint(difficulty_color, 0.75), tint(difficulty_color, 0.55), PANEL_RADIUS)

    border_color = tuple(max(0, ch - 60) for ch in difficulty_color)
    draw_translucent_border(bg_rect, border_color, PANEL_RADIUS)

    pad = 18
    inner_w = bg_rect.width - pad * 2
    x = bg_rect.left + pad

    # --- Difficulty title ---
    title_text = current_level_label if current_level_label else "Tic.. Tac.. Toe"
    diff_title_surf = panel_title_font.render(title_text, True, border_color)
    screen.blit(diff_title_surf, diff_title_surf.get_rect(midtop=(bg_rect.centerx, bg_rect.top + pad)))
    top_y = bg_rect.top + pad + diff_title_surf.get_height() + 14

    # --- Statistics card (anchored to the top) ---
    stat_rows = [
        ("Games", str(stats["games"]), None),
        ("Wins", str(stats["wins"]), WIN_COLOR),
        ("Losses", str(stats["losses"]), LOSS_COLOR),
        ("Ties", str(stats["ties"]), TIE_COLOR),
    ]
    title_h = panel_header_font.get_height()
    row_h = panel_font.get_height() + 14
    bar_h = 18
    stats_card_h = 16 + title_h + 10 + row_h * len(stat_rows) + 8 + bar_h + panel_font.get_height() + 14
    stats_card = pygame.Rect(x, top_y, inner_w, stats_card_h)
    draw_card(stats_card, STATS_ACCENT)

    sy = stats_card.top + 12
    title_surf = panel_header_font.render("STATISTICS", True, STATS_ACCENT)
    screen.blit(title_surf, (stats_card.left + 14, sy))
    sy += title_surf.get_height() + 10

    for label, value, dot_color in stat_rows:
        if dot_color:
            pygame.draw.circle(screen, dot_color, (stats_card.left + 22, sy + row_h // 2 - 2), 6)
        label_surf = panel_font.render(label, True, INK_COLOR)
        screen.blit(label_surf, (stats_card.left + 38, sy))
        value_surf = panel_font.render(value, True, dot_color or INK_COLOR)
        screen.blit(value_surf, (stats_card.right - 14 - value_surf.get_width(), sy))
        sy += row_h

    games = stats["games"]
    win_rate = (stats["wins"] / games) if games else 0.0
    bar_x = stats_card.left + 14
    bar_w = stats_card.width - 28
    pygame.draw.rect(screen, (230, 230, 230), (bar_x, sy, bar_w, bar_h), border_radius=bar_h // 2)
    fill_w = int(bar_w * win_rate)
    if fill_w > 0:
        pygame.draw.rect(screen, WIN_COLOR, (bar_x, sy, fill_w, bar_h), border_radius=bar_h // 2)
    sy += bar_h + 6
    rate_surf = panel_font.render(f"Win rate: {win_rate * 100:.0f}%", True, INK_COLOR)
    screen.blit(rate_surf, (bar_x, sy))

    # --- Status card (anchored to the bottom) ---
    status_lines = wrap_text(status_msg, panel_font, inner_w - 28)
    line_h = panel_font.get_height() + 4
    status_card_h = 16 + title_h + 6 + len(status_lines) * line_h + 10
    status_card = pygame.Rect(x, bg_rect.bottom - pad - status_card_h, inner_w, status_card_h)
    draw_card(status_card, STATUS_ACCENT)

    ty = status_card.top + 12
    title_surf = panel_header_font.render("STATUS", True, STATUS_ACCENT)
    screen.blit(title_surf, (status_card.left + 14, ty))
    ty += title_surf.get_height() + 6
    for line in status_lines:
        line_surf = panel_font.render(line, True, INK_COLOR)
        screen.blit(line_surf, (status_card.left + 14, ty))
        ty += line_h

console_raw_mode = sys.stdin.isatty()
if console_raw_mode:
    console_old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())
    print("Console ready. Press 'r' here to reset the game.")

run = True
try:
    while run:
        ret, frame = cap.read();
        if not ret:
            run = False

        if console_raw_mode and select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.read(1)
            if key.lower() == "r":
                print("Manual reset requested from console.")
                enter_level_select()

        diagnostic_frame = frame.copy()
        raw_gray = cv2.cvtColor(diagnostic_frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = detector.detectMarkers(raw_gray)

        if ids is not None:
            cv2.aruco.drawDetectedMarkers(diagnostic_frame, corners, ids)
            cv2.putText(diagnostic_frame, f"Tracking: {len(ids)}/4 Anchors Found", (15, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
        else:
            cv2.putText(diagnostic_frame, f"CRITICAL ERROR: No Markers Detected", (15, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA)
        
        #cv2.imshow("Webcam Live Feed / ArUco Diagnostics", diagnostic_frame)
    
        cv2.waitKey(1)
        
        ############### PYGAME ###############
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            
            elif event.type == pygame.VIDEORESIZE:
                # DYNAMIC WINDOW RECALIBRATION
                width, height = event.w, event.h
                screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
                BOARD_W, BOARD_H, panel_rect = compute_layout(width, height)
                board_rect = pygame.Rect(0, 0, BOARD_W, BOARD_H).inflate(-PANEL_MARGIN * 2, -PANEL_MARGIN * 2)
                cell_w = board_rect.width // 3
                cell_h = board_rect.height // 3
                homography_matrix = None
                prev_gray = None
                homography_locked = False
                print(f"Window resized to {width}x{height}. Recalibrating ArUco tracking...")
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    enter_level_select()
    
        M = find_homography(frame, BOARD_W, BOARD_H)
        if M is not None:
            if not homography_locked:
                print("ArUco calibration locked: all 4 markers found.")
                homography_locked = True
            homography_matrix = M

        if homography_matrix is None:
            screen.fill((255, 255, 255))

            screen.blit(markers_surf[0], (0, 0))
            screen.blit(markers_surf[1], (BOARD_W - MARKER_SIZE, 0))
            screen.blit(markers_surf[2], (BOARD_W - MARKER_SIZE, BOARD_H - MARKER_SIZE))
            screen.blit(markers_surf[3], (0, BOARD_H - MARKER_SIZE))
            draw_side_panel()
            pygame.display.update()
            continue

        warped_frame = cv2.warpPerspective(frame, homography_matrix, (BOARD_W, BOARD_H))
        gray = cv2.cvtColor(warped_frame, cv2.COLOR_BGR2GRAY)
        gray_blurred = cv2.GaussianBlur(gray, (21, 21), 0)

        if prev_gray is None:
            prev_gray = gray_blurred
            reference_gray = gray_blurred
            continue
    
        if game_phase == "LEVEL_SELECT":
            frame_delta = cv2.absdiff(prev_gray, gray_blurred)
            _, thresh_delta = cv2.threshold(frame_delta, 20, 255, cv2.THRESH_BINARY)
            changed_pixels = cv2.countNonZero(thresh_delta)

            motion_threshold = int((BOARD_W * BOARD_H) * 0.005)

            if changed_pixels > motion_threshold:
                motion_detected = True
                stable_frames = 0
                status_msg = "Ink strokes detected..."
                status_color = (0, 0, 255)
            else:
                if motion_detected:
                    stable_frames += 1
                    status_msg = f"Hold still... scanning ink in {max(0, 20 - stable_frames)}"
                    status_color = (0, 100, 200)

                    if stable_frames >= 20:
                        motion_detected = False
                        stable_frames = 0

                        turn_delta = cv2.cvtColor(warped_frame, cv2.COLOR_BGR2GRAY)
                        turn_delta = cv2.erode(turn_delta, kernel, iterations=5)
                        _, turn_thresh_inv = cv2.threshold(turn_delta, 160, 255, cv2.THRESH_BINARY_INV)
                        turn_thresh = cv2.GaussianBlur(turn_thresh_inv, (7, 7), 0)

                        # The CNN model isn't reliable at this low a signal level (it reads
                        # ~0.9+ "X confidence" even on near-blank zones), so the level choice
                        # is decided from raw ink coverage instead - whichever zone was
                        # actually marked should have noticeably more ink than the other two.
                        MIN_INK_RATIO = 0.25
                        MIN_INK_MARGIN = 0.10

                        zone_ink = {}
                        for level_name, rect in get_level_zones().items():
                            if level_name not in LEVEL_SKILLS:
                                continue  # "filler" is just a spacer, never a valid choice
                            zone_roi = turn_thresh[rect.top:rect.bottom, rect.left:rect.right]
                            zone_ink[level_name] = cv2.countNonZero(zone_roi) / (zone_roi.shape[0] * zone_roi.shape[1])

                        print("Difficulty scan (ink coverage): " +
                              ", ".join(f"{name}={ink:.0%}" for name, ink in zone_ink.items()))

                        ranked = sorted(zone_ink.items(), key=lambda kv: kv[1], reverse=True)
                        top_name, top_ink = ranked[0]
                        runner_up_ink = ranked[1][1]

                        best_level = None
                        if top_ink >= MIN_INK_RATIO and (top_ink - runner_up_ink) >= MIN_INK_MARGIN:
                            best_level = top_name

                        if best_level:
                            BOT_SKILL = LEVEL_SKILLS[best_level]
                            current_level_label = best_level.upper()
                            print(f"Difficulty selected: {best_level.upper()} (BOT_SKILL={BOT_SKILL:.2f})")
                            start_level_confirm(best_level)
                        else:
                            print("Difficulty scan failed: no zone matched confidently.")
                            status_msg = "Scan failed. Mark EASY, MID, or HARD with an X."
                else:
                    status_msg = "Choose a difficulty: draw an X over EASY, MID, or HARD."
                    status_color = (0, 120, 0)

        elif game_phase == "LEVEL_CONFIRM":
            status_msg = f"{confirm_level.upper()} selected!"
            status_color = (0, 120, 0)
            if time.time() - confirm_start_time >= CONFIRM_DURATION:
                reset_game()
                game_phase = "PLAYING"

        elif game_phase == "PLAYING" and not game_over and current_player == "X":
            frame_delta = cv2.absdiff(prev_gray, gray_blurred)

            _, thresh_delta = cv2.threshold(frame_delta, 20, 255, cv2.THRESH_BINARY)
            changed_pixels = cv2.countNonZero(thresh_delta)

            best_cell = None
            max_ink_density = 0

            motion_threshold = int((BOARD_W * BOARD_H) * 0.005)

            if changed_pixels > motion_threshold:
                if not motion_detected:
                    motion_detected = True
                    reference_gray = prev_gray.copy()
                stable_frames = 0
                status_msg = "Ink strokes detected..."
                status_color = (0, 0, 255)
            else:
                if motion_detected:
                    stable_frames += 1
                    status_msg = f"Hold still... scanning ink in {max(0, 20 - stable_frames)}"
                    status_color = (0, 100, 200)

                    if stable_frames >= 20:
                        motion_detected = False
                        stable_frames = 0

                        turn_delta = cv2.cvtColor(warped_frame,  cv2.COLOR_BGR2GRAY)


                        turn_delta = cv2.erode(turn_delta, kernel, iterations=5)

                        _, turn_thresh_inv = cv2.threshold(turn_delta, 160, 255, cv2.THRESH_BINARY_INV)
                        turn_thresh = cv2.GaussianBlur(turn_thresh_inv, (7, 7), 0)

                        #cv2.imshow("turn_thresh", turn_thresh)
                        print("Scanning board for a new X placement...")

                        best_cell = None
                        max_ink_density = 0

                        for r in range(3):
                            for c in range(3):
                                if board[r][c] == "":
                                    # 1. Crop the cell region of interest
                                    cy, cx = board_rect.top + r*cell_h, board_rect.left + c*cell_w
                                    cell_roi = turn_thresh[cy : cy+cell_h, cx : cx+cell_w]

                                    # 2. Resize to 32x32 to match your model's input size
                                    cell_resized = cv2.resize(cell_roi, (32, 32))

                                    # 3. Reshape to (1, 32, 32, 1) -> Batch, Height, Width, Channel
                                    cell_input = cell_resized.reshape(1, 32, 32, 1).astype(np.float32) / 255.0

                                    # 4. Run prediction
                                    predictions = model.predict(cell_input, verbose=0) # verbose=0 keeps terminal clean
                                    x_confidence = predictions[0][1]

                                    # 5. Check if this is the strongest "X" we've seen so far
                                    # (e.g., must be higher than previous max and at least 70% confident)
                                    if x_confidence > max_ink_density and x_confidence > 0.70:
                                        max_ink_density = x_confidence
                                        best_cell = (r, c)

                        if best_cell:
                            r, c = best_cell
                            board[r][c] = "X"
                            mark_anim_start[(r, c)] = time.time()
                            x_place_sound.play()
                            print(f"Player placed X at row {r}, col {c} (confidence {max_ink_density:.2f})")
                            check_game_status()
                            if not game_over:
                                current_player = "O"
                                bot_move_ready_time = time.time() + BOT_MOVE_DELAY
                        else:
                            print("Scan failed: no cell matched confidently as X.")
                            status_msg = "Scan failed. Bolder lines are required."
                else:
                    if M is not None:
                        status_msg = "Your Turn: Draw your marker step."
                        status_color = (0, 120, 0)
                    else:
                        status_msg = "Webcam tag coverage dropped. Running fallback memory calculations..."
                        status_color = (120, 120, 0)

        elif game_phase == "PLAYING" and not game_over and current_player == "O":
            status_msg = "Bot is thinking..."
            status_color = (30, 100, 220)
            if bot_move_ready_time is not None and time.time() >= bot_move_ready_time:
                opening_move = bot_opens
                if bot_opens:
                    empty_cells = [(r, c) for r in range(3) for c in range(3) if board[r][c] == ""]
                    move = random.choice(empty_cells) if empty_cells else None
                    bot_opens = False
                else:
                    move = get_computer_move()
                if move:
                    r, c = move
                    board[r][c] = "O"
                    mark_anim_start[(r, c)] = time.time()
                    print(f"Bot placed O at row {r}, col {c}" + (" (random opening move)" if opening_move else ""))
                    check_game_status()
                current_player = "X"
                bot_move_ready_time = None

        elif game_phase == "PLAYING" and game_over:
            since_game_over = time.time() - game_over_time
            if since_game_over < REVEAL_DELAY:
                status_msg = "Tie match!" if winner == "Tie" else f"Victory! Winner: {winner}."
                status_color = (100, 100, 100) if winner == "Tie" else ((0, 120, 0) if winner == "X" else (30, 100, 220))
            else:
                remaining = max(0, RESTART_DELAY - int(since_game_over - REVEAL_DELAY))
                if winner == "Tie":
                    status_msg = f"Tie match! Restarting in {remaining}..."
                    status_color = (100, 100, 100)
                else:
                    status_msg = f"Victory! Winner: {winner}. Restarting in {remaining}..."
                    status_color = (0, 120, 0) if winner == "X" else (30, 100, 220)

            if since_game_over >= REVEAL_DELAY + RESTART_DELAY:
                print("Restart timer elapsed.")
                enter_level_select()

        prev_gray = gray_blurred

        screen.fill((255, 255, 255))

        if game_phase == "LEVEL_SELECT":
            zones = get_level_zones()
            for level_name, rect in zones.items():
                if level_name == "filler":
                    draw_zone(rect, "", FILLER_COLOR)
                else:
                    draw_zone(rect, level_name.upper(), LEVEL_BUTTON_COLORS[level_name])

        elif game_phase == "LEVEL_CONFIRM":
            elapsed = time.time() - confirm_start_time
            t = min(1.0, elapsed / CONFIRM_DURATION)
            scale = punch_scale(t)
            rect = get_level_zones()[confirm_level]
            draw_zone(rect, confirm_level.upper(), LEVEL_BUTTON_COLORS[confirm_level], scale=scale)

        elif game_phase == "PLAYING":
            board_surf = render_board_surface(include_result=True)
            clip_to_board_radius(board_surf)
            screen.blit(board_surf, board_rect.topleft)

        board_border_color = tuple(max(0, ch - 60) for ch in LEVEL_COLORS.get(current_level_label, NO_DIFFICULTY_COLOR))
        draw_translucent_border(board_rect, board_border_color, PANEL_RADIUS)

        draw_side_panel()
        pygame.display.update()
finally:
    if console_raw_mode:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, console_old_settings)

print("program stoped")
cap.release()
cv2.destroyAllWindows()
pygame.quit()
sys.exit()
