"""
Camera Preview Widget for Arctos Control

Displays live webcam feed with hand tracking overlays.
Shows neutral zone, detected landmarks, and active axis indicators.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap


class CameraPreviewWidget(QWidget):
    """Live webcam preview with hand tracking overlay."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 400)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel("Camera not active")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("background-color: #1a1a1a; color: #666; font-size: 14px;")
        self._label.setMinimumSize(400, 400)
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._label)

    def update_frame(self, q_image: QImage):
        """
        Update the preview with a new camera frame.

        Args:
            q_image: QImage from CameraManager.frame_ready signal
        """
        pixmap = QPixmap.fromImage(q_image)
        scaled = pixmap.scaled(
            self._label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self._label.setPixmap(scaled)

    def clear(self):
        """Clear the preview and show placeholder text."""
        self._label.clear()
        self._label.setText("Camera not active")
