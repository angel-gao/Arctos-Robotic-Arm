"""
Camera Gesture Manager for Arctos Control

Threaded webcam + MediaPipe hand tracking for gesture-based robot control.
Emits the same state dict format as JoystickManager for plug-compatible integration.

Control mapping:
    Right hand OUTSIDE neutral zone: X (left/right), Y (up/down)
    Right hand INSIDE neutral zone:  A (wrist rotation), B (wrist flexion)
    Left hand INSIDE neutral zone:   Z (wrist flexion), C (wrist rotation)
    Gripper: right hand finger openness (any zone, calibrated neutral)

All outputs are binary (±1.0 or 0) — no proportional scaling.
Requires calibration before use to capture neutral wrist angles and finger openness.
"""

import cv2
import math
import sys
import time
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False


class CameraManager(QThread):
    """Background thread for webcam hand tracking with wrist gesture control."""

    # Signals
    camera_connected = pyqtSignal(str)
    camera_disconnected = pyqtSignal()
    camera_update = pyqtSignal(dict)
    frame_ready = pyqtSignal(QImage)
    error_occurred = pyqtSignal(str)
    calibration_progress = pyqtSignal(int)  # 0-100

    # MediaPipe landmark indices
    WRIST = 0
    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4
    INDEX_MCP = 5
    INDEX_TIP = 8
    MIDDLE_MCP = 9
    MIDDLE_TIP = 12
    RING_MCP = 13
    RING_TIP = 16
    PINKY_MCP = 17
    PINKY_TIP = 20

    def __init__(self, camera_index: int = 0):
        super().__init__()
        self.camera_index = camera_index
        self.running = False
        self._connected = False

        # Dry-run mode: emit state dict but UI won't send GRBL commands
        self.dry_run = True

        # Load config
        from core.config import Config
        self._cfg = Config().camera_gesture_config

        # Calibration state
        self._calibrated = False
        self._calibration_target = None  # "right", "left", or None
        self._calibration_samples = []

        # Calibrated neutral angles
        self._neutral_right_rotation = 0.0   # A axis
        self._neutral_right_flexion = 0.0    # B axis
        self._neutral_left_rotation = 0.0    # C axis
        self._neutral_left_flexion = 0.0     # Z axis
        self._neutral_finger_openness = 0.0  # Gripper resting openness

        # Smoothing buffers
        self._smooth_size = self._cfg['smoothing_frames']
        self._right_rotation_buf = []
        self._right_flexion_buf = []
        self._left_rotation_buf = []
        self._left_flexion_buf = []
        self._right_pos_buf = []
        self._finger_openness_buf = []

        # Neutral zone hysteresis state
        self._right_in_neutral = False
        self._left_in_neutral = False

    def is_connected(self) -> bool:
        return self._connected

    def is_calibrated(self) -> bool:
        return self._calibrated

    def set_calibrated(self, value: bool):
        self._calibrated = value

    def start_calibration(self, target: str):
        """Start capturing calibration samples. target: 'right' or 'left'."""
        self._calibration_target = target
        self._calibration_samples = []

    def finish_calibration(self) -> bool:
        """Compute neutral angles from collected samples. Returns True if enough data."""
        if len(self._calibration_samples) < 20:
            self._calibration_target = None
            return False

        if self._calibration_target == "right":
            # Samples are (rotation, flexion, finger_openness)
            avg_rot = sum(s[0] for s in self._calibration_samples) / len(self._calibration_samples)
            avg_flex = sum(s[1] for s in self._calibration_samples) / len(self._calibration_samples)
            avg_open = sum(s[2] for s in self._calibration_samples) / len(self._calibration_samples)
            self._neutral_right_rotation = avg_rot
            self._neutral_right_flexion = avg_flex
            self._neutral_finger_openness = avg_open

        elif self._calibration_target == "left":
            # Samples are (rotation, flexion)
            avg_rot = sum(s[0] for s in self._calibration_samples) / len(self._calibration_samples)
            avg_flex = sum(s[1] for s in self._calibration_samples) / len(self._calibration_samples)
            self._neutral_left_rotation = avg_rot
            self._neutral_left_flexion = avg_flex

        self._calibration_samples = []
        self._calibration_target = None
        return True

    def stop(self):
        self.running = False

    def run(self):
        """Main camera loop."""
        if not MEDIAPIPE_AVAILABLE:
            self.error_occurred.emit("MediaPipe not installed. Run: pip install mediapipe")
            return

        # Open webcam
        if sys.platform == 'win32':
            cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            self.error_occurred.emit(f"Cannot open camera {self.camera_index}")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._connected = True
        self.camera_connected.emit(f"Camera {actual_w}x{actual_h}")
        self.running = True

        target_fps = 25
        frame_interval = 1.0 / target_fps

        mp_hands = mp.solutions.hands
        mp_draw = mp.solutions.drawing_utils

        try:
            with mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.6
            ) as hands:
                while self.running:
                    frame_start = time.time()

                    ret, frame = cap.read()
                    if not ret:
                        self.error_occurred.emit("Camera frame read failed")
                        break

                    # Mirror for natural movement
                    frame = cv2.flip(frame, 1)
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = hands.process(rgb_frame)

                    # Process landmarks into control state
                    state = self._process_results(results)
                    self.camera_update.emit(state)

                    # Draw overlays on frame
                    self._draw_overlays(frame, results, state, mp_hands, mp_draw)

                    # Convert to QImage for preview
                    h, w, ch = frame.shape
                    bytes_per_line = ch * w
                    rgb_display = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    q_img = QImage(rgb_display.data, w, h, bytes_per_line,
                                   QImage.Format.Format_RGB888)
                    self.frame_ready.emit(q_img.copy())

                    # Throttle
                    elapsed = time.time() - frame_start
                    sleep_time = frame_interval - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)

        except Exception as e:
            if self.running:
                self.error_occurred.emit(f"Camera error: {str(e)}")
        finally:
            cap.release()
            self._connected = False
            self.camera_disconnected.emit()

    # ========== Gesture Detection Helpers ==========

    def _calculate_wrist_rotation(self, landmarks) -> float:
        """Angle of INDEX_MCP->PINKY_MCP line relative to horizontal, in degrees."""
        idx = landmarks.landmark[self.INDEX_MCP]
        pinky = landmarks.landmark[self.PINKY_MCP]
        return math.degrees(math.atan2(pinky.y - idx.y, pinky.x - idx.x))

    def _calculate_wrist_flexion(self, landmarks) -> float:
        """Angle of WRIST->MIDDLE_MCP vector relative to vertical (up), in degrees."""
        wrist = landmarks.landmark[self.WRIST]
        mcp = landmarks.landmark[self.MIDDLE_MCP]
        # atan2(horizontal_component, upward_component)
        # wrist.y - mcp.y = upward (y is inverted in image coords)
        return math.degrees(math.atan2(mcp.x - wrist.x, wrist.y - mcp.y))

    def _calculate_finger_openness(self, landmarks) -> float:
        """
        Calculate how open/extended fingers are, orientation-independent.

        Measures average normalized distance of fingertips from wrist.
        Works regardless of palm orientation (front-facing or sideways).
        """
        wrist = landmarks.landmark[self.WRIST]
        middle_mcp = landmarks.landmark[self.MIDDLE_MCP]

        # Hand size reference (wrist to middle MCP)
        hand_size = math.hypot(middle_mcp.x - wrist.x, middle_mcp.y - wrist.y)
        if hand_size < 0.01:
            return 0.0

        tips = [
            landmarks.landmark[self.INDEX_TIP],
            landmarks.landmark[self.MIDDLE_TIP],
            landmarks.landmark[self.RING_TIP],
            landmarks.landmark[self.PINKY_TIP],
        ]

        # Average normalized tip distance from wrist
        total = 0.0
        for tip in tips:
            dist = math.hypot(tip.x - wrist.x, tip.y - wrist.y)
            total += dist / hand_size
        return total / len(tips)

    def _smooth(self, buf: list, value: float) -> float:
        """Add value to buffer, return smoothed average."""
        buf.append(value)
        if len(buf) > self._smooth_size:
            buf.pop(0)
        return sum(buf) / len(buf)

    def _check_neutral_zone(self, x: float, y: float, currently_in: bool) -> bool:
        """
        Check neutral zone with hysteresis to prevent flickering at boundary.

        To ENTER neutral zone: hand must be well inside (nz - margin).
        To EXIT neutral zone: hand must be well outside (nz + margin).
        """
        nz = self._cfg['neutral_zone']
        margin = 0.05  # hysteresis margin

        if currently_in:
            # Must move clearly outside to exit
            return abs(x - 0.5) < (nz + margin) and abs(y - 0.5) < (nz + margin)
        else:
            # Must move clearly inside to enter
            return abs(x - 0.5) < (nz - margin) and abs(y - 0.5) < (nz - margin)

    # ========== Main Processing ==========

    def _process_results(self, results) -> dict:
        """Convert MediaPipe results to joystick-compatible state dict.

        All axis outputs are binary (±1.0 or 0). Direction convention:
        - X: positive = hand moves right
        - Y: positive = hand moves up
        - A: positive = wrist rotates clockwise (viewer perspective)
        - Z: positive = left wrist flexes up
        - B (hat): positive = right wrist flexes up
        - C (hat): positive = left wrist rotates clockwise
        - Gripper: buttons[1]=close, buttons[3]=open
        """
        axes = [0.0, 0.0, 0.0, 0.0]  # [X, Y, A, Z]
        buttons = [0, 0, 0, 0]        # [_, close, _, open]
        hats = [(0, 0)]                # [(B, C)]

        if not results.multi_hand_landmarks or not results.multi_handedness:
            self._clear_buffers()
            self._right_in_neutral = False
            self._left_in_neutral = False
            return {'axes': axes, 'buttons': buttons, 'hats': hats}

        # Separate hands (MediaPipe labels match the user's actual hands)
        right_lm = None
        left_lm = None
        for i, handedness in enumerate(results.multi_handedness):
            label = handedness.classification[0].label
            lm = results.multi_hand_landmarks[i]
            if label == "Right":
                right_lm = lm
            elif label == "Left":
                left_lm = lm

        hat_b = 0
        hat_c = 0

        # === RIGHT HAND ===
        if right_lm:
            wrist = right_lm.landmark[self.WRIST]

            # Calibration mode
            if self._calibration_target == "right":
                rot = self._calculate_wrist_rotation(right_lm)
                flex = self._calculate_wrist_flexion(right_lm)
                openness = self._calculate_finger_openness(right_lm)
                self._calibration_samples.append((rot, flex, openness))
                self.calibration_progress.emit(len(self._calibration_samples))

            elif self._calibrated:
                # Update neutral zone state with hysteresis
                self._right_in_neutral = self._check_neutral_zone(
                    wrist.x, wrist.y, self._right_in_neutral
                )

                if self._right_in_neutral:
                    # WRIST MODE: A axis (rotation) + B axis (flexion)
                    raw_rot = self._calculate_wrist_rotation(right_lm)
                    smooth_rot = self._smooth(self._right_rotation_buf, raw_rot)
                    rot_offset = smooth_rot - self._neutral_right_rotation

                    rot_thresh = self._cfg['wrist_rotation_threshold']
                    if abs(rot_offset) > rot_thresh:
                        axes[2] = 1.0 if rot_offset > 0 else -1.0  # A axis

                    raw_flex = self._calculate_wrist_flexion(right_lm)
                    smooth_flex = self._smooth(self._right_flexion_buf, raw_flex)
                    flex_offset = smooth_flex - self._neutral_right_flexion

                    flex_thresh = self._cfg['wrist_flexion_threshold']
                    if abs(flex_offset) > flex_thresh:
                        hat_b = 1 if flex_offset > 0 else -1  # B axis
                else:
                    # POSITION MODE: X and Y axes (binary output)
                    nz = self._cfg['neutral_zone']

                    # Smooth position
                    x_off = wrist.x - 0.5
                    y_off = wrist.y - 0.5
                    self._right_pos_buf.append((x_off, y_off))
                    if len(self._right_pos_buf) > self._smooth_size:
                        self._right_pos_buf.pop(0)
                    sx = sum(p[0] for p in self._right_pos_buf) / len(self._right_pos_buf)
                    sy = sum(p[1] for p in self._right_pos_buf) / len(self._right_pos_buf)

                    # Binary output: ±1.0 when outside neutral zone
                    if abs(sx) > nz:
                        axes[0] = 1.0 if sx > 0 else -1.0  # X: right = positive
                    if abs(sy) > nz:
                        # Y: hand up = sy < 0 = positive output
                        axes[1] = -1.0 if sy > 0 else 1.0

                # GRIPPER (always active for right hand, orientation-independent)
                raw_openness = self._calculate_finger_openness(right_lm)
                smooth_openness = self._smooth(self._finger_openness_buf, raw_openness)
                openness_diff = smooth_openness - self._neutral_finger_openness
                deadzone = self._cfg['finger_spread_deadzone']

                if openness_diff > deadzone:
                    buttons[3] = 1  # Open (fingers more extended than neutral)
                elif openness_diff < -deadzone:
                    buttons[1] = 1  # Close (fingers more curled than neutral)
        else:
            self._right_rotation_buf.clear()
            self._right_flexion_buf.clear()
            self._right_pos_buf.clear()
            self._finger_openness_buf.clear()
            self._right_in_neutral = False

        # === LEFT HAND ===
        if left_lm:
            wrist = left_lm.landmark[self.WRIST]

            if self._calibration_target == "left":
                rot = self._calculate_wrist_rotation(left_lm)
                flex = self._calculate_wrist_flexion(left_lm)
                self._calibration_samples.append((rot, flex))
                self.calibration_progress.emit(len(self._calibration_samples))

            elif self._calibrated:
                # Update neutral zone state with hysteresis
                self._left_in_neutral = self._check_neutral_zone(
                    wrist.x, wrist.y, self._left_in_neutral
                )

                if self._left_in_neutral:
                    # Z axis: wrist flexion (same method as B on right hand)
                    raw_flex = self._calculate_wrist_flexion(left_lm)
                    smooth_flex = self._smooth(self._left_flexion_buf, raw_flex)
                    flex_offset = smooth_flex - self._neutral_left_flexion

                    flex_thresh = self._cfg['wrist_flexion_threshold']
                    if abs(flex_offset) > flex_thresh:
                        # Inverted: flex up = Z-, flex down = Z+
                        axes[3] = -1.0 if flex_offset > 0 else 1.0  # Z axis

                    # C axis: wrist rotation
                    raw_rot = self._calculate_wrist_rotation(left_lm)
                    smooth_rot = self._smooth(self._left_rotation_buf, raw_rot)
                    rot_offset = smooth_rot - self._neutral_left_rotation

                    rot_thresh = self._cfg['wrist_rotation_threshold']
                    if abs(rot_offset) > rot_thresh:
                        hat_c = 1 if rot_offset > 0 else -1
        else:
            self._left_rotation_buf.clear()
            self._left_flexion_buf.clear()
            self._left_in_neutral = False

        hats = [(hat_b, hat_c)]
        return {'axes': axes, 'buttons': buttons, 'hats': hats}

    def _clear_buffers(self):
        """Clear all smoothing buffers."""
        self._right_rotation_buf.clear()
        self._right_flexion_buf.clear()
        self._left_rotation_buf.clear()
        self._left_flexion_buf.clear()
        self._right_pos_buf.clear()
        self._finger_openness_buf.clear()

    # ========== Overlay Drawing ==========

    def _draw_overlays(self, frame, results, state, mp_hands, mp_draw):
        """Draw hand landmarks, neutral zone, and debug info on frame."""
        h, w = frame.shape[:2]
        nz = self._cfg['neutral_zone']

        # Neutral zone rectangle (thick border)
        x1 = int(w * (0.5 - nz))
        y1 = int(h * (0.5 - nz))
        x2 = int(w * (0.5 + nz))
        y2 = int(h * (0.5 + nz))
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
        cv2.putText(frame, "NEUTRAL ZONE", (x1 + 5, y1 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Hand landmarks
        if results.multi_hand_landmarks:
            for hand_lm in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, hand_lm, mp_hands.HAND_CONNECTIONS)

        # Dry-run banner
        if self.dry_run:
            cv2.putText(frame, "DRY RUN - no robot commands", (w // 2 - 180, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        # Calibration status
        if self._calibration_target:
            cv2.putText(frame, f"CALIBRATING: {self._calibration_target.upper()} HAND",
                        (w // 2 - 160, 55),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            cv2.putText(frame, f"Samples: {len(self._calibration_samples)}",
                        (w // 2 - 60, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
            return  # Skip axis display during calibration

        if not self._calibrated:
            cv2.putText(frame, "NOT CALIBRATED", (w // 2 - 90, 55),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            return

        # Determine right hand mode from hysteresis state
        right_mode = "---"
        if self._right_in_neutral:
            right_mode = "WRIST (A/B)"
        elif results.multi_hand_landmarks and results.multi_handedness:
            for i, handedness in enumerate(results.multi_handedness):
                if handedness.classification[0].label == "Right":
                    right_mode = "POSITION (X/Y)"

        # Axis status display
        axes = state['axes']
        y_pos = 30
        axis_info = [
            ('X', axes[0]),
            ('Y', axes[1]),
            ('A', axes[2]),
            ('Z', axes[3]),
        ]
        for name, val in axis_info:
            if val != 0:
                direction = "+" if val > 0 else "-"
                color = (0, 255, 0)
            else:
                direction = " "
                color = (100, 100, 100)
            cv2.putText(frame, f"{name}: {direction}", (10, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            y_pos += 25

        # B/C from hats
        hat = state['hats'][0]
        for name, val in [('B', hat[0]), ('C', hat[1])]:
            if val != 0:
                direction = "+" if val > 0 else "-"
                color = (0, 255, 0)
            else:
                direction = " "
                color = (100, 100, 100)
            cv2.putText(frame, f"{name}: {direction}", (10, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            y_pos += 25

        # Gripper
        if state['buttons'][1]:
            cv2.putText(frame, "GRIP: CLOSE", (10, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        elif state['buttons'][3]:
            cv2.putText(frame, "GRIP: OPEN", (10, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 0), 2)
        else:
            cv2.putText(frame, "GRIP: ---", (10, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 2)

        y_pos += 30
        # Right hand mode
        cv2.putText(frame, f"R: {right_mode}", (10, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 0), 1)

        # Left hand zone state
        y_pos += 20
        left_mode = "---"
        if self._left_in_neutral:
            left_mode = "WRIST (Z/C)"
        elif results.multi_hand_landmarks and results.multi_handedness:
            for i, handedness in enumerate(results.multi_handedness):
                if handedness.classification[0].label == "Left":
                    left_mode = "OUTSIDE"
        cv2.putText(frame, f"L: {left_mode}", (10, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 0), 1)
