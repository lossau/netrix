# Netrix

A Matrix-style network traffic visualizer for the terminal. Watch your network activity in real-time with a beautiful falling character effect. Download traffic is shown as downward streams, and upload traffic as upward streams. The density of streams corresponds to your network activity level.

## Features

- Real-time network traffic visualization with Matrix-style effects
- Separate visualization for download (downward) and upload (upward) streams
- Customizable color themes
- Interactive HUD (Heads-Up Display) showing network speeds
- Keyboard controls for customization
- Automatically detects and monitors the primary network interface

## Requirements

- Python 3.6 or higher
- A terminal with curses support (most Unix-like systems have this built-in)
- `psutil` library for network monitoring

## Installation

1. Clone or download this repository:
   ```bash
   git clone <repository-url>
   cd netrix
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

   Or install directly:
   ```bash
   pip install psutil==7.1.3
   ```

## Usage

Run the application:
```bash
python run.py
```

The application will automatically detect your primary network interface and start displaying network traffic in real-time.

### Controls

- **q** - Quit the application
- **h** - Toggle help overlay
- **d** - Cycle download color theme
- **u** - Cycle upload color theme
- **c** - Cycle both color themes simultaneously
- **m** - Toggle numeric meter (HUD) visibility
- **p** - Change meter position (top_right, top_left, bottom_right, bottom_left, center)

### Visual Elements

- **Downward streams** (↓) - Represent download traffic
- **Upward streams** (↑) - Represent upload traffic
- **Stream density** - More active columns indicate higher network activity
- **HUD** - Shows current upload and download speeds in human-readable format (B/s, KB/s, MB/s, GB/s)

## How It Works

Netrix monitors your network interface using `psutil` and converts the traffic data into a visual representation. The number of active columns is proportional to your network speed, creating a dynamic visualization that responds to your actual network activity.

The application uses the curses library for terminal rendering, providing smooth animations and a responsive interface that works in most terminal emulators.

## Troubleshooting

- **No network interfaces found**: Make sure you have an active network connection and that `psutil` can detect your network interfaces.
- **Display issues**: Ensure your terminal supports curses and has sufficient size (at least 2x2 characters).
- **Import errors**: Make sure `psutil` is installed correctly: `pip install psutil`

## License

MIT
