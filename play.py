import cv2
import pygame
import numpy as np
import time
import sys
import random

from game import ai, config, flow
from game import layout as layout_mod
from game import vision as vision_mod
from game.animation import punch_scale
from game.assets import Assets
from game.console import ConsoleResetListener
from game.state import GameState, VisionState
from game.ui import board as board_ui
from game.ui import panel as panel_ui
from game.ui import widgets as ui_widgets

pygame.init()
pygame.mixer.init()
pygame.font.init()
assets = Assets()


def play_outcome_sound(outcome):
    if outcome == "win":
        assets.sounds.win.play()
    elif outcome == "loss":
        assets.sounds.lose.play()
    elif outcome == "tie":
        assets.sounds.tie.play()

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

display_info = pygame.display.Info()
width, height = display_info.current_w, display_info.current_h  # Fullscreen size

kernel = np.ones((5, 5), np.uint8)

screen = pygame.display.set_mode((width, height), pygame.FULLSCREEN)
pygame.display.set_caption("Foil Sandbox (OBS Capture Target)")

markers_surf = vision_mod.generate_marker_surfaces()

layout = layout_mod.Layout(width, height)
state = GameState()
vision = VisionState()

run = True
with ConsoleResetListener() as console:
    while run:
        ret, frame = cap.read()
        if not ret:
            run = False

        if console.reset_requested():
            print("Manual reset requested from console.")
            flow.enter_level_select(state, vision)

        diagnostic_frame = frame.copy()
        raw_gray = cv2.cvtColor(diagnostic_frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = vision_mod.detector.detectMarkers(raw_gray)

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
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                layout.resize(event.w, event.h)
                vision.homography_matrix = None
                vision.prev_gray = None
                vision.homography_locked = False
                print(f"Window resized to {event.w}x{event.h}. Recalibrating ArUco tracking...")
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    flow.enter_level_select(state, vision)

        M = vision_mod.find_homography(frame, layout.board_w, layout.board_h)
        if M is not None:
            if not vision.homography_locked:
                print("ArUco calibration locked: all 4 markers found.")
                assets.sounds.calibration_locked.play()
                vision.homography_locked = True
            vision.homography_matrix = M

        if vision.homography_matrix is None:
            screen.fill((255, 255, 255))

            screen.blit(markers_surf[0], (0, 0))
            screen.blit(markers_surf[1], (layout.board_w - vision_mod.MARKER_SIZE, 0))
            screen.blit(markers_surf[2], (layout.board_w - vision_mod.MARKER_SIZE, layout.board_h - vision_mod.MARKER_SIZE))
            screen.blit(markers_surf[3], (0, layout.board_h - vision_mod.MARKER_SIZE))
            panel_ui.draw_side_panel(screen, layout, state, assets.fonts)
            pygame.display.update()
            continue

        warped_frame = cv2.warpPerspective(frame, vision.homography_matrix, (layout.board_w, layout.board_h))
        gray = cv2.cvtColor(warped_frame, cv2.COLOR_BGR2GRAY)
        gray_blurred = cv2.GaussianBlur(gray, (21, 21), 0)

        if vision.prev_gray is None:
            vision.prev_gray = gray_blurred
            vision.reference_gray = gray_blurred
            continue

        if state.game_phase == "LEVEL_SELECT":
            frame_delta = cv2.absdiff(vision.prev_gray, gray_blurred)
            _, thresh_delta = cv2.threshold(frame_delta, 20, 255, cv2.THRESH_BINARY)
            changed_pixels = cv2.countNonZero(thresh_delta)

            motion_threshold = int((layout.board_w * layout.board_h) * 0.005)

            if changed_pixels > motion_threshold:
                vision.motion_detected = True
                vision.stable_frames = 0
                state.status_msg = "Ink strokes detected..."
                state.status_color = (0, 0, 255)
            else:
                if vision.motion_detected:
                    vision.stable_frames += 1
                    state.status_msg = f"Hold still... scanning ink in {max(0, 20 - vision.stable_frames)}"
                    state.status_color = (0, 100, 200)

                    if vision.stable_frames >= 20:
                        vision.motion_detected = False
                        vision.stable_frames = 0

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
                        for level_name, rect in board_ui.get_level_zones(layout).items():
                            if level_name not in config.LEVEL_SKILLS:
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
                            state.bot_skill = config.LEVEL_SKILLS[best_level]
                            state.current_level_label = best_level.upper()
                            print(f"Difficulty selected: {best_level.upper()} (BOT_SKILL={state.bot_skill:.2f})")
                            assets.sounds.button_confirm.play()
                            flow.start_level_confirm(state, best_level)
                        else:
                            print("Difficulty scan failed: no zone matched confidently.")
                            state.status_msg = "Scan failed. Mark EASY, MID, or HARD with an X."
                            #assets.sounds.error.play()
                else:
                    state.status_msg = "Choose a difficulty: draw an X over EASY, MID, or HARD."
                    state.status_color = (0, 120, 0)

        elif state.game_phase == "LEVEL_CONFIRM":
            state.status_msg = f"{state.confirm_level.upper()} selected!"
            state.status_color = (0, 120, 0)
            if time.time() - state.confirm_start_time >= config.CONFIRM_DURATION:
                flow.reset_game(state, vision)
                state.game_phase = "PLAYING"

        elif state.game_phase == "PLAYING" and not state.game_over and state.current_player == "X":
            frame_delta = cv2.absdiff(vision.prev_gray, gray_blurred)

            _, thresh_delta = cv2.threshold(frame_delta, 20, 255, cv2.THRESH_BINARY)
            changed_pixels = cv2.countNonZero(thresh_delta)

            motion_threshold = int((layout.board_w * layout.board_h) * 0.005)

            if changed_pixels > motion_threshold:
                if not vision.motion_detected:
                    vision.motion_detected = True
                    vision.reference_gray = vision.prev_gray.copy()
                vision.stable_frames = 0
                state.status_msg = "Ink strokes detected..."
                state.status_color = (0, 0, 255)
            else:
                if vision.motion_detected:
                    vision.stable_frames += 1
                    state.status_msg = f"Hold still... scanning ink in {max(0, 20 - vision.stable_frames)}"
                    state.status_color = (0, 100, 200)

                    if vision.stable_frames >= 20:
                        vision.motion_detected = False
                        vision.stable_frames = 0

                        turn_delta = cv2.cvtColor(warped_frame, cv2.COLOR_BGR2GRAY)
                        turn_delta = cv2.erode(turn_delta, kernel, iterations=5)

                        _, turn_thresh_inv = cv2.threshold(turn_delta, 160, 255, cv2.THRESH_BINARY_INV)
                        turn_thresh = cv2.GaussianBlur(turn_thresh_inv, (7, 7), 0)

                        print("Scanning board for a new X placement...")

                        best_cell = None
                        max_ink_density = 0

                        for r in range(3):
                            for c in range(3):
                                if state.board[r][c] == "":
                                    # 1. Crop the cell region of interest
                                    cy = layout.board_rect.top + r * layout.cell_h
                                    cx = layout.board_rect.left + c * layout.cell_w
                                    cell_roi = turn_thresh[cy: cy + layout.cell_h, cx: cx + layout.cell_w]

                                    # 2. Resize to 32x32 to match your model's input size
                                    cell_resized = cv2.resize(cell_roi, (32, 32))

                                    # 3. Reshape to (1, 32, 32, 1) -> Batch, Height, Width, Channel
                                    cell_input = cell_resized.reshape(1, 32, 32, 1).astype(np.float32) / 255.0

                                    # 4. Run prediction
                                    predictions = assets.model.predict(cell_input, verbose=0)  # verbose=0 keeps terminal clean
                                    x_confidence = predictions[0][1]

                                    # 5. Check if this is the strongest "X" we've seen so far
                                    # (e.g., must be higher than previous max and at least 70% confident)
                                    if x_confidence > max_ink_density and x_confidence > 0.70:
                                        max_ink_density = x_confidence
                                        best_cell = (r, c)

                        if best_cell:
                            r, c = best_cell
                            flow.place_mark(state, r, c, "X")
                            assets.sounds.x_place.play()
                            print(f"Player placed X at row {r}, col {c} (confidence {max_ink_density:.2f})")
                            play_outcome_sound(flow.check_game_status(state))
                            if not state.game_over:
                                state.current_player = "O"
                                state.bot_move_ready_time = time.time() + config.BOT_MOVE_DELAY
                        else:
                            print("Scan failed: no cell matched confidently as X.")
                            state.status_msg = "Scan failed. Bolder lines are required."
                            #assets.sounds.error.play()
                else:
                    if M is not None:
                        state.status_msg = "Your Turn: Draw your marker step."
                        state.status_color = (0, 120, 0)
                    else:
                        state.status_msg = "Webcam tag coverage dropped. Running fallback memory calculations..."
                        state.status_color = (120, 120, 0)

        elif state.game_phase == "PLAYING" and not state.game_over and state.current_player == "O":
            state.status_msg = "Bot is thinking..."
            state.status_color = (30, 100, 220)
            if state.bot_move_ready_time is not None and time.time() >= state.bot_move_ready_time:
                opening_move = state.bot_opens
                if state.bot_opens:
                    empty_cells = [(r, c) for r in range(3) for c in range(3) if state.board[r][c] == ""]
                    move = random.choice(empty_cells) if empty_cells else None
                    state.bot_opens = False
                else:
                    move = ai.get_computer_move(state.board, state.bot_skill)
                if move:
                    r, c = move
                    flow.place_mark(state, r, c, "O")
                    assets.sounds.o_place.play()
                    print(f"Bot placed O at row {r}, col {c}" + (" (random opening move)" if opening_move else ""))
                    play_outcome_sound(flow.check_game_status(state))
                state.current_player = "X"
                state.bot_move_ready_time = None

        elif state.game_phase == "PLAYING" and state.game_over:
            since_game_over = time.time() - state.game_over_time
            if since_game_over < config.REVEAL_DELAY:
                state.status_msg = "Tie match!" if state.winner == "Tie" else f"Victory! Winner: {state.winner}."
                state.status_color = (100, 100, 100) if state.winner == "Tie" else ((0, 120, 0) if state.winner == "X" else (30, 100, 220))
            else:
                remaining = max(0, config.RESTART_DELAY - int(since_game_over - config.REVEAL_DELAY))
                if remaining != state.last_countdown_tick:
                    assets.sounds.tick.play()
                    state.last_countdown_tick = remaining
                if state.winner == "Tie":
                    state.status_msg = f"Tie match! Restarting in {remaining}..."
                    state.status_color = (100, 100, 100)
                else:
                    state.status_msg = f"Victory! Winner: {state.winner}. Restarting in {remaining}..."
                    state.status_color = (0, 120, 0) if state.winner == "X" else (30, 100, 220)

            if since_game_over >= config.REVEAL_DELAY + config.RESTART_DELAY:
                print("Restart timer elapsed.")
                flow.enter_level_select(state, vision)

        vision.prev_gray = gray_blurred

        screen.fill((255, 255, 255))

        if state.game_phase == "LEVEL_SELECT":
            zones = board_ui.get_level_zones(layout)
            for level_name, rect in zones.items():
                if level_name == "filler":
                    board_ui.draw_zone(screen, assets.fonts.countdown, rect, "", config.FILLER_COLOR)
                else:
                    board_ui.draw_zone(screen, assets.fonts.countdown, rect, level_name.upper(), config.LEVEL_BUTTON_COLORS[level_name])

        elif state.game_phase == "LEVEL_CONFIRM":
            elapsed = time.time() - state.confirm_start_time
            t = min(1.0, elapsed / config.CONFIRM_DURATION)
            scale = punch_scale(t)
            rect = board_ui.get_level_zones(layout)[state.confirm_level]
            board_ui.draw_zone(screen, assets.fonts.countdown, rect, state.confirm_level.upper(),
                                config.LEVEL_BUTTON_COLORS[state.confirm_level], scale=scale)

        elif state.game_phase == "PLAYING":
            board_surf = board_ui.render_board_surface(layout, state, assets.fonts, include_result=True)
            board_ui.clip_to_board_radius(board_surf)
            screen.blit(board_surf, layout.board_rect.topleft)

        board_border_color = tuple(max(0, ch - 60) for ch in config.LEVEL_COLORS.get(state.current_level_label, config.NO_DIFFICULTY_COLOR))
        ui_widgets.draw_translucent_border(screen, layout.board_rect, board_border_color, config.PANEL_RADIUS)

        panel_ui.draw_side_panel(screen, layout, state, assets.fonts)
        pygame.display.update()

print("program stoped")
cap.release()
cv2.destroyAllWindows()
pygame.quit()
sys.exit()
