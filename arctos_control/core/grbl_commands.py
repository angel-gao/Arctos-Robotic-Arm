"""
GRBL Command Generator for Arctos 6-Axis Robotic Arm

Generates standard GRBL commands for jogging, gripper control, and emergency stop.
"""


class GRBLCommands:
    """Static methods for generating GRBL command strings."""

    @staticmethod
    def jog(axis: str, distance: float, feedrate: int) -> str:
        """
        Generate incremental jog command.

        Args:
            axis: Axis letter ('X', 'Y', 'Z', 'A', 'B', 'C')
            distance: Distance to move (mm or degrees), positive or negative
            feedrate: Speed in mm/min or deg/min

        Returns:
            GRBL jog command string (e.g., "$J=G91 X5.0 F500\n")
        """
        return f"$J=G91 {axis}{distance:.2f} F{feedrate}\n"

    @staticmethod
    def jog_multi(axis_distances: dict, feedrate: int) -> str:
        """
        Generate a single jog command for multiple axes simultaneously.

        Args:
            axis_distances: Dict mapping axis letter to distance.
                           e.g., {'X': 20.0, 'Y': -50.0, 'Z': 10.0}
            feedrate: Speed in mm/min (shared across all axes)

        Returns:
            GRBL jog command string, e.g., "$J=G91 X20.00 Y-50.00 Z10.00 F500\n"
        """
        if not axis_distances:
            return ""
        axes_str = " ".join(f"{axis}{dist:.2f}" for axis, dist in axis_distances.items())
        return f"$J=G91 {axes_str} F{feedrate}\n"

    @staticmethod
    def jog_cancel() -> bytes:
        """
        Real-time jog cancel command (0x85).
        Immediately stops current jog motion and flushes jog queue.

        Returns:
            Single byte 0x85
        """
        return bytes([0x85])

    @staticmethod
    def feed_hold() -> bytes:
        """
        Real-time feed hold command (!).
        Pauses motion, decelerates safely to stop.

        Returns:
            ASCII '!' character
        """
        return b'!'

    @staticmethod
    def cycle_start() -> bytes:
        """
        Real-time cycle start/resume command (~).
        Resumes from feed hold or paused state.

        Returns:
            ASCII '~' character
        """
        return b'~'

    @staticmethod
    def soft_reset() -> bytes:
        """
        Real-time soft reset command (Ctrl-X).
        Emergency halt and reset without power cycle.

        Returns:
            Control character 0x18
        """
        return bytes([0x18])

    @staticmethod
    def status_query() -> str:
        """
        Request real-time status report.

        Returns:
            Status query character '?'
        """
        return "?"

    @staticmethod
    def get_settings() -> str:
        """
        Request all GRBL settings ($$ command).

        Returns:
            Settings query command
        """
        return "$$\n"

    @staticmethod
    def gripper_move(pulse_value: int, duration: float = 0.2) -> str:
        """
        Generate gripper servo control command (M97).

        Args:
            pulse_value: Servo pulse width value (0-499)
                        Typical: 40 = closed, 120 = open
            duration: Time in seconds for movement

        Returns:
            M97 servo command string
        """
        return f"M97 B{pulse_value} T{duration}\n"

    @staticmethod
    def gripper_open(pulse_value: int = 120, duration: float = 0.2) -> str:
        """
        Open gripper command.

        Args:
            pulse_value: Servo position for open (default 120)
            duration: Movement duration in seconds

        Returns:
            M97 command to open gripper
        """
        return GRBLCommands.gripper_move(pulse_value, duration)

    @staticmethod
    def gripper_close(pulse_value: int = 40, duration: float = 0.2) -> str:
        """
        Close gripper command.

        Args:
            pulse_value: Servo position for closed (default 40)
            duration: Movement duration in seconds

        Returns:
            M97 command to close gripper
        """
        return GRBLCommands.gripper_move(pulse_value, duration)

    @staticmethod
    def unlock() -> str:
        """
        Unlock GRBL after alarm ($X command).

        Returns:
            Unlock command
        """
        return "$X\n"
