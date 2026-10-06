"""
Joystick Mapping Diagram Widget

Visual representation of gamepad-to-robot-axis mapping using QPainter.
Shows controller layout with labeled sticks, D-pad, and buttons.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath


class JoystickDiagramWidget(QWidget):
    """Visual diagram showing joystick-to-axis mapping for the controller."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(700, 300)
        self.setMaximumHeight(320)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Colors
        bg_color = QColor(45, 45, 50)
        body_color = QColor(65, 65, 70)
        body_border = QColor(90, 90, 95)
        stick_color = QColor(70, 130, 210)
        stick_inner = QColor(90, 155, 235)
        dpad_color = QColor(80, 180, 80)
        btn_close_color = QColor(220, 90, 70)
        btn_open_color = QColor(70, 170, 220)
        text_white = QColor(240, 240, 240)
        text_dim = QColor(180, 180, 180)
        arrow_color = QColor(255, 255, 255, 200)

        # Background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(QRectF(0, 0, w, h), 12, 12)

        # Controller body - centered, generous size
        body_w = min(w - 60, 620)
        body_h = min(h - 60, 240)
        bx = (w - body_w) / 2
        by = (h - body_h) / 2 + 10  # Slight offset down for title

        painter.setPen(QPen(body_border, 2.5))
        painter.setBrush(QBrush(body_color))
        painter.drawRoundedRect(QRectF(bx, by, body_w, body_h), 28, 28)

        # === Title (above controller body) ===
        title_font = QFont("Segoe UI", 13, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QPen(text_white))
        painter.drawText(QRectF(0, 4, w, 30),
                         Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                         "Controller Mapping")

        # === Left Stick ===
        stick_r = body_h * 0.22
        ls_cx = bx + body_w * 0.20
        ls_cy = by + body_h * 0.42

        self._draw_stick(painter, ls_cx, ls_cy, stick_r, stick_color, stick_inner, arrow_color)

        # Center label inside stick
        font_stick = QFont("Segoe UI", 13, QFont.Weight.Bold)
        painter.setFont(font_stick)
        painter.setPen(QPen(text_white))
        painter.drawText(QRectF(ls_cx - 30, ls_cy - 10, 60, 20),
                         Qt.AlignmentFlag.AlignCenter, "X / Y")

        # "Left Stick" label above
        font_sub = QFont("Segoe UI", 10)
        painter.setFont(font_sub)
        painter.setPen(QPen(stick_color.lighter(140)))
        painter.drawText(QRectF(ls_cx - 50, ls_cy - stick_r - 24, 100, 18),
                         Qt.AlignmentFlag.AlignCenter, "Left Stick")

        # Directional labels outside the circle with good spacing
        font_dir = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font_dir)
        painter.setPen(QPen(text_dim))
        gap = 12
        painter.drawText(QRectF(ls_cx + stick_r + gap, ls_cy - 9, 40, 18),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "X+")
        painter.drawText(QRectF(ls_cx - stick_r - gap - 40, ls_cy - 9, 40, 18),
                         Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "X-")
        painter.drawText(QRectF(ls_cx - 20, ls_cy - stick_r - gap - 16, 40, 18),
                         Qt.AlignmentFlag.AlignCenter, "Y+")
        painter.drawText(QRectF(ls_cx - 20, ls_cy + stick_r + gap, 40, 18),
                         Qt.AlignmentFlag.AlignCenter, "Y-")

        # === Right Stick ===
        rs_cx = bx + body_w * 0.58
        rs_cy = by + body_h * 0.52

        self._draw_stick(painter, rs_cx, rs_cy, stick_r, stick_color, stick_inner, arrow_color)

        painter.setFont(font_stick)
        painter.setPen(QPen(text_white))
        painter.drawText(QRectF(rs_cx - 30, rs_cy - 10, 60, 20),
                         Qt.AlignmentFlag.AlignCenter, "A / Z")

        painter.setFont(font_sub)
        painter.setPen(QPen(stick_color.lighter(140)))
        painter.drawText(QRectF(rs_cx - 50, rs_cy - stick_r - 24, 100, 18),
                         Qt.AlignmentFlag.AlignCenter, "Right Stick")

        painter.setFont(font_dir)
        painter.setPen(QPen(text_dim))
        painter.drawText(QRectF(rs_cx + stick_r + gap, rs_cy - 9, 40, 18),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "A+")
        painter.drawText(QRectF(rs_cx - stick_r - gap - 40, rs_cy - 9, 40, 18),
                         Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "A-")
        painter.drawText(QRectF(rs_cx - 20, rs_cy - stick_r - gap - 16, 40, 18),
                         Qt.AlignmentFlag.AlignCenter, "Z+")
        painter.drawText(QRectF(rs_cx - 20, rs_cy + stick_r + gap, 40, 18),
                         Qt.AlignmentFlag.AlignCenter, "Z-")

        # === D-pad ===
        dp_cx = bx + body_w * 0.20
        dp_cy = by + body_h * 0.80
        dp_size = body_h * 0.09

        self._draw_dpad(painter, dp_cx, dp_cy, dp_size, dpad_color)

        # D-pad label below
        font_dpad = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font_dpad)
        painter.setPen(QPen(dpad_color.lighter(130)))
        painter.drawText(QRectF(dp_cx - 60, dp_cy + dp_size * 1.8, 120, 20),
                         Qt.AlignmentFlag.AlignCenter, "D-pad: B / C")

        # === Buttons (A and Y) ===
        btn_r = body_h * 0.10
        btn_spacing = btn_r * 3.2

        # Y button (Open) - top
        y_cx = bx + body_w * 0.82
        y_cy = by + body_h * 0.32
        self._draw_button(painter, y_cx, y_cy, btn_r, btn_open_color, "Y")

        font_btn_label = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font_btn_label)
        painter.setPen(QPen(btn_open_color.lighter(130)))
        painter.drawText(QRectF(y_cx - 50, y_cy - btn_r - 20, 100, 18),
                         Qt.AlignmentFlag.AlignCenter, "Open Gripper")

        # A button (Close) - bottom
        a_cx = bx + body_w * 0.82
        a_cy = y_cy + btn_spacing
        self._draw_button(painter, a_cx, a_cy, btn_r, btn_close_color, "A")

        painter.setFont(font_btn_label)
        painter.setPen(QPen(btn_close_color.lighter(130)))
        painter.drawText(QRectF(a_cx - 50, a_cy + btn_r + 4, 100, 18),
                         Qt.AlignmentFlag.AlignCenter, "Close Gripper")

        painter.end()

    def _draw_stick(self, painter, cx, cy, r, color, inner_color, arrow_color):
        """Draw an analog stick circle with directional arrows."""
        # Outer ring
        painter.setPen(QPen(color.darker(130), 2.5))
        painter.setBrush(QBrush(color.darker(170)))
        painter.drawEllipse(QPointF(cx, cy), r, r)

        # Inner stick
        painter.setPen(QPen(color.darker(110), 1.5))
        painter.setBrush(QBrush(inner_color.darker(130)))
        painter.drawEllipse(QPointF(cx, cy), r * 0.55, r * 0.55)

        # Direction arrows
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(arrow_color))
        ar = r * 0.13

        self._draw_triangle(painter, cx, cy - r * 0.80, ar, "up")
        self._draw_triangle(painter, cx, cy + r * 0.80, ar, "down")
        self._draw_triangle(painter, cx - r * 0.80, cy, ar, "left")
        self._draw_triangle(painter, cx + r * 0.80, cy, ar, "right")

    def _draw_button(self, painter, cx, cy, r, color, letter):
        """Draw a face button with letter inside."""
        painter.setPen(QPen(color.darker(130), 2.5))
        painter.setBrush(QBrush(color))
        painter.drawEllipse(QPointF(cx, cy), r, r)

        font = QFont("Segoe UI", 14, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.drawText(QRectF(cx - r, cy - r, r * 2, r * 2),
                         Qt.AlignmentFlag.AlignCenter, letter)

    def _draw_triangle(self, painter, cx, cy, size, direction):
        """Draw a small directional triangle."""
        path = QPainterPath()
        if direction == "up":
            path.moveTo(cx, cy - size)
            path.lineTo(cx - size, cy + size * 0.5)
            path.lineTo(cx + size, cy + size * 0.5)
        elif direction == "down":
            path.moveTo(cx, cy + size)
            path.lineTo(cx - size, cy - size * 0.5)
            path.lineTo(cx + size, cy - size * 0.5)
        elif direction == "left":
            path.moveTo(cx - size, cy)
            path.lineTo(cx + size * 0.5, cy - size)
            path.lineTo(cx + size * 0.5, cy + size)
        elif direction == "right":
            path.moveTo(cx + size, cy)
            path.lineTo(cx - size * 0.5, cy - size)
            path.lineTo(cx - size * 0.5, cy + size)
        path.closeSubpath()
        painter.drawPath(path)

    def _draw_dpad(self, painter, cx, cy, size, color):
        """Draw a D-pad cross shape."""
        painter.setPen(QPen(color.darker(130), 2))
        painter.setBrush(QBrush(color.darker(150)))

        # Horizontal bar
        painter.drawRoundedRect(
            QRectF(cx - size * 1.8, cy - size * 0.6, size * 3.6, size * 1.2),
            4, 4
        )
        # Vertical bar
        painter.drawRoundedRect(
            QRectF(cx - size * 0.6, cy - size * 1.8, size * 1.2, size * 3.6),
            4, 4
        )
