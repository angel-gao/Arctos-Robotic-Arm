"""
Configuration Manager for Arctos Control

Loads and saves configuration from/to YAML file.
"""

import yaml
from pathlib import Path
from typing import Any, Dict


class Config:
    """Configuration manager for application settings."""

    def __init__(self, config_file: str = "config.yaml"):
        """
        Initialize configuration manager.

        Args:
            config_file: Path to YAML config file (relative or absolute)
        """
        self.config_file = Path(config_file)
        self.config_data: Dict[str, Any] = {}
        self.load()

    def load(self):
        """Load configuration from YAML file, create with defaults if missing."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    self.config_data = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")
                self.config_data = self._defaults()
        else:
            # Create default config if file doesn't exist
            self.config_data = self._defaults()
            self.save()

    def save(self):
        """Save current configuration to YAML file."""
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config_data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            print(f"Error: Could not save config file: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self.config_data.get(key, default)

    def set(self, key: str, value: Any):
        """
        Set configuration value.

        Args:
            key: Configuration key
            value: Value to set
        """
        self.config_data[key] = value

    # Convenience properties for commonly used values
    @property
    def com_port(self) -> str:
        return self.get('com_port', 'COM3')

    @com_port.setter
    def com_port(self, value: str):
        self.set('com_port', value)

    @property
    def baud_rate(self) -> int:
        return self.get('baud_rate', 115200)

    @property
    def default_feedrate(self) -> int:
        return self.get('default_feedrate', 100)

    @property
    def gripper_open_pulse(self) -> int:
        return self.get('gripper_open_pulse', 120)

    @property
    def gripper_close_pulse(self) -> int:
        return self.get('gripper_close_pulse', 40)

    @property
    def gripper_duration(self) -> float:
        return self.get('gripper_duration', 0.2)

    @property
    def auto_connect(self) -> bool:
        return self.get('auto_connect', False)

    @property
    def status_update_rate(self) -> int:
        return self.get('status_update_rate', 200)

    @property
    def axis_speed_multipliers(self) -> Dict[str, float]:
        """Get axis speed multipliers from config, or use defaults."""
        return self.get('axis_speed_multipliers', {
            'X': 1.0, 'Y': 1.0, 'Z': 2.5,
            'A': 2.5, 'B': 2.5, 'C': 2.5
        })

    @property
    def gripper_step(self) -> int:
        """Get gripper step size from config."""
        return self.get('gripper_step', 5)

    @property
    def camera_gesture_config(self) -> Dict[str, Any]:
        """Get camera gesture configuration with defaults."""
        defaults = {
            'neutral_zone': 0.35,
            'wrist_rotation_threshold': 40.0,
            'wrist_rotation_max': 60.0,
            'wrist_flexion_threshold': 40.0,
            'wrist_flexion_max': 70.0,
            'finger_spread_deadzone': 0.15,
            'smoothing_frames': 5,
        }
        user_config = self.get('camera_gesture', {})
        return {**defaults, **(user_config or {})}

    @staticmethod
    def _defaults() -> Dict[str, Any]:
        """
        Get default configuration values.

        Returns:
            Dictionary of default configuration
        """
        return {
            'com_port': 'COM3',
            'baud_rate': 115200,
            'default_jog_distance': 1.0,
            'default_feedrate': 100,
            'gripper_open_pulse': 120,
            'gripper_close_pulse': 20,
            'gripper_duration': 0.1,
            'gripper_step': 5,
            'auto_connect': False,
            'status_update_rate': 200,
            'axis_speed_multipliers': {
                'X': 1.0, 'Y': 1.0, 'Z': 2.5,
                'A': 2.5, 'B': 2.5, 'C': 2.5
            }
        }
