# Arctos 6-Axis Robotic Arm Control Software

Custom control software for the Arctos robotic arm with button-based jogging interface.

## Features

- ✅ **6-Axis Control**: Individual buttons for X, Y, Z, A, B, C axes (positive/negative)
- ✅ **Gripper Control**: Open/close buttons for servo gripper
- ✅ **Emergency Stop**: Large red button for immediate motion halt
- ✅ **Adjustable Parameters**: Real-time feedrate control
- ✅ **Position Display**: Live feedback of arm position
- ✅ **Serial Communication**: Direct GRBL communication at 115200 baud

## Requirements

- Python 3.10 or higher
- Arduino Mega 2560 with GRBL firmware (already flashed)
- Windows/Linux/macOS

## Installation

1. **Install Python dependencies**:
   ```bash
   cd arctos_control
   pip install -r requirements.txt
   ```

2. **Choose the COM port**:
   - Select your Arduino's port from the dropdown in the application (the choice is saved to `config.yaml`)

3. **Connect Arduino**:
   - Plug in Arduino Mega 2560 via USB
   - **Do NOT power on the motors yet**

## Usage

1. **Launch the application**:
   ```bash
   python main.py
   ```

2. **Connect to Arduino**:
   - Select COM port from dropdown
   - Click "Connect"
   - Wait for "Connected" status (green)

3. **Set the movement speed**:
   - Start with 100 mm/min (safe default)

4. **Test jogging** (IMPORTANT: Low speed first!):
   - **Before powering motors**: Make sure work area is clear
   - **Power on the robot**: Turn on motor power supply
   - Press and hold an axis button (e.g., X+)
   - Release button to stop motion
   - Verify axis moves in expected direction

5. **Emergency stop**:
   - Click red "EMERGENCY STOP" button to halt all motion immediately
   - Motion will pause; reconnect or reset to continue

## Safety Checklist

Before each session:
- [ ] Work area is clear (no obstacles)
- [ ] All wiring connections verified
- [ ] Power supply voltage correct (24V for motors, 6V for servo)
- [ ] Emergency stop button tested and accessible
- [ ] Start with feedrate = 100mm/min
- [ ] Monitor for unusual sounds, binding, or overheating

## Configuration

Edit `config.yaml` to customize:

```yaml
com_port: "COM3"              # Your Arduino COM port
default_feedrate: 100         # Default speed (mm/min)
gripper_open_pulse: 120       # Servo pulse for 100% open (raw value)
gripper_close_pulse: 20       # Servo pulse for 0% closed (raw value)
gripper_step: 5               # Percentage points per step (0-100 scale)
```

**Note**: Gripper position is shown as 0-100% in the UI (0=closed, 100=open) but converts to pulse values (20-120) internally.

## Troubleshooting

**"Connection failed"**:
- Check Arduino is plugged in via USB
- Verify correct COM port selected
- Check GRBL firmware is flashed (open Arduino Serial Monitor at 115200 baud - should see "Grbl" message)

**Axes don't move**:
- Verify motor power supply is ON
- Check wiring matches official Arctos open-loop diagram
- Send `$$` command in Serial Monitor to verify GRBL settings

**Gripper doesn't move**:
- Verify servo is connected to pin 6 (white wire to pin labeled "6" on Arduino Mega)
- Check servo power (red to the 6V buck output, black to GND)
- Try different pulse values in config.yaml (typical range: 20-120)

**Gripper position out of sync**:
- Click "Reset Position" button
- Enter current physical position: 0 if fully closed, 100 if fully open
- Software will sync and allow full range of motion

**BC axes binding or moving wrong**:
- GRBL handles BC coupling automatically - just send normal B/C commands
- If binding occurs, reduce feedrate or check mechanical alignment

## GRBL Commands Reference

The software sends these commands to GRBL:

| Command | Description |
|---------|-------------|
| `$J=G91 X1000.00 F540` | Jog X-axis (stopped by jog cancel on release) |
| `!` | Feed hold (pause motion) |
| `0x85` | Jog cancel (stop jog) |
| `M97 B120 T0.2` | Open gripper |
| `M97 B20 T0.2` | Close gripper |
| `?` | Request status report |

## Future Enhancements

Planned features:
- Macro recording/playback
- Keyboard shortcuts for jogging
- Teaching mode (record arm movements)
- 3D visualization of arm position
- Zero position setting
- Custom motion sequences

## License

This software is provided for educational and personal use with the Arctos robotic arm.

## Support

For issues or questions:
- Check the official Arctos documentation: https://arctosrobotics.com/docs/
- GRBL documentation: https://github.com/gnea/grbl
