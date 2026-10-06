"""
Arctos 6-Axis Robotic Arm Control - Main Entry Point

Launch the control application.
"""

import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    """Launch the application."""
    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("Arctos Control")
    app.setOrganizationName("Arctos Robotics")

    # Create and show main window
    window = MainWindow()
    window.show()

    # Run application event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
