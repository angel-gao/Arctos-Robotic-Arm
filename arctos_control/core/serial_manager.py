"""
Serial Communication Manager for GRBL

Threaded serial I/O to prevent UI freezing.
"""

from PyQt6.QtCore import QThread, pyqtSignal
import serial
import serial.tools.list_ports
import time
from typing import Optional, List


class SerialManager(QThread):
    """
    Background thread for serial communication with Arduino/GRBL.

    Signals:
        connected: Emitted when connection established (bool: success)
        disconnected: Emitted when connection lost
        response_received: Emitted when data received from GRBL (str: line)
        error_occurred: Emitted on errors (str: error message)
    """

    connected = pyqtSignal(bool)
    disconnected = pyqtSignal()
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, port: str = "COM3", baud_rate: int = 115200):
        """
        Initialize serial manager.

        Args:
            port: COM port name (e.g., "COM3", "/dev/ttyUSB0")
            baud_rate: Baud rate (must match GRBL: 115200)
        """
        super().__init__()
        self.port = port
        self.baud_rate = baud_rate
        self.serial_port: Optional[serial.Serial] = None
        self.running = False
        self._write_lock = False  # Simple lock for write operations

    def connect(self) -> bool:
        """
        Open serial connection to Arduino and verify GRBL responds.

        Returns:
            True if connection successful and GRBL responds, False otherwise
        """
        try:
            # Close existing connection if any
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()

            # Open new connection
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=0.5,  # 500ms read timeout for verification
                write_timeout=1.0
            )

            # Wait for Arduino reset (DTR toggling causes reset)
            time.sleep(2.0)

            # Try to read GRBL startup message (should get "Grbl x.x [...]")
            grbl_detected = False
            start_time = time.time()
            timeout = 3.0  # 3 second timeout for GRBL response

            while time.time() - start_time < timeout:
                try:
                    if self.serial_port.in_waiting > 0:
                        line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                        if line and 'Grbl' in line:
                            grbl_detected = True
                            break
                except Exception:
                    pass
                time.sleep(0.1)

            # If no GRBL response, try sending status query
            if not grbl_detected:
                self.serial_port.write(b'?\n')
                time.sleep(0.5)
                if self.serial_port.in_waiting > 0:
                    line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                    if line.startswith('<'):  # GRBL status format: <Idle|...>
                        grbl_detected = True

            # Close connection if GRBL not detected
            if not grbl_detected:
                self.serial_port.close()
                self.error_occurred.emit(f"No GRBL response on {self.port}. Check Arduino connection.")
                self.connected.emit(False)
                return False

            # Flush buffers after verification
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()

            # Start read thread
            self.running = True
            self.start()

            self.connected.emit(True)
            return True

        except Exception as e:
            self.error_occurred.emit(f"Connection failed: {str(e)}")
            self.connected.emit(False)
            return False

    def disconnect(self):
        """Close serial connection."""
        self.running = False

        # Wait for thread to finish (max 1 second)
        if self.isRunning():
            self.wait(1000)

        # Close serial port
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except Exception:
                pass

        self.disconnected.emit()

    def is_connected(self) -> bool:
        """
        Check if serial port is connected.

        Returns:
            True if connected and open, False otherwise
        """
        return self.serial_port is not None and self.serial_port.is_open

    def send_command(self, command: str | bytes):
        """
        Send command to GRBL.

        Args:
            command: String command (will be encoded) or raw bytes
        """
        if not self.is_connected():
            self.error_occurred.emit("Not connected - cannot send command")
            return

        try:
            # Convert string to bytes if needed
            if isinstance(command, str):
                data = command.encode('utf-8')
            else:
                data = command

            # Send to serial port
            self.serial_port.write(data)

        except Exception as e:
            self.error_occurred.emit(f"Send error: {str(e)}")

    def run(self):
        """
        Background thread: continuously read from serial port.
        Runs until self.running is set to False.
        """
        while self.running and self.is_connected():
            try:
                # Check if data available
                if self.serial_port.in_waiting > 0:
                    # Read line (blocks until \n or timeout)
                    line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()

                    if line:
                        # Emit received data to main thread
                        self.response_received.emit(line)

                else:
                    # No data, sleep briefly to avoid busy-wait
                    time.sleep(0.01)

            except Exception as e:
                if self.running:  # Only report error if still supposed to be running
                    self.error_occurred.emit(f"Read error: {str(e)}")
                break

    @staticmethod
    def list_ports() -> List[str]:
        """
        List all available serial ports.

        Returns:
            List of port names (e.g., ["COM3", "COM4"])
        """
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    @staticmethod
    def find_arduino(vendor_id: int = 0x2341) -> Optional[str]:
        """
        Auto-detect Arduino by vendor ID.

        Args:
            vendor_id: USB vendor ID (0x2341 for Arduino, 0x1A86 for CH340 clones)

        Returns:
            Port name if found, None otherwise
        """
        ports = serial.tools.list_ports.comports()

        for port in ports:
            # Check for official Arduino or common clones
            if port.vid == vendor_id or port.vid == 0x1A86:
                return port.device

        return None
