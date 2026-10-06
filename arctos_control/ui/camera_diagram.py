"""
Camera Gesture Mapping Diagram Widget

Visual reference showing how hand positions and gestures map to robot axes.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont


class CameraDiagramWidget(QWidget):
    """Visual diagram showing hand gesture to axis mapping."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(700, 230)
        self.setMaximumHeight(250)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Colors
        bg_color = QColor(45, 45, 50)
        panel_color = QColor(60, 60, 65)
        panel_border = QColor(85, 85, 90)
        right_color = QColor(70, 130, 210)
        left_color = QColor(210, 160, 60)
        gripper_close = QColor(220, 90, 70)
        gripper_open = QColor(70, 200, 120)
        text_white = QColor(240, 240, 240)
        text_dim = QColor(170, 170, 170)
        highlight = QColor(100, 200, 255)

        # Background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(QRectF(0, 0, w, h), 10, 10)

        # Title
        title_font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QPen(text_white))
        painter.drawText(QRectF(0, 6, w, 22),
                         Qt.AlignmentFlag.AlignHCenter, "Camera Gesture Mapping")

        # Three panels
        panel_y = 34
        panel_h = h - 44
        margin = 10
        panel_w = (w - margin * 4) / 3

        content_font = QFont("Segoe UI", 9)
        small_font = QFont("Segoe UI", 8)
        hint_font = QFont("Segoe UI", 8)

        # --- Right Hand Panel ---
        rx = margin
        self._draw_panel(painter, rx, panel_y, panel_w, panel_h,
                         panel_color, panel_border, "RIGHT HAND", right_color)

        line_y = panel_y + 30

        painter.setFont(small_font)
        painter.setPen(QPen(highlight))
        painter.drawText(QRectF(rx + 8, line_y, panel_w - 16, 14),
                         Qt.AlignmentFlag.AlignLeft, "Outside neutral zone:")
        line_y += 16

        painter.setFont(content_font)
        painter.setPen(QPen(text_white))
        for line in ["Move Left/Right  \u2192  X axis",
                      "Move Up/Down     \u2192  Y axis"]:
            painter.drawText(QRectF(rx + 14, line_y, panel_w - 28, 16),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, line)
            line_y += 17

        line_y += 4
        painter.setFont(small_font)
        painter.setPen(QPen(highlight))
        painter.drawText(QRectF(rx + 8, line_y, panel_w - 16, 14),
                         Qt.AlignmentFlag.AlignLeft, "Inside neutral zone:")
        line_y += 16

        painter.setFont(content_font)
        painter.setPen(QPen(text_white))
        for line in ["Rotate wrist     \u2192  A axis",
                      "Flex wrist up/dn \u2192  B axis"]:
            painter.drawText(QRectF(rx + 14, line_y, panel_w - 28, 16),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, line)
            line_y += 17

        # --- Left Hand Panel ---
        lx = margin * 2 + panel_w
        self._draw_panel(painter, lx, panel_y, panel_w, panel_h,
                         panel_color, panel_border, "LEFT HAND", left_color)

        line_y = panel_y + 30

        painter.setFont(small_font)
        painter.setPen(QPen(highlight))
        painter.drawText(QRectF(lx + 8, line_y, panel_w - 16, 14),
                         Qt.AlignmentFlag.AlignLeft, "Inside neutral zone:")
        line_y += 16

        painter.setFont(content_font)
        painter.setPen(QPen(text_white))
        for line in ["Flex wrist up/dn \u2192  Z axis",
                      "Rotate wrist     \u2192  C axis"]:
            painter.drawText(QRectF(lx + 14, line_y, panel_w - 28, 16),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, line)
            line_y += 17

        line_y += 6
        painter.setFont(hint_font)
        painter.setPen(QPen(text_dim))
        painter.drawText(QRectF(lx + 8, line_y, panel_w - 16, 14),
                         Qt.AlignmentFlag.AlignLeft, "Same as right hand A/B")
        line_y += 14
        painter.drawText(QRectF(lx + 8, line_y, panel_w - 16, 14),
                         Qt.AlignmentFlag.AlignLeft, "Hand must be in green box")

        # --- Gripper Panel ---
        gx = margin * 3 + panel_w * 2
        self._draw_panel(painter, gx, panel_y, panel_w, panel_h,
                         panel_color, panel_border, "GRIPPER", QColor(180, 180, 180))

        painter.setFont(content_font)

        icon_y = panel_y + 38
        # Close
        painter.setPen(QPen(gripper_close, 2))
        painter.setBrush(QBrush(gripper_close.darker(140)))
        painter.drawEllipse(QPointF(gx + 25, icon_y + 4), 8, 8)
        painter.setPen(QPen(text_white))
        painter.drawText(QRectF(gx + 40, icon_y - 5, panel_w - 55, 18),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         "Fingers closed \u2192 Close")

        icon_y += 30
        # Open
        painter.setPen(QPen(gripper_open, 2))
        painter.setBrush(QBrush(gripper_open.darker(140)))
        painter.drawEllipse(QPointF(gx + 25, icon_y + 4), 8, 8)
        painter.setPen(QPen(text_white))
        painter.drawText(QRectF(gx + 40, icon_y - 5, panel_w - 55, 18),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         "Fingers spread \u2192 Open")

        icon_y += 34
        painter.setFont(hint_font)
        painter.setPen(QPen(text_dim))
        painter.drawText(QRectF(gx + 8, icon_y, panel_w - 16, 14),
                         Qt.AlignmentFlag.AlignLeft, "Right hand, any zone")
        icon_y += 14
        painter.drawText(QRectF(gx + 8, icon_y, panel_w - 16, 14),
                         Qt.AlignmentFlag.AlignLeft, "Calibrated neutral = no action")

        painter.end()

    def _draw_panel(self, painter, x, y, w, h, bg, border, title, title_color):
        """Draw a labeled panel box."""
        painter.setPen(QPen(border, 1.5))
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(QRectF(x, y, w, h), 8, 8)

        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(title_color))
        painter.drawText(QRectF(x, y + 6, w, 18),
                         Qt.AlignmentFlag.AlignHCenter, title)
