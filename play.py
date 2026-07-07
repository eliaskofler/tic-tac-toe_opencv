import cv2
import pygame
import numpy as np
import time
import random
import sys
import tensorflow as tf
import cv2

pygame.init()
model = tf.keras.models.load_model("data/model.keras")

cap = cv2.VideoCapture(2)

if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

#if width == 0 or height == 0:

width, height = 1000, 800  # Default baseline size
    
screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
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
board = [["" for _ in range(3)] for _ in range(3)]
current_player = "X" 
winner = None
game_over = False

cell_w = width // 3
cell_h = height // 3

# cv
homography_matrix = None
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
    for i in range(3):
        if board[i][0] == board[i][1] == board[i][2] == player: return True
        if board[0][i] == board[1][i] == board[2][i] == player: return True
    if board[0][0] == board[1][1] == board[2][2] == player: return True
    if board[0][2] == board[1][1] == board[2][0] == player: return True
    return False

def check_game_status():
    global winner, game_over
    if check_win_condition("X"): winner = "X"; game_over = True; return
    if check_win_condition("O"): winner = "O"; game_over = True; return
    if all(board[r][c] != "" for r in range(3) for c in range(3)): winner = "Tie"; game_over = True

def get_computer_move():
    open_spaces = [(r, c) for r in range(3) for c in range(3) if board[r][c] == ""]
    return random.choice(open_spaces) if open_spaces else None

def reset_game():
    global board, current_player, winner, game_over, reference_gray, motion_detected, stable_frames
    board = [["" for _ in range(3)] for _ in range(3)]
    current_player = "X"
    winner = None
    game_over = False
    reference_gray = None
    motion_detected = False
    stable_frames = 0
run = True
while run:
    ret, frame = cap.read();
    if not ret:
        run = False

    
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
        
    cv2.imshow("Webcam Live Feed / ArUco Diagnostics", diagnostic_frame)
    
    cv2.waitKey(1)
        
    ############### PYGAME ###############
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
            
        elif event.type == pygame.VIDEORESIZE:
            # DYNAMIC WINDOW RECALIBRATION
            width, height = event.w, event.h
            screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
            cell_w = width // 3
            cell_h = height // 3
            homography_matrix = None 
            prev_gray = None 
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r: 
                reset_game()
    
    M = find_homography(frame, width, height)
    if M is not None:
        homography_matrix = M  
    
    if homography_matrix is None:
        display_frame = np.full((height, width, 3), 255, dtype=np.uint8)
        cv2.putText(display_frame, "CALIBRATION ERROR: Check Diagnostics Window", (15, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2, cv2.LINE_AA)
        frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        frame_surface = pygame.image.frombuffer(frame_rgb.tobytes(), (width, height), "RGB")
        screen.blit(frame_surface, (0, 0))
        
        screen.blit(markers_surf[0], (0, 0))
        screen.blit(markers_surf[1], (width - MARKER_SIZE, 0))
        screen.blit(markers_surf[2], (width - MARKER_SIZE, height - MARKER_SIZE))
        screen.blit(markers_surf[3], (0, height - MARKER_SIZE))
        pygame.display.update()
        continue
    
    warped_frame = cv2.warpPerspective(frame, homography_matrix, (width, height))
    gray = cv2.cvtColor(warped_frame, cv2.COLOR_BGR2GRAY)
    gray_blurred = cv2.GaussianBlur(gray, (21, 21), 0)

    if prev_gray is None:
        prev_gray = gray_blurred
        reference_gray = gray_blurred
        continue
    
    if not game_over and current_player == "X":
        frame_delta = cv2.absdiff(prev_gray, gray_blurred)
        
        frame_delta[0:60, :] = 0 
        frame_delta[0:MARKER_SIZE, 0:MARKER_SIZE] = 0
        frame_delta[0:MARKER_SIZE, width-MARKER_SIZE:width] = 0
        frame_delta[height-MARKER_SIZE:height, width-MARKER_SIZE:width] = 0
        frame_delta[height-MARKER_SIZE:height, 0:MARKER_SIZE] = 0
        
        _, thresh_delta = cv2.threshold(frame_delta, 20, 255, cv2.THRESH_BINARY)
        changed_pixels = cv2.countNonZero(thresh_delta)
                
        best_cell = None
        max_ink_density = 0
        
        motion_threshold = int((width * height) * 0.005)
        
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
                    
                    turn_delta = cv2.absdiff(reference_gray, gray_blurred)
                    turn_delta[0:60, :] = 0
                    turn_delta[0:MARKER_SIZE, 0:MARKER_SIZE] = 0
                    turn_delta[0:MARKER_SIZE, width-MARKER_SIZE:width] = 0
                    turn_delta[height-MARKER_SIZE:height, width-MARKER_SIZE:width] = 0
                    turn_delta[height-MARKER_SIZE:height, 0:MARKER_SIZE] = 0
                    
                    _, turn_thresh = cv2.threshold(turn_delta, 70, 255, cv2.THRESH_BINARY)
                    
                    
                    cv2.imshow("turn_thresh", turn_thresh)
                    
                    
                    best_cell = None
                    max_ink_density = 0
                    
                    for r in range(3):
                        for c in range(3):
                            if board[r][c] == "":
                                # 1. Crop the cell region of interest
                                cell_roi = turn_thresh[r*cell_h : (r+1)*cell_h, c*cell_w : (c+1)*cell_w]
                                
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
                        check_game_status()
                        if not game_over: current_player = "O"
                    else:
                        status_msg = "Scan failed. Bolder lines are required."
            else:
                if M is not None:
                    status_msg = "Your Turn: Draw your marker step."
                    status_color = (0, 120, 0)
                else:
                    status_msg = "Webcam tag coverage dropped. Running fallback memory calculations..."
                    status_color = (120, 120, 0)

    elif game_over:
        if winner == "Tie":
            status_msg = "Tie match! Hit 'R' to wipe board."
            status_color = (100, 100, 100)
        else:
            status_msg = f"Victory! Winner: {winner}. Hit 'R' to clear."
            status_color = (0, 120, 0) if winner == "X" else (0, 0, 200)

    prev_gray = gray_blurred
    
    display_frame = np.full((height, width, 3), 255, dtype=np.uint8)
    cv2.putText(display_frame, status_msg, (15, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_color, 2, cv2.LINE_AA)
    
    frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
    frame_surface = pygame.image.frombuffer(frame_rgb.tobytes(), (width, height), "RGB")
    screen.blit(frame_surface, (0, 0))

    # Fix anchor graphics to corners regardless of size mutations
    screen.blit(markers_surf[0], (0, 0))
    screen.blit(markers_surf[1], (width - MARKER_SIZE, 0))
    screen.blit(markers_surf[2], (width - MARKER_SIZE, height - MARKER_SIZE))
    screen.blit(markers_surf[3], (0, height - MARKER_SIZE))

    # 6. Computer Move Calculations
    if not game_over and current_player == "O":
        time.sleep(0.5)
        move = get_computer_move()
        if move:
            r, c = move
            board[r][c] = "O"
            check_game_status()
        current_player = "X"
        
    for i in range(1, 3):
        pygame.draw.line(screen, (70, 70, 70), (i * cell_w, 0), (i * cell_w, height), 3)
        pygame.draw.line(screen, (70, 70, 70), (0, i * cell_h), (width, i * cell_h), 3)

    for r in range(3):
        for c in range(3):
            center_x = c * cell_w + cell_w // 2
            center_y = r * cell_h + cell_h // 2
            offset = min(cell_w, cell_h) // 4
            
            if board[r][c] == "X":
                pygame.draw.line(screen, (34, 139, 34), (center_x - offset, center_y - offset), (center_x + offset, center_y + offset), 5)
                pygame.draw.line(screen, (34, 139, 34), (center_x + offset, center_y - offset), (center_x - offset, center_y + offset), 5)
            elif board[r][c] == "O":
                pygame.draw.circle(screen, (220, 20, 60), (center_x, center_y), offset, 6)

    pygame.display.update()
        
print("program stoped")
cap.release()
cv2.destroyAllWindows()
pygame.quit()
sys.exit()