"""
Main Window for Arctos 6-Axis Control

GUI with button controls for each axis and gripper.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QSpinBox,
    QGroupBox, QMessageBox, QRadioButton, QDialog, QProgressBar,
    QApplication
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.serial_manager import SerialManager
from core.grbl_commands import GRBLCommands
from core.config import Config
from core.joystick_manager import JoystickManager
from core.camera_manager import CameraManager
from ui.joystick_diagram import JoystickDiagramWidget
from ui.camera_preview import CameraPreviewWidget
from ui.camera_diagram import CameraDiagramWidget


class MainWindow(QMainWindow):
    """Main application window for robotic arm control."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Arctos 6-Axis Robotic Arm Control")
        self.setMinimumSize(800, 600)

        # Load configuration
        self.config = Config()

        # Initialize serial manager
        self.serial = SerialManager(
            port=self.config.com_port,
            baud_rate=self.config.baud_rate
        )

        # Connect serial signals
        self.serial.connected.connect(self.on_connected)
        self.serial.disconnected.connect(self.on_disconnected)
        self.serial.response_received.connect(self.on_response)
        self.serial.error_occurred.connect(self.on_error)

        # Current control values
        self.current_feedrate = self.config.default_feedrate

        # Gripper position tracking (0-100 percentage scale)
        # 0 = fully closed, 100 = fully open
        # Start at mid-position (50%)
        self.current_gripper_position = 50.0
        self.gripper_step = self.config.gripper_step  # From config, percentage points per step
        self.gripper_timer = QTimer()
        self.gripper_timer.timeout.connect(self.gripper_continue_move)
        self.gripper_timer.setSingleShot(False)  # Repeating timer
        self.gripper_direction = 0  # 0 = stopped, 1 = opening, -1 = closing

        # Status update timer (for position display)
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.request_status)

        # Control mode state
        self.current_control_mode = "manual"  # "manual" or "joystick"

        # Joystick state tracking (per-axis ON/OFF)
        self.joystick_axes_active = {}  # axis -> bool, tracks which axes are currently active
        self.prev_joystick_state = {}   # axis -> direction, previous poll direction

        # Joystick gripper control (counter-based, NO QTimer - prevents Windows handle leaks)
        self.joystick_gripper_counter = 0
        self.joystick_gripper_direction = 0  # 0=stopped, 1=opening, -1=closing

        # Initialize joystick manager (increased deadzone to prevent drift)
        self.joystick = JoystickManager(poll_rate_hz=50, deadzone=0.2)
        self.joystick.joystick_connected.connect(self.on_joystick_connected)
        self.joystick.joystick_disconnected.connect(self.on_joystick_disconnected)
        self.joystick.joystick_update.connect(self.on_joystick_update)
        self.joystick.error_occurred.connect(self.on_joystick_error)
        self.joystick.start()

        # Initialize camera manager (not started until camera mode selected)
        self.camera = CameraManager()
        self.camera.camera_connected.connect(self.on_camera_connected)
        self.camera.camera_disconnected.connect(self.on_camera_disconnected)
        self.camera.camera_update.connect(self.on_joystick_update)  # Reuse same handler
        self.camera.error_occurred.connect(self.on_camera_error)

        # Build UI
        self.init_ui()

        # Auto-connect if configured
        if self.config.auto_connect:
            self.connect_serial()

    def init_ui(self):
        """Build the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # === Top: Connection Controls ===
        connection_layout = QHBoxLayout()

        self.port_combo = QComboBox()
        self.port_combo.addItems(SerialManager.list_ports())
        connection_layout.addWidget(QLabel("COM Port:"))
        connection_layout.addWidget(self.port_combo)

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.clicked.connect(self.connect_serial)
        connection_layout.addWidget(self.btn_connect)

        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.clicked.connect(self.disconnect_serial)
        self.btn_disconnect.setEnabled(False)
        connection_layout.addWidget(self.btn_disconnect)

        connection_layout.addStretch()

        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("font-weight: bold; color: red;")
        connection_layout.addWidget(self.status_label)

        main_layout.addLayout(connection_layout)

        # === Control Mode Selection ===
        mode_layout = QHBoxLayout()

        mode_label = QLabel("Control Mode:")
        mode_label.setStyleSheet("font-weight: bold;")
        mode_layout.addWidget(mode_label)

        self.radio_manual = QRadioButton("Manual Button Control")
        self.radio_manual.setChecked(True)  # Default to manual mode
        self.radio_manual.setEnabled(False)  # Disabled until robot connects
        self.radio_manual.toggled.connect(lambda checked: self.switch_control_mode("manual") if checked else None)
        mode_layout.addWidget(self.radio_manual)

        self.radio_joystick = QRadioButton("Joystick Control")
        self.radio_joystick.setEnabled(False)  # Disabled until robot connects
        self.radio_joystick.toggled.connect(lambda checked: self.switch_control_mode("joystick") if checked else None)
        mode_layout.addWidget(self.radio_joystick)

        self.radio_camera = QRadioButton("Camera Gesture Control")
        self.radio_camera.setEnabled(False)  # Disabled until robot connects
        self.radio_camera.toggled.connect(lambda checked: self.switch_control_mode("camera") if checked else None)
        mode_layout.addWidget(self.radio_camera)

        mode_layout.addSpacing(20)

        # Joystick status indicator
        joystick_status_label = QLabel("Joystick:")
        mode_layout.addWidget(joystick_status_label)

        self.joystick_status = QLabel("Searching...")
        self.joystick_status.setStyleSheet("font-weight: bold; color: orange;")
        mode_layout.addWidget(self.joystick_status)

        mode_layout.addSpacing(10)

        # Camera status indicator
        camera_status_label = QLabel("Camera:")
        mode_layout.addWidget(camera_status_label)

        self.camera_status = QLabel("Off")
        self.camera_status.setStyleSheet("font-weight: bold; color: gray;")
        mode_layout.addWidget(self.camera_status)

        mode_layout.addStretch()

        main_layout.addLayout(mode_layout)

        # === Joystick Mapping Diagram (visible only in joystick mode) ===
        self.joystick_diagram = JoystickDiagramWidget()
        self.joystick_diagram.setVisible(False)
        main_layout.addWidget(self.joystick_diagram)

        # === Camera Gesture Widgets (visible only in camera mode) ===
        self.camera_diagram = CameraDiagramWidget()
        self.camera_diagram.setVisible(False)
        main_layout.addWidget(self.camera_diagram)

        self.camera_preview = CameraPreviewWidget()
        self.camera_preview.setVisible(False)
        main_layout.addWidget(self.camera_preview, 1)  # stretch=1 to fill available space

        # "Go Live" button for camera mode (exits dry-run)
        self.btn_go_live = QPushButton("Go Live — Start Sending Commands")
        self.btn_go_live.setMinimumHeight(40)
        self.btn_go_live.setStyleSheet(
            "QPushButton { background-color: #2a7a2a; color: white; font-weight: bold; font-size: 13px; }"
            "QPushButton:hover { background-color: #3a9a3a; }"
        )
        self.btn_go_live.setVisible(False)
        self.btn_go_live.clicked.connect(self._go_live)
        main_layout.addWidget(self.btn_go_live)

        # === Control Parameters ===
        params_layout = QHBoxLayout()

        # Feedrate Spinbox (jog distance removed - continuous motion controlled by hold time)
        params_layout.addWidget(QLabel("Movement Speed:"))
        self.feedrate_spin = QSpinBox()
        self.feedrate_spin.setRange(10, 3000)
        self.feedrate_spin.setSingleStep(10)
        self.feedrate_spin.setValue(self.config.default_feedrate)
        self.feedrate_spin.setSuffix(" mm/min")
        self.feedrate_spin.valueChanged.connect(self.update_feedrate)
        params_layout.addWidget(self.feedrate_spin)

        params_layout.addSpacing(20)

        info_label = QLabel("Hold button to move continuously, release to stop")
        info_label.setStyleSheet("color: gray; font-style: italic;")
        params_layout.addWidget(info_label)

        params_layout.addStretch()

        main_layout.addLayout(params_layout)

        # === Axis Control Buttons ===
        control_layout = QHBoxLayout()

        # Left side: Axis buttons
        self.axes_group = QGroupBox("Axis Control")
        axes_layout = QGridLayout()

        # Define axes in order: X, Y, Z, A, B, C
        # Note: Z and B have reversed direction (see jog_start method)
        axes = [
            ('X', 0), ('Y', 1), ('Z', 2),
            ('A', 3), ('B', 4), ('C', 5)
        ]

        self.axis_buttons = {}

        for axis, row in axes:
            # Axis label
            label = QLabel(f"{axis}-Axis:")
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            axes_layout.addWidget(label, row, 0)

            # Positive button
            btn_pos = QPushButton(f"{axis}+")
            btn_pos.setMinimumWidth(80)
            btn_pos.pressed.connect(lambda a=axis, d=1: self.jog_start(a, d))
            btn_pos.released.connect(self.jog_stop)
            axes_layout.addWidget(btn_pos, row, 1)

            # Negative button
            btn_neg = QPushButton(f"{axis}-")
            btn_neg.setMinimumWidth(80)
            btn_neg.pressed.connect(lambda a=axis, d=-1: self.jog_start(a, d))
            btn_neg.released.connect(self.jog_stop)
            axes_layout.addWidget(btn_neg, row, 2)

            self.axis_buttons[axis] = (btn_pos, btn_neg)

        self.axes_group.setLayout(axes_layout)
        control_layout.addWidget(self.axes_group)

        # Right side: Emergency Stop and Gripper
        right_layout = QVBoxLayout()

        # Emergency Stop
        self.btn_emergency_stop = QPushButton("⚠ EMERGENCY STOP ⚠")
        self.btn_emergency_stop.setMinimumHeight(60)
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.btn_emergency_stop.setFont(font)
        self.btn_emergency_stop.setStyleSheet(
            "QPushButton { background-color: #cc0000; color: white; border: 3px solid #660000; }"
            "QPushButton:hover { background-color: #ff0000; }"
        )
        self.btn_emergency_stop.clicked.connect(self.emergency_stop)
        right_layout.addWidget(self.btn_emergency_stop)

        right_layout.addSpacing(20)

        # Gripper Control
        self.gripper_group = QGroupBox("Gripper Control")
        gripper_layout = QVBoxLayout()

        self.btn_gripper_open = QPushButton("Open Gripper")
        self.btn_gripper_open.setMinimumHeight(50)
        self.btn_gripper_open.pressed.connect(self.gripper_open_start)
        self.btn_gripper_open.released.connect(self.gripper_stop)
        gripper_layout.addWidget(self.btn_gripper_open)

        self.btn_gripper_close = QPushButton("Close Gripper")
        self.btn_gripper_close.setMinimumHeight(50)
        self.btn_gripper_close.pressed.connect(self.gripper_close_start)
        self.btn_gripper_close.released.connect(self.gripper_stop)
        gripper_layout.addWidget(self.btn_gripper_close)

        # Gripper position display (0-100 percentage)
        self.gripper_position_label = QLabel("Position: 50%")
        self.gripper_position_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gripper_layout.addWidget(self.gripper_position_label)

        # Reset gripper position button
        self.btn_gripper_reset = QPushButton("Reset Position")
        self.btn_gripper_reset.clicked.connect(self.gripper_reset_position)
        gripper_layout.addWidget(self.btn_gripper_reset)

        self.gripper_group.setLayout(gripper_layout)
        right_layout.addWidget(self.gripper_group)

        right_layout.addStretch()

        control_layout.addLayout(right_layout)

        main_layout.addLayout(control_layout)

        # === Position Display ===
        position_group = QGroupBox("Current Position")
        position_layout = QHBoxLayout()

        self.position_labels = {}
        for axis in ['X', 'Y', 'Z', 'A', 'B', 'C']:
            label = QLabel(f"{axis}: 0.0")
            label.setMinimumWidth(80)
            position_layout.addWidget(label)
            self.position_labels[axis] = label

        position_group.setLayout(position_layout)
        main_layout.addWidget(position_group)

        # === Status Messages ===
        self.message_label = QLabel("Ready")
        self.message_label.setWordWrap(True)
        main_layout.addWidget(self.message_label)

        # Disable controls until connected
        self.set_controls_enabled(False)

    def set_controls_enabled(self, enabled: bool):
        """Enable/disable all control buttons."""
        for btn_pos, btn_neg in self.axis_buttons.values():
            btn_pos.setEnabled(enabled)
            btn_neg.setEnabled(enabled)

        self.btn_gripper_open.setEnabled(enabled)
        self.btn_gripper_close.setEnabled(enabled)
        self.btn_gripper_reset.setEnabled(enabled)
        self.btn_emergency_stop.setEnabled(enabled)
        self.feedrate_spin.setEnabled(enabled)

    # === Serial Connection ===

    def connect_serial(self):
        """Connect to Arduino via serial."""
        selected_port = self.port_combo.currentText()
        if not selected_port:
            QMessageBox.warning(self, "No Port", "Please select a COM port")
            return

        self.serial.port = selected_port
        self.config.com_port = selected_port  # Save for next time
        self.config.save()

        self.message_label.setText(f"Connecting to {selected_port}...")
        self.serial.connect()

    def disconnect_serial(self):
        """Disconnect from Arduino."""
        self.serial.disconnect()

    def on_connected(self, success: bool):
        """Handle connection result."""
        if success:
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("font-weight: bold; color: green;")
            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)
            self.set_controls_enabled(True)

            # Enable manual control mode (always available when robot connected)
            self.radio_manual.setEnabled(True)

            # Enable joystick control mode ONLY if joystick is also connected
            if self.joystick.is_connected():
                self.radio_joystick.setEnabled(True)
            else:
                self.radio_joystick.setEnabled(False)

            # Camera mode always available when connected (uses laptop webcam)
            self.radio_camera.setEnabled(True)

            self.message_label.setText("Connected to GRBL. Ready to jog.")

            # Unlock GRBL (clears any alarm state)
            self.serial.send_command(GRBLCommands.unlock())

            # Start status updates if configured
            if self.config.status_update_rate > 0:
                self.status_timer.start(self.config.status_update_rate)

        else:
            self.status_label.setText("Connection Failed")
            self.status_label.setStyleSheet("font-weight: bold; color: red;")
            self.message_label.setText("Connection failed. Check port and try again.")

    def on_disconnected(self):
        """Handle disconnection."""
        self.status_label.setText("Disconnected")
        self.status_label.setStyleSheet("font-weight: bold; color: red;")
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self.set_controls_enabled(False)

        # Disable control mode selection when robot disconnected
        self.radio_manual.setEnabled(False)
        self.radio_joystick.setEnabled(False)
        self.radio_camera.setEnabled(False)

        # Stop camera if running
        if self.camera.is_connected():
            self.camera.stop()

        # Reset to manual mode on disconnect
        self.radio_manual.setChecked(True)

        self.message_label.setText("Disconnected from GRBL.")
        self.status_timer.stop()

    def on_response(self, line: str):
        """Handle response from GRBL."""
        # Parse different response types
        if line.startswith('<'):
            # Status report: <Idle|MPos:x,y,z,a,b,c|...>
            self.parse_status(line)

        elif line == 'ok':
            # Command acknowledged
            pass

        elif line.startswith('error:'):
            # GRBL error
            self.message_label.setText(f"GRBL Error: {line}")

        elif line.startswith('ALARM:'):
            # GRBL alarm
            self.message_label.setText(f"⚠ ALARM: {line}")
            QMessageBox.warning(self, "GRBL Alarm", f"{line}\n\nReset may be required.")

        elif line.startswith('Grbl'):
            # GRBL startup message
            self.message_label.setText(f"GRBL Ready: {line}")

    def on_error(self, error_msg: str):
        """Handle serial errors."""
        self.message_label.setText(f"Error: {error_msg}")

    def parse_status(self, status: str):
        """Parse GRBL status report and update position display."""
        try:
            # Example: <Idle|MPos:0.000,0.000,0.000,0.000,0.000,0.000|FS:0,0>
            if 'MPos:' in status:
                pos_str = status.split('MPos:')[1].split('|')[0]
                positions = pos_str.split(',')

                axes = ['X', 'Y', 'Z', 'A', 'B', 'C']
                for i, axis in enumerate(axes):
                    if i < len(positions):
                        value = float(positions[i])
                        self.position_labels[axis].setText(f"{axis}: {value:.1f}")

        except Exception:
            pass  # Ignore parse errors

    def request_status(self):
        """Request status report from GRBL (called by timer)."""
        if self.serial.is_connected():
            self.serial.send_command(GRBLCommands.status_query())

    # === Control Parameter Updates ===

    def update_feedrate(self, value: int):
        """Update feedrate (movement speed) when spinbox changes."""
        self.current_feedrate = value
        self.message_label.setText(f"Movement speed updated: {value} mm/min")

    # === Jogging Control ===

    def jog_start(self, axis: str, direction: int):
        """
        Start jogging axis continuously.

        Args:
            axis: Axis letter ('X', 'Y', 'Z', 'A', 'B', 'C')
            direction: +1 for positive, -1 for negative
        """
        if not self.serial.is_connected():
            return

        # Swap B and C functionality (button labeled B controls C motor, and vice versa)
        actual_axis = axis
        if axis == 'B':
            actual_axis = 'C'
        elif axis == 'C':
            actual_axis = 'B'

        # Reverse direction for Z, B, and C axes (user request)
        if actual_axis in ['Z', 'B', 'C']:
            direction = -direction

        # Apply axis-specific speed multiplier from config
        multiplier = self.config.axis_speed_multipliers.get(actual_axis, 1.0)
        adjusted_feedrate = int(self.current_feedrate * multiplier)

        # Use large distance (1000mm) for continuous motion
        # Motion stops when button is released (jog_cancel sent)
        distance = 1000.0 * direction
        command = GRBLCommands.jog(actual_axis, distance, adjusted_feedrate)
        self.serial.send_command(command)
        self.message_label.setText(f"Jogging {axis}{'+'if direction > 0 else '-'} @ {adjusted_feedrate} mm/min")

    def jog_stop(self):
        """Stop current jog motion."""
        if self.serial.is_connected():
            self.serial.send_command(GRBLCommands.jog_cancel())
            self.message_label.setText("Jog stopped")

    # === Gripper Control (Incremental) ===

    def _gripper_percentage_to_pulse(self, percentage: float) -> int:
        """
        Convert gripper position percentage (0-100) to servo pulse value.

        Args:
            percentage: 0 = fully closed, 100 = fully open

        Returns:
            Pulse value for M97 command
        """
        min_pulse = self.config.gripper_close_pulse  # 20
        max_pulse = self.config.gripper_open_pulse    # 120
        pulse_value = min_pulse + (percentage / 100.0) * (max_pulse - min_pulse)
        return int(pulse_value)

    def _start_gripper_timer(self):
        """Start gripper timer for manual mode."""
        if self.gripper_timer.isActive():
            self.gripper_timer.stop()
        self.gripper_timer.start(100)

    def _stop_gripper_timer(self):
        """Stop gripper timer."""
        self.gripper_timer.stop()

    def gripper_open_start(self):
        """Start opening gripper incrementally."""
        if not self.serial.is_connected():
            return

        self.gripper_direction = 1  # Opening
        if not self.gripper_timer.isActive():
            self._start_gripper_timer()
        self.message_label.setText("Opening gripper...")

    def gripper_close_start(self):
        """Start closing gripper incrementally."""
        if not self.serial.is_connected():
            return

        self.gripper_direction = -1  # Closing
        if not self.gripper_timer.isActive():
            self._start_gripper_timer()
        self.message_label.setText("Closing gripper...")

    def gripper_stop(self):
        """Stop gripper motion."""
        self._stop_gripper_timer()
        self.gripper_direction = 0
        self.message_label.setText(f"Gripper stopped at position {int(self.current_gripper_position)}%")

    def gripper_reset_position(self):
        """Reset gripper position tracking to match current physical state."""
        if not self.serial.is_connected():
            return

        # Ask user for current gripper state
        from PyQt6.QtWidgets import QInputDialog

        current_pos, ok = QInputDialog.getInt(
            self,
            "Reset Gripper Position",
            "Enter current gripper position (0=closed, 100=open):",
            value=int(self.current_gripper_position),
            min=0,
            max=100,
            step=5
        )

        if ok:
            self.current_gripper_position = float(current_pos)
            self.gripper_position_label.setText(f"Position: {current_pos}%")
            self.message_label.setText(f"Gripper position reset to {current_pos}%")

            # Convert percentage to pulse value and send M97 command
            pulse_value = self._gripper_percentage_to_pulse(current_pos)
            command = GRBLCommands.gripper_move(pulse_value, 0.2)
            self.serial.send_command(command)

    def gripper_continue_move(self):
        """Continue gripper movement (called by timer)."""
        if not self.serial.is_connected() or self.gripper_direction == 0:
            self._stop_gripper_timer()
            return

        # Update position (percentage scale, no limits - user controls manually)
        self.current_gripper_position += self.gripper_step * self.gripper_direction

        # Convert percentage to pulse value for M97 command
        pulse_value = self._gripper_percentage_to_pulse(self.current_gripper_position)
        command = GRBLCommands.gripper_move(
            pulse_value,
            0.1  # Short duration for incremental steps
        )
        self.serial.send_command(command)

        # Update display
        self.gripper_position_label.setText(f"Position: {int(self.current_gripper_position)}%")

    # === Emergency Stop ===

    def emergency_stop(self):
        """Emergency stop: feed hold + jog cancel."""
        if not self.serial.is_connected():
            return

        # Send feed hold
        self.serial.send_command(GRBLCommands.feed_hold())

        # Send jog cancel after brief delay
        QTimer.singleShot(50, lambda: self.serial.send_command(GRBLCommands.jog_cancel()))

        self.message_label.setText("⚠ EMERGENCY STOP ACTIVATED ⚠")

        # Show message box
        QMessageBox.warning(
            self,
            "Emergency Stop",
            "All motion has been halted.\n\nPress 'Cycle Start/Resume' or reconnect to continue."
        )

    def closeEvent(self, event):
        """Handle window close event."""
        # Stop all timers first to prevent Windows handle leaks
        self.status_timer.stop()
        self.gripper_timer.stop()

        # Stop input threads
        self.joystick.stop()
        self.camera.stop()
        self.camera.wait(2000)

        # Stop motion and disconnect serial
        if self.serial.is_connected():
            self.serial.send_command(GRBLCommands.jog_cancel())
            self.serial.disconnect()

        event.accept()

    # === Joystick Control Mode ===

    def switch_control_mode(self, mode: str):
        """
        Switch between manual, joystick, and camera control modes.

        Args:
            mode: "manual", "joystick", or "camera"
        """
        prev_mode = self.current_control_mode
        self.current_control_mode = mode

        # Stop camera when leaving camera mode
        if prev_mode == "camera" and mode != "camera":
            if self.camera.is_connected():
                self.camera.stop()
                self.camera.wait(3000)  # Wait up to 3s for thread to release camera
            self.camera_preview.clear()

        # Hide all mode-specific widgets first
        self.joystick_diagram.setVisible(False)
        self.camera_diagram.setVisible(False)
        self.camera_preview.setVisible(False)
        self.btn_go_live.setVisible(False)

        if mode == "manual":
            # Show axis and gripper controls
            self.axes_group.setVisible(True)
            self.gripper_group.setVisible(True)

            # Enable manual axis buttons
            for btn_pos, btn_neg in self.axis_buttons.values():
                btn_pos.setEnabled(self.serial.is_connected())
                btn_neg.setEnabled(self.serial.is_connected())

            # Enable gripper buttons
            self.btn_gripper_open.setEnabled(self.serial.is_connected())
            self.btn_gripper_close.setEnabled(self.serial.is_connected())
            self.btn_gripper_reset.setEnabled(self.serial.is_connected())

            self.message_label.setText("Switched to Manual Button Control")

        elif mode == "joystick":
            # Hide axis and gripper controls (joystick handles everything)
            self.axes_group.setVisible(False)
            self.gripper_group.setVisible(False)

            self.joystick_diagram.setVisible(True)

            if self.joystick.is_connected():
                self.message_label.setText("Switched to Joystick Control")
            else:
                self.message_label.setText("Joystick Control selected, but no joystick connected")

        elif mode == "camera":
            # Hide axis and gripper controls (camera handles everything)
            self.axes_group.setVisible(False)
            self.gripper_group.setVisible(False)

            # Show camera preview only (diagram hidden to maximize camera size)
            self.camera_preview.setVisible(True)

            # Start camera if not already running
            if not self.camera.is_connected():
                # Create fresh camera manager (thread can only be started once)
                self.camera = CameraManager()
                self.camera.camera_connected.connect(self.on_camera_connected)
                self.camera.camera_disconnected.connect(self.on_camera_disconnected)
                self.camera.camera_update.connect(self.on_joystick_update)
                self.camera.error_occurred.connect(self.on_camera_error)
                self.camera.frame_ready.connect(self.camera_preview.update_frame)
                self.camera.start()
                self.message_label.setText("Starting camera...")
                # Launch calibration after camera connects
                QTimer.singleShot(2000, self._run_camera_calibration)
            else:
                self.message_label.setText("Switched to Camera Gesture Control")

    def on_joystick_connected(self, name: str):
        """Handle joystick connection."""
        self.joystick_status.setText(f"✓ Connected: {name}")
        self.joystick_status.setStyleSheet("font-weight: bold; color: green;")
        self.message_label.setText(f"Joystick connected: {name}")

        # Enable joystick radio button only if robot is also connected
        if self.serial.is_connected():
            self.radio_joystick.setEnabled(True)

    def on_joystick_disconnected(self):
        """Handle joystick disconnection - SAFETY CRITICAL."""
        self.joystick_status.setText("✗ Disconnected")
        self.joystick_status.setStyleSheet("font-weight: bold; color: red;")
        self.message_label.setText("Joystick disconnected")

        # SAFETY: If in joystick mode, stop all motion immediately
        if self.current_control_mode == "joystick":
            # Send jog cancel to stop any queued motion
            if self.serial.is_connected():
                self.serial.send_command(GRBLCommands.jog_cancel())

            # Force switch back to manual control mode
            self.radio_manual.setChecked(True)

            # Warn user
            QMessageBox.warning(
                self,
                "Joystick Disconnected",
                "Joystick disconnected! All motion stopped.\n\n"
                "Switched to Manual Button Control for safety."
            )

        # Disable joystick radio button (can't use joystick mode without joystick)
        self.radio_joystick.setEnabled(False)

    def on_joystick_update(self, state: dict):
        """
        Process joystick input and send single-axis jog commands.

        Mapping (Genesis Mangan 300 Mode 2):
        - Left Stick X/Y -> X/Y axes (Y inverted)
        - Right Stick X/Y -> A/Z axes (Z NOT inverted)
        - D-pad Left/Right -> B axis (exclusive: only one direction)
        - D-pad Up/Down -> C axis (exclusive, INVERTED)
        - A button (index 1) -> Gripper close
        - Y button (index 3) -> Gripper open
        """
        if self.current_control_mode not in ("joystick", "camera") or not self.serial.is_connected():
            return

        # In camera dry-run mode, don't send any GRBL commands
        if self.current_control_mode == "camera" and self.camera.dry_run:
            return

        THRESHOLD = 0.5  # 50% deflection required to activate
        JOG_DISTANCE = 1000.0  # Large distance - motion stopped by jog_cancel on release

        # === Analog Sticks -> Axes ===
        stick_mappings = []

        # Left Stick X -> X axis
        if len(state['axes']) > 0:
            val = state['axes'][0]
            if abs(val) > THRESHOLD:
                stick_mappings.append(('X', 1 if val > 0 else -1))
            else:
                stick_mappings.append(('X', 0))

        # Left Stick Y -> Y axis
        if len(state['axes']) > 1:
            val = state['axes'][1]
            if abs(val) > THRESHOLD:
                if self.current_control_mode == "camera":
                    # Camera: direct mapping (hand up = Y+)
                    stick_mappings.append(('Y', 1 if val > 0 else -1))
                else:
                    # Joystick: Y axis inverted (stick forward = negative)
                    stick_mappings.append(('Y', -1 if val > 0 else 1))
            else:
                stick_mappings.append(('Y', 0))

        # Right Stick X -> A axis
        if len(state['axes']) > 2:
            val = state['axes'][2]
            if abs(val) > THRESHOLD:
                stick_mappings.append(('A', 1 if val > 0 else -1))
            else:
                stick_mappings.append(('A', 0))

        # Right Stick Y -> Z axis (NOT inverted)
        if len(state['axes']) > 3:
            val = state['axes'][3]
            if abs(val) > THRESHOLD:
                stick_mappings.append(('Z', 1 if val > 0 else -1))
            else:
                stick_mappings.append(('Z', 0))

        # D-pad -> B and C axes (exclusive: only one D-pad direction at a time)
        if len(state['hats']) > 0:
            hat_x, hat_y = state['hats'][0]
            # D-pad exclusive: horizontal takes priority over vertical
            if hat_x != 0:
                stick_mappings.append(('B', hat_x))
                stick_mappings.append(('C', 0))
            elif hat_y != 0:
                stick_mappings.append(('B', 0))
                if self.current_control_mode == "camera":
                    stick_mappings.append(('C', hat_y))  # Camera: direct
                else:
                    stick_mappings.append(('C', -hat_y))  # Joystick: inverted
            else:
                stick_mappings.append(('B', 0))
                stick_mappings.append(('C', 0))

        # === Process each axis: send jog on activate, cancel on release ===
        for axis, direction in stick_mappings:
            was_active = self.joystick_axes_active.get(axis, False)
            prev_dir = self.prev_joystick_state.get(axis, 0)
            is_active = direction != 0

            if is_active and (not was_active or direction != prev_dir):
                # Axis just activated or changed direction -> send jog cancel then new jog
                self.serial.send_command(GRBLCommands.jog_cancel())
                multiplier = self.config.axis_speed_multipliers.get(axis, 1.0)
                feedrate = int(self.feedrate_spin.value() * multiplier)
                distance = JOG_DISTANCE * direction
                self.serial.send_command(GRBLCommands.jog(axis, distance, feedrate))
                self.joystick_axes_active[axis] = True
                self.prev_joystick_state[axis] = direction

            elif is_active and was_active:
                # Axis still held in same direction -> do nothing, motion continues
                pass

            elif not is_active and was_active:
                # Axis just released -> cancel jog
                self.serial.send_command(GRBLCommands.jog_cancel())
                self.joystick_axes_active[axis] = False
                self.prev_joystick_state[axis] = 0

        # === Gripper control (counter-based, NO QTimer) ===
        # Button A (index 1) -> close, Button Y (index 3) -> open
        # Exclusive: both pressed = stop
        GRIPPER_POLL_INTERVAL = 5  # Every 5 polls = 100ms at 50Hz

        if len(state['buttons']) > 3:
            a_pressed = state['buttons'][1] == 1
            y_pressed = state['buttons'][3] == 1

            if a_pressed and y_pressed:
                desired = 0
            elif a_pressed:
                desired = -1
            elif y_pressed:
                desired = 1
            else:
                desired = 0

            if desired != self.joystick_gripper_direction:
                self.joystick_gripper_direction = desired
                self.joystick_gripper_counter = 0
                if desired != 0:
                    self._joystick_gripper_step(desired)
            elif desired != 0:
                self.joystick_gripper_counter += 1
                if self.joystick_gripper_counter >= GRIPPER_POLL_INTERVAL:
                    self.joystick_gripper_counter = 0
                    self._joystick_gripper_step(desired)

    def _joystick_gripper_step(self, direction: int):
        """
        Send one gripper step command from joystick control.
        Reuses the same gripper position tracking as manual mode.

        Args:
            direction: 1 for open, -1 for close
        """
        if not self.serial.is_connected():
            return

        self.current_gripper_position += self.gripper_step * direction
        pulse_value = self._gripper_percentage_to_pulse(self.current_gripper_position)
        command = GRBLCommands.gripper_move(pulse_value, 0.1)
        self.serial.send_command(command)
        self.gripper_position_label.setText(f"Position: {int(self.current_gripper_position)}%")

    def on_joystick_error(self, error_msg: str):
        """Handle joystick errors."""
        self.message_label.setText(f"Joystick Error: {error_msg}")

    # === Camera Gesture Control ===

    def _run_camera_calibration(self):
        """Run calibration procedure after camera has started."""
        if not self.camera.is_connected():
            self.message_label.setText("Camera failed to start")
            self.radio_manual.setChecked(True)
            return

        success = self._show_calibration_dialog()
        if success:
            self.camera.set_calibrated(True)
            self.camera.dry_run = True  # Start in dry-run
            self.btn_go_live.setVisible(True)
            self.message_label.setText("Calibrated! DRY RUN mode — test gestures, then click Go Live")
        else:
            self.camera.stop()
            self.camera.wait(3000)
            self.radio_manual.setChecked(True)
            self.message_label.setText("Calibration cancelled")

    def _show_calibration_dialog(self) -> bool:
        """Show calibration dialog. Returns True if both hands calibrated."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Camera Gesture Calibration")
        dialog.setMinimumWidth(450)
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)

        instruction = QLabel(
            "Calibration captures your neutral wrist position.\n\n"
            "Step 1: Hold RIGHT hand in the green neutral zone\n"
            "        with relaxed wrist and fingers. Stay still.\n\n"
            "Step 2: Hold LEFT hand in the green neutral zone\n"
            "        with relaxed wrist. Stay still.\n\n"
            "Keep your wrist straight and fingers naturally relaxed."
        )
        instruction.setWordWrap(True)
        layout.addWidget(instruction)

        status_label = QLabel("Ready to start")
        status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(status_label)

        progress = QProgressBar()
        progress.setRange(0, 50)
        progress.setValue(0)
        progress.setVisible(False)
        layout.addWidget(progress)

        btn_right = QPushButton("1. Calibrate Right Hand")
        btn_right.setMinimumHeight(35)
        btn_left = QPushButton("2. Calibrate Left Hand")
        btn_left.setMinimumHeight(35)
        btn_left.setEnabled(False)
        btn_done = QPushButton("Done — Enter Dry-Run Mode")
        btn_done.setMinimumHeight(35)
        btn_done.setEnabled(False)
        btn_cancel = QPushButton("Cancel")

        layout.addWidget(btn_right)
        layout.addWidget(btn_left)
        layout.addWidget(btn_done)
        layout.addWidget(btn_cancel)

        calibration_state = {'right_done': False, 'left_done': False}

        def calibrate_hand(hand: str):
            btn_right.setEnabled(False)
            btn_left.setEnabled(False)
            btn_cancel.setEnabled(False)
            progress.setVisible(True)
            progress.setValue(0)

            # Countdown
            for i in range(3, 0, -1):
                status_label.setText(f"Hold {hand.upper()} hand steady in neutral zone... {i}")
                QApplication.processEvents()
                time.sleep(1)

            # Start capture
            status_label.setText(f"Capturing {hand.upper()} hand — DO NOT MOVE")
            self.camera.start_calibration(hand)

            # Collect ~50 samples at ~25fps = 2 seconds
            for i in range(50):
                progress.setValue(i + 1)
                QApplication.processEvents()
                time.sleep(0.04)

            ok = self.camera.finish_calibration()
            progress.setVisible(False)

            if ok:
                status_label.setText(f"{hand.upper()} hand calibrated!")
                if hand == "right":
                    calibration_state['right_done'] = True
                    btn_left.setEnabled(True)
                else:
                    calibration_state['left_done'] = True

                if calibration_state['right_done'] and calibration_state['left_done']:
                    btn_done.setEnabled(True)
                    status_label.setText("Both hands calibrated! Click Done.")
            else:
                status_label.setText(f"Failed — hand not detected. Try again.")
                if hand == "right":
                    btn_right.setEnabled(True)
                else:
                    btn_left.setEnabled(True)

            btn_cancel.setEnabled(True)

        import time
        btn_right.clicked.connect(lambda: calibrate_hand("right"))
        btn_left.clicked.connect(lambda: calibrate_hand("left"))
        btn_done.clicked.connect(dialog.accept)
        btn_cancel.clicked.connect(dialog.reject)

        return dialog.exec() == QDialog.DialogCode.Accepted

    def _go_live(self):
        """Exit dry-run mode and start sending GRBL commands."""
        if hasattr(self, 'camera') and self.camera.is_connected():
            self.camera.dry_run = False
            self.btn_go_live.setVisible(False)
            self.message_label.setText("LIVE — Camera gesture control active!")

    def on_camera_connected(self, info: str):
        """Handle camera connection."""
        self.camera_status.setText(f"Active: {info}")
        self.camera_status.setStyleSheet("font-weight: bold; color: green;")
        self.message_label.setText(f"Camera started: {info}")

    def on_camera_disconnected(self):
        """Handle camera disconnection — SAFETY CRITICAL."""
        self.camera_status.setText("Off")
        self.camera_status.setStyleSheet("font-weight: bold; color: gray;")
        self.camera_preview.clear()

        # SAFETY: If in camera mode, stop all motion and switch to manual
        if self.current_control_mode == "camera":
            if self.serial.is_connected():
                self.serial.send_command(GRBLCommands.jog_cancel())
            self.radio_manual.setChecked(True)
            self.message_label.setText("Camera stopped. Switched to Manual Control.")

    def on_camera_error(self, error_msg: str):
        """Handle camera errors."""
        self.message_label.setText(f"Camera Error: {error_msg}")
        self.camera_status.setText("Error")
        self.camera_status.setStyleSheet("font-weight: bold; color: red;")


def main():
    """Launch main application."""
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
