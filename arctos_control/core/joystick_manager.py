"""
Joystick Input Manager for Arctos Control

Threaded joystick polling to prevent UI freezing.
"""

import os
from PyQt6.QtCore import QThread, pyqtSignal
from typing import Optional
import time

# Set environment variables before pygame import
os.environ["SDL_VIDEODRIVER"] = "dummy"  # No video window needed
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"  # Background input

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


class JoystickManager(QThread):
    """
    Background thread for joystick input polling.

    Signals:
        joystick_connected: Emitted when joystick detected (str: joystick name)
        joystick_disconnected: Emitted when joystick unplugged
        joystick_update: Emitted with joystick state (dict: axes, buttons, hats)
        error_occurred: Emitted on errors (str: error message)
    """

    joystick_connected = pyqtSignal(str)
    joystick_disconnected = pyqtSignal()
    joystick_update = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, poll_rate_hz: int = 50, deadzone: float = 0.1):
        """
        Initialize joystick manager.

        Args:
            poll_rate_hz: Polling frequency in Hz (default 50 Hz = 20ms interval)
            deadzone: Minimum axis value to register (0.0 - 1.0)
        """
        super().__init__()
        self.poll_rate_hz = poll_rate_hz
        self.deadzone = deadzone
        self.running = False
        self.joystick: Optional['pygame.joystick.Joystick'] = None
        self.joystick_name: Optional[str] = None
        self._initialized = False

    def initialize_pygame(self) -> bool:
        """
        Initialize pygame joystick system.

        Returns:
            True if successful, False otherwise
        """
        if not PYGAME_AVAILABLE:
            self.error_occurred.emit("pygame library not installed")
            return False

        try:
            pygame.init()
            pygame.joystick.init()
            self._initialized = True
            return True
        except Exception as e:
            self.error_occurred.emit(f"Failed to initialize pygame: {str(e)}")
            return False

    def detect_joystick(self) -> bool:
        """
        Detect and connect to first available joystick.

        Returns:
            True if joystick found and connected, False otherwise
        """
        if not self._initialized:
            return False

        try:
            num_joysticks = pygame.joystick.get_count()

            if num_joysticks == 0:
                return False

            # Connect to first joystick
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            self.joystick_name = self.joystick.get_name()

            # Emit connection signal
            self.joystick_connected.emit(self.joystick_name)
            return True

        except Exception as e:
            self.error_occurred.emit(f"Joystick detection error: {str(e)}")
            return False

    def run(self):
        """
        Background thread main loop: poll joystick and emit state updates.
        """
        # Initialize pygame
        if not self.initialize_pygame():
            return

        # Detect joystick
        joystick_detected = self.detect_joystick()
        if not joystick_detected:
            self.error_occurred.emit("No joystick detected. Please connect a USB controller.")

        self.running = True
        poll_interval_ms = int(1000 / self.poll_rate_hz)

        while self.running:
            try:
                # Update pygame's internal state FIRST (critical for hot-plug detection)
                pygame.event.pump()

                # Now check if joystick connection changed
                num_joysticks = pygame.joystick.get_count()

                if num_joysticks == 0 and self.joystick is not None:
                    # Joystick disconnected
                    self.joystick = None
                    self.joystick_name = None
                    self.joystick_disconnected.emit()

                elif num_joysticks > 0 and self.joystick is None:
                    # Joystick connected (hot-plug detection)
                    if self.detect_joystick():
                        pass  # Signal already emitted in detect_joystick()

                # Poll joystick state if connected
                if self.joystick is not None:
                    try:

                        # Read all axes
                        axes = []
                        for i in range(self.joystick.get_numaxes()):
                            axis_value = self.joystick.get_axis(i)

                            # Apply deadzone
                            if abs(axis_value) < self.deadzone:
                                axis_value = 0.0

                            axes.append(axis_value)

                        # Read all buttons
                        buttons = []
                        for i in range(self.joystick.get_numbuttons()):
                            button_state = self.joystick.get_button(i)
                            buttons.append(button_state)

                        # Read all hats (D-pad)
                        hats = []
                        for i in range(self.joystick.get_numhats()):
                            hat_state = self.joystick.get_hat(i)
                            hats.append(hat_state)

                        # Emit state update
                        state = {
                            'axes': axes,
                            'buttons': buttons,
                            'hats': hats
                        }
                        self.joystick_update.emit(state)

                    except Exception as e:
                        # Error reading joystick data - likely disconnected
                        if self.running:
                            # Verify disconnection by checking count
                            if pygame.joystick.get_count() == 0:
                                # Joystick actually disconnected
                                self.joystick = None
                                self.joystick_name = None
                                self.joystick_disconnected.emit()
                            else:
                                # Transient error, log it
                                self.error_occurred.emit(f"Joystick read error: {str(e)}")

                # Sleep to maintain poll rate
                self.msleep(poll_interval_ms)

            except Exception as e:
                if self.running:  # Only report if still supposed to be running
                    self.error_occurred.emit(f"Joystick poll loop error: {str(e)}")
                    # Don't break - continue polling to detect reconnection
                    time.sleep(1.0)  # Back off on errors

        # Cleanup
        if self.joystick is not None:
            try:
                self.joystick.quit()
            except Exception:
                pass

        if self._initialized:
            try:
                pygame.joystick.quit()
                pygame.quit()
            except Exception:
                pass

    def stop(self):
        """Stop joystick polling thread."""
        self.running = False
        self.wait(1000)  # Wait up to 1 second for thread to finish

    def is_connected(self) -> bool:
        """
        Check if joystick is connected.

        Returns:
            True if joystick connected, False otherwise
        """
        return self.joystick is not None

    def get_joystick_name(self) -> Optional[str]:
        """
        Get name of connected joystick.

        Returns:
            Joystick name string, or None if not connected
        """
        return self.joystick_name

