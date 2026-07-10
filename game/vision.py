"""ArUco marker detection and homography calibration.

The board's coordinate system is a closed digital loop: pygame draws four ArUco
markers at the board's corners, a webcam watches the physical display, and the
detected marker corners are used to compute a homography that warps future camera
frames back into "board pixel" space. Nothing here is a physical/fixed marker, so
recalibration is safe and automatic whenever the board is resized or momentarily lost.
"""
import cv2
import numpy as np
import pygame

MARKER_SIZE = 140

aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
aruco_params = cv2.aruco.DetectorParameters()
aruco_params.adaptiveThreshWinSizeMin = 3
aruco_params.adaptiveThreshWinSizeMax = 25
aruco_params.adaptiveThreshWinSizeStep = 10
aruco_params.minMarkerPerimeterRate = 0.02

detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)


def generate_marker_surfaces():
    """Generates the 4 ArUco corner-marker images shown during calibration, keyed by id."""
    surfaces = {}
    for m_id in range(4):
        core = cv2.aruco.generateImageMarker(aruco_dict, m_id, MARKER_SIZE - 30)
        padded = cv2.copyMakeBorder(core, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=255)
        rgb_marker = cv2.cvtColor(padded, cv2.COLOR_GRAY2RGB)
        surfaces[m_id] = pygame.image.frombuffer(rgb_marker.tobytes(), (MARKER_SIZE, MARKER_SIZE), "RGB")
    return surfaces


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
