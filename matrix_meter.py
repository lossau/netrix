"""
Matrix-style network traffic visualizer for the terminal.

This module provides a real-time visualization of network traffic using a
Matrix-style falling character effect. Download traffic is shown as downward
streams, and upload traffic as upward streams. The density of streams
corresponds to the network activity level.

Usage:
    python matrix_meter.py

Controls:
    q - Quit
    h - Toggle help overlay
    d - Cycle download color
    u - Cycle upload color
    c - Cycle both colors
    m - Toggle numeric meter visibility
    p - Change meter position
"""

import curses
import random
import time
import psutil


# Character set used for the Matrix effect (Japanese katakana, numbers, symbols)
CHARS = '日ﾊﾐﾋｰｳｼﾅﾓﾆｻﾜﾂｵﾘｱﾎﾃﾏｹﾒｴｶｷﾑﾕﾗｾﾈｽﾀﾇﾍ012345789Z:・."=*+-<>¦｜╌ｸ'

# Animation and rendering constants
FRAME_DELAY = 0.05  # Delay between frames in seconds (20 FPS)
DENSITY_SMOOTHING = 0.2  # Smoothing factor for column density changes (0-1)
SPEED_DIVISOR = 10_000  # Divisor for converting bytes/s to column density
BASE_DENSITY_FACTOR = 0.05  # Base density as fraction of screen width (5%)
STARTUP_MESSAGE_DURATION = 3.0  # Seconds to show startup message
BOLD_PROBABILITY = 0.1  # Probability of bold character in trail (10%)
FADE_THRESHOLD = 0.66  # Fade threshold for trail brightness (66%)

# Color themes: (foreground, background) pairs for stream visualization
# Background is typically ignored (uses terminal default)
COLOR_THEMES = [
    (curses.COLOR_GREEN, curses.COLOR_BLACK),
    (curses.COLOR_CYAN, curses.COLOR_BLACK),
    (curses.COLOR_YELLOW, curses.COLOR_BLACK),
    (curses.COLOR_MAGENTA, curses.COLOR_BLACK),
    (curses.COLOR_RED, curses.COLOR_BLACK),
    (curses.COLOR_BLUE, curses.COLOR_BLACK),
    (curses.COLOR_WHITE, curses.COLOR_BLACK),
    (curses.COLOR_GREEN, curses.COLOR_YELLOW),
    (curses.COLOR_MAGENTA, curses.COLOR_CYAN),
    (curses.COLOR_CYAN, curses.COLOR_GREEN),
]


def get_main_interface():
    """
    Identify the primary network interface based on total traffic.

    The interface with the highest combined bytes received and sent is
    selected as the main interface for monitoring.

    Returns:
        str: Name of the network interface with the most traffic.

    Raises:
        RuntimeError: If no network interfaces are found.
    """
    counters = psutil.net_io_counters(pernic=True)
    if not counters:
        raise RuntimeError("No network interfaces found")
    return max(counters, key=lambda k: counters[k].bytes_recv + counters[k].bytes_sent)


def get_network_io(interface):
    """
    Get current network I/O statistics for a specific interface.

    Args:
        interface (str): Name of the network interface to query.

    Returns:
        tuple: (bytes_received, bytes_sent) cumulative totals for the interface.

    Raises:
        KeyError: If the specified interface does not exist.
    """
    stats = psutil.net_io_counters(pernic=True)[interface]
    return stats.bytes_recv, stats.bytes_sent


def format_speed(bps):
    """
    Format bytes per second into a human-readable string.

    Converts bytes to the most appropriate unit (B/s, KB/s, MB/s, GB/s, TB/s)
    and returns a formatted string with no decimal places.

    Args:
        bps (float): Bytes per second to format.

    Returns:
        str: Formatted speed string (e.g., "1024 KB/s", "5 MB/s").
    """
    for unit in ["B/s", "KB/s", "MB/s", "GB/s"]:
        if bps < 1024.0:
            return f"{int(bps)} {unit}"
        bps /= 1024.0
    return f"{int(bps)} TB/s"


def get_hud_position(hud_position, height, width, hud_width):
    """
    Calculate the screen position for the HUD (Heads-Up Display) meter.

    The HUD displays network speed information and can be positioned at
    various locations on the screen.

    Args:
        hud_position (str): Position name - one of:
            - "top_right": Top right corner
            - "top_left": Top left corner
            - "bottom_right": Bottom right corner
            - "bottom_left": Bottom left corner
            - "center": Center of screen
        height (int): Screen height in characters.
        width (int): Screen width in characters.
        hud_width (int): Width of the HUD text in characters.

    Returns:
        tuple: (y, x) coordinates for the HUD position. Defaults to top_right
            if an invalid position is specified.
    """
    if hud_position == "top_right":
        return 0, width - hud_width - 1
    elif hud_position == "top_left":
        return 0, 1
    elif hud_position == "bottom_right":
        return height - 2, width - hud_width - 1
    elif hud_position == "bottom_left":
        return height - 2, 1
    elif hud_position == "center":
        # Center vertically, accounting for 2-line HUD
        center_y = max(0, (height - 2) // 2)
        center_x = max(1, (width - hud_width) // 2)
        return center_y, center_x
    else:
        return 0, width - hud_width - 1  # Default to top_right


def draw_help_overlay(stdscr, height, width):
    """
    Draw a help overlay showing available keyboard commands.

    The overlay is centered on the screen with a bordered box containing
    the help text. It automatically adjusts if the screen is too small.

    Args:
        stdscr: Curses window object.
        height (int): Screen height in characters.
        width (int): Screen width in characters.
    """
    help_lines = [
        "Commands:",
        "",
        "  q  - Quit",
        "  h  - Toggle this help",
        "  d  - Cycle download color",
        "  u  - Cycle upload color",
        "  c  - Cycle both colors",
        "  m  - Toggle numeric meter",
        "  p  - Change meter position",
        "",
        "Press 'h' to close",
    ]

    # Calculate overlay dimensions
    overlay_height = len(help_lines) + 2
    overlay_width = max(len(line) for line in help_lines) + 4

    # Center the overlay
    start_y = (height - overlay_height) // 2
    start_x = (width - overlay_width) // 2

    # Ensure overlay fits on screen
    if start_y < 0:
        start_y = 0
    if start_x < 0:
        start_x = 0
    if start_y + overlay_height > height:
        overlay_height = height - start_y
    if start_x + overlay_width > width:
        overlay_width = width - start_x

    # Draw border
    try:
        # Top and bottom borders
        for x in range(start_x + 1, min(start_x + overlay_width - 1, width - 1)):
            if start_y < height:
                stdscr.addstr(start_y, x, "─", curses.color_pair(7) | curses.A_BOLD)
            if start_y + overlay_height - 1 < height:
                stdscr.addstr(
                    start_y + overlay_height - 1,
                    x,
                    "─",
                    curses.color_pair(7) | curses.A_BOLD,
                )
        # Left and right borders
        for y in range(start_y + 1, min(start_y + overlay_height - 1, height - 1)):
            if start_x < width:
                stdscr.addstr(y, start_x, "│", curses.color_pair(7) | curses.A_BOLD)
            if start_x + overlay_width - 1 < width:
                stdscr.addstr(
                    y,
                    start_x + overlay_width - 1,
                    "│",
                    curses.color_pair(7) | curses.A_BOLD,
                )
        # Corners
        if start_y < height and start_x < width:
            stdscr.addstr(start_y, start_x, "┌", curses.color_pair(7) | curses.A_BOLD)
        if start_y < height and start_x + overlay_width - 1 < width:
            stdscr.addstr(
                start_y,
                start_x + overlay_width - 1,
                "┐",
                curses.color_pair(7) | curses.A_BOLD,
            )
        if start_y + overlay_height - 1 < height and start_x < width:
            stdscr.addstr(
                start_y + overlay_height - 1,
                start_x,
                "└",
                curses.color_pair(7) | curses.A_BOLD,
            )
        if (
            start_y + overlay_height - 1 < height
            and start_x + overlay_width - 1 < width
        ):
            stdscr.addstr(
                start_y + overlay_height - 1,
                start_x + overlay_width - 1,
                "┘",
                curses.color_pair(7) | curses.A_BOLD,
            )
    except curses.error:
        pass

    # Draw help text
    text_start_y = start_y + 1
    text_start_x = start_x + 2
    for i, line in enumerate(help_lines):
        y = text_start_y + i
        if y >= height - 1:
            break
        try:
            stdscr.addstr(
                y,
                text_start_x,
                line[: overlay_width - 4],
                curses.color_pair(7) | curses.A_BOLD,
            )
        except curses.error:
            pass


class Column:
    """
    Represents a single column in the Matrix-style visualization.

    Each column can display a falling or rising stream of characters that
    represents network traffic. The column manages its own position, speed,
    trail length, and character updates.

    Attributes:
        TRAIL_FADE_LEVELS (int): Number of fade levels for the trail effect.
        x (int): Horizontal position (column index) on screen.
        height (int): Screen height in characters.
        direction (str): Movement direction - "down" or "up".
        trail (int): Length of the character trail.
        speed (int): Movement speed (frames per step, 1-3).
        y (int): Current vertical position of the trail head.
        active (bool): Whether this column is currently active.
        trail_chars (list): Characters displayed in the trail.
        trail_timers (list): Timers for character change animations.
        frame_counter (int): Counter for speed control.
        start_delay (int): Frames to wait before starting movement.
    """

    TRAIL_FADE_LEVELS = 5  # Number of fade levels for visual effect

    def __init__(self, x, height):
        """
        Initialize a new column at the specified position.

        Args:
            x (int): Horizontal position (column index) on screen.
            height (int): Screen height in characters.
        """
        self.x = x
        self.height = height
        self.trail_chars = []  # Store characters for each position in the trail
        self.trail_timers = []  # Track when each character should change
        self.frame_counter = 0  # Initialize frame_counter to fix linter warning
        self.reset()

    def reset(self):
        """
        Reset the column with new random properties.

        Randomly selects direction, trail length, speed, and starting position.
        The column is deactivated and positioned off-screen, ready to be
        activated when needed.
        """
        self.direction = random.choice(["down", "up"])
        # Ensure trail length is always valid (at least 1, at most height//2, but never less than 5)
        min_trail = min(5, self.height)
        max_trail = max(min_trail, self.height // 2)
        self.trail = random.randint(min_trail, max_trail)
        self.speed = random.randint(1, 3)  # Frames per movement step
        self.frame_counter = 0
        self.start_delay = random.randint(0, 10)  # Random delay before starting
        self.active = False
        # Position off-screen based on direction
        if self.direction == "down":
            self.y = -self.trail  # Start above screen
        else:
            self.y = self.height + self.trail  # Start below screen
        # Initialize trail characters and timers
        self.trail_chars = [random.choice(CHARS) for _ in range(self.trail)]
        self.trail_timers = [0 for _ in range(self.trail)]

    def update(self):
        """
        Update the column's position for the current frame.

        Handles movement speed, start delay, and boundary checking.
        Resets the column when it moves completely off-screen.

        Returns:
            bool: True if the column was updated, False if inactive or waiting.
        """
        if not self.active:
            return False
        if self.start_delay > 0:
            self.start_delay -= 1
            return False
        self.frame_counter += 1
        if self.frame_counter < self.speed:
            return False
        self.frame_counter = 0
        # Move based on direction
        if self.direction == "down":
            self.y += 1
        else:
            self.y -= 1
        # Check if completely off-screen and reset if so
        if (self.direction == "down" and self.y - self.trail > self.height) or (
            self.direction == "up" and self.y + self.trail < 0
        ):
            self.reset()
            return True
        return True

    def update_chars(self):
        """
        Update characters in the trail for animation effect.

        The head character always changes. Trail characters change with
        decreasing probability based on their distance from the head,
        creating a more dynamic visual effect.
        """
        if not self.active:
            return
        # Head always changes for maximum visual activity
        self.trail_chars[0] = random.choice(CHARS)
        # Update trail characters based on their position
        for i in range(1, self.trail):
            self.trail_timers[i] += 1
            # Change probability decreases with distance from head
            # (1/2 for position 1, 1/3 for position 2, etc.)
            if random.random() < (1.0 / (i + 1)):
                self.trail_chars[i] = random.choice(CHARS)
                self.trail_timers[i] = 0

    def cleanup(self, stdscr):
        """
        Clear the previous positions occupied by this column's trail.

        Erases characters from the screen before drawing new ones to prevent
        ghosting. Handles both downward and upward streams correctly.

        Args:
            stdscr: Curses window object.
        """
        # Clear only the positions that were previously occupied
        # Handle both downward and upward streams correctly
        if self.direction == "down":
            start_y = self.y
            end_y = self.y + self.trail
        else:
            # For upward streams, trail extends backward from head
            start_y = self.y - self.trail + 1
            end_y = self.y + 1
        for y in range(start_y, end_y):
            if 0 <= y < self.height:
                try:
                    stdscr.addstr(y, self.x, " ")
                except curses.error:
                    pass

    def draw(self, stdscr, color_index):
        """
        Draw the column's trail on the screen.

        Clears previous positions and draws the current trail with appropriate
        colors and fade effects. The head is brighter, and the trail fades
        based on distance from the head.

        Args:
            stdscr: Curses window object.
            color_index (int): Index into COLOR_THEMES for this column's color.
        """
        if not self.active:
            return

        # Clear previous positions to prevent ghosting
        self.cleanup(stdscr)

        # Get color pairs (regular and bright for head)
        trail_color = curses.color_pair(color_index + 1)
        head_color = curses.color_pair(color_index + 11)

        for i in range(self.trail):
            # Calculate screen position based on direction
            offset = i if self.direction == "down" else -i
            y = self.y - offset if self.direction == "down" else self.y + offset
            if 0 <= y < self.height:
                char = self.trail_chars[i]
                # Randomly make some characters bold for visual interest
                attr = curses.A_BOLD if random.random() < BOLD_PROBABILITY else 0
                # Reverse fade calculation for upward streams
                # (head should always be brightest)
                fade_i = i if self.direction == "down" else self.trail - 1 - i
                fade = (
                    max(0, Column.TRAIL_FADE_LEVELS - fade_i) / Column.TRAIL_FADE_LEVELS
                )
                # Head uses bright color, trail fades based on distance
                color = (
                    head_color
                    if fade_i == 0
                    else trail_color
                    | (curses.A_BOLD if fade > FADE_THRESHOLD else curses.A_DIM)
                )
                try:
                    stdscr.addstr(y, self.x, char, color | attr)
                except curses.error:
                    pass


def main(stdscr):
    """
    Main application loop for the Matrix network meter.

    Initializes curses, sets up colors, monitors network traffic, and
    manages the visualization loop with keyboard input handling.

    Args:
        stdscr: Curses window object (provided by curses.wrapper).
    """
    # Initialize curses settings
    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(True)  # Non-blocking input
    curses.start_color()
    curses.use_default_colors()

    # Enable window buffering to reduce flicker
    curses.cbreak()  # Character-by-character input
    curses.noecho()  # Don't echo typed characters
    stdscr.scrollok(False)  # Disable scrolling
    stdscr.idlok(True)  # Enable insert/delete line
    stdscr.leaveok(True)  # Cursor can leave window

    # Initialize color pairs for each theme
    # Pairs 1-10: regular trail colors
    # Pairs 11-20: bright head colors (same colors, brighter)
    for i, (fg, _) in enumerate(COLOR_THEMES):
        curses.init_pair(i + 1, fg, -1)  # Regular color
        curses.init_pair(i + 11, fg, -1)  # Bright color (same, but used differently)

    # Initialize network monitoring
    interface = get_main_interface()
    last_recv, last_sent = get_network_io(interface)
    last_check = time.time()

    # Application state
    download_speed = upload_speed = 0
    download_color_index = 0  # Green (first theme)
    upload_color_index = 4  # Red (fifth theme)
    hud_visible = True
    hud_positions = ["top_right", "top_left", "bottom_right", "bottom_left", "center"]
    hud_position_index = 3  # Start at bottom_left
    help_overlay_visible = False
    startup_message_visible = True
    startup_message_start_time = time.time()

    # Column density targets (smoothed values)
    down_target = up_target = 0.0
    columns = []

    # Main application loop
    while True:
        try:
            height, width = stdscr.getmaxyx()
            # Skip rendering if screen is too small
            if height < 2 or width < 2:
                time.sleep(FRAME_DELAY)
                continue

            # Calculate base density (minimum number of active columns)
            base_density = int(width * BASE_DENSITY_FACTOR)

            # Recreate columns if screen width changed
            if len(columns) != width:
                columns = [Column(x, height) for x in range(width)]
            else:
                # Update height for existing columns
                for col in columns:
                    col.height = height

            # Clear the entire screen at the start of each frame
            # Use erase() instead of clear() for less flicker
            stdscr.erase()

            now = time.time()

            # Check if startup message should still be visible
            if startup_message_visible:
                if now - startup_message_start_time >= STARTUP_MESSAGE_DURATION:
                    startup_message_visible = False

            # Update network statistics every second
            if now - last_check >= 1:
                try:
                    recv, sent = get_network_io(interface)
                    delta = now - last_check
                    download_speed = (recv - last_recv) / delta
                    upload_speed = (sent - last_sent) / delta
                    last_recv, last_sent = recv, sent
                    last_check = now
                except (KeyError, AttributeError):
                    # Interface may have disappeared, try to get a new one
                    try:
                        interface = get_main_interface()
                        last_recv, last_sent = get_network_io(interface)
                        last_check = now
                    except (RuntimeError, KeyError):
                        # No interfaces available, keep using last known speeds
                        pass

            # Calculate target column density based on network speed
            # Convert bytes/s to number of columns, with minimum base_density
            raw_down = min(
                width, max(base_density, int(download_speed / SPEED_DIVISOR))
            )
            raw_up = min(width, max(base_density, int(upload_speed / SPEED_DIVISOR)))
            # Smooth density changes to avoid jarring transitions
            down_target += DENSITY_SMOOTHING * (raw_down - down_target)
            up_target += DENSITY_SMOOTHING * (raw_up - up_target)

            # Count currently active columns by type
            down_active = sum(1 for c in columns if c.active and c.direction == "down")
            up_active = sum(1 for c in columns if c.active and c.direction == "up")

            # Randomly activate more columns up to target density
            if down_active < int(down_target):
                available = [
                    c for c in columns if not c.active and c.direction == "down"
                ]
                to_activate = random.sample(
                    available, min(len(available), int(down_target) - down_active)
                )
                for c in to_activate:
                    c.active = True

            if up_active < int(up_target):
                available = [c for c in columns if not c.active and c.direction == "up"]
                to_activate = random.sample(
                    available, min(len(available), int(up_target) - up_active)
                )
                for c in to_activate:
                    c.active = True

            # Update and draw all columns
            for col in columns:
                col.update()
                col.update_chars()  # Update characters before drawing
                if col.active:
                    # Select color based on direction (down=download, up=upload)
                    color_index = (
                        download_color_index
                        if col.direction == "down"
                        else upload_color_index
                    )
                    col.draw(stdscr, color_index)

            # Draw HUD (Heads-Up Display) with network speeds
            if hud_visible:
                up_str = f"{format_speed(upload_speed)} ↑"
                down_str = f"{format_speed(download_speed)} ↓"
                hud_width = max(len(up_str), len(down_str))
                hud_y, start_x = get_hud_position(
                    hud_positions[hud_position_index], height, width, hud_width
                )
                try:
                    stdscr.addstr(
                        hud_y,
                        start_x + 1,
                        up_str,
                        curses.color_pair(upload_color_index + 1) | curses.A_BOLD,
                    )
                    stdscr.addstr(
                        hud_y + 1,
                        start_x + 1,
                        down_str,
                        curses.color_pair(download_color_index + 1) | curses.A_BOLD,
                    )
                except curses.error:
                    pass

            if help_overlay_visible:
                draw_help_overlay(stdscr, height, width)

            if startup_message_visible:
                message = "Press 'h' for help"
                message_x = (width - len(message)) // 2
                message_y = height - 1
                if message_x >= 0 and message_y >= 0:
                    try:
                        stdscr.addstr(
                            message_y,
                            message_x,
                            message,
                            curses.color_pair(7) | curses.A_BOLD,
                        )
                    except curses.error:
                        pass

            # Refresh screen to display all changes
            stdscr.refresh()

            # Handle keyboard input
            key = stdscr.getch()
            if key != -1:
                if key == ord("q"):
                    break
                elif key == ord("h"):
                    help_overlay_visible = not help_overlay_visible
                    startup_message_visible = (
                        False  # Hide startup message when help is toggled
                    )
                elif key == ord("d"):
                    download_color_index = (download_color_index + 1) % len(
                        COLOR_THEMES
                    )
                elif key == ord("u"):
                    upload_color_index = (upload_color_index + 1) % len(COLOR_THEMES)
                elif key == ord("c"):
                    download_color_index = (download_color_index + 1) % len(
                        COLOR_THEMES
                    )
                    upload_color_index = (upload_color_index + 1) % len(COLOR_THEMES)
                elif key == ord("m"):
                    hud_visible = not hud_visible
                elif key == ord("p"):
                    hud_position_index = (hud_position_index + 1) % len(hud_positions)

            # Frame rate control
            time.sleep(FRAME_DELAY)
        except curses.error:
            # Handle curses errors gracefully, especially during window resize
            time.sleep(FRAME_DELAY)
            continue


if __name__ == "__main__":
    curses.wrapper(main)
