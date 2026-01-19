import curses
import random
import time
import psutil


CHARS = '日ﾊﾐﾋｰｳｼﾅﾓﾆｻﾜﾂｵﾘｱﾎﾃﾏｹﾒｴｶｷﾑﾕﾗｾﾈｽﾀﾇﾍ012345789Z:・."=*+-<>¦｜╌ｸ'
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
    counters = psutil.net_io_counters(pernic=True)
    return max(counters, key=lambda k: counters[k].bytes_recv + counters[k].bytes_sent)


def get_network_io(interface):
    stats = psutil.net_io_counters(pernic=True)[interface]
    return stats.bytes_recv, stats.bytes_sent


def format_speed(bps):
    for unit in ["B/s", "KB/s", "MB/s", "GB/s"]:
        if bps < 1024:
            return f"{bps:.1f} {unit}"
        bps /= 1024
    return f"{bps:.1f} TB/s"


def draw_help_overlay(stdscr, height, width):
    """Draw a help overlay showing available commands."""
    help_lines = [
        "Commands:",
        "",
        "  q  - Quit",
        "  h  - Toggle this help",
        "  d  - Cycle download color",
        "  u  - Cycle upload color",
        "  c  - Cycle both colors",
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
    TRAIL_FADE_LEVELS = 5

    def __init__(self, x, height):
        self.x = x
        self.height = height
        self.trail_chars = []  # Store characters for each position in the trail
        self.trail_timers = []  # Track when each character should change
        self.reset()

    def reset(self):
        self.direction = random.choice(["down", "up"])
        # Ensure trail length is always valid (at least 1, at most height//2, but never less than 5)
        min_trail = min(5, self.height)
        max_trail = max(min_trail, self.height // 2)
        self.trail = random.randint(min_trail, max_trail)
        self.speed = random.randint(1, 3)
        self.frame_counter = 0
        self.start_delay = random.randint(0, 10)
        self.active = False
        if self.direction == "down":
            self.y = -self.trail
        else:
            self.y = self.height + self.trail
        # Initialize trail characters and timers
        self.trail_chars = [random.choice(CHARS) for _ in range(self.trail)]
        self.trail_timers = [0 for _ in range(self.trail)]

    def update(self):
        if not self.active:
            return False
        if self.start_delay > 0:
            self.start_delay -= 1
            return False
        self.frame_counter += 1
        if self.frame_counter < self.speed:
            return False
        self.frame_counter = 0
        if self.direction == "down":
            self.y += 1
        else:
            self.y -= 1
        if (self.direction == "down" and self.y - self.trail > self.height) or (
            self.direction == "up" and self.y + self.trail < 0
        ):
            self.reset()
            return True
        return True

    def update_chars(self):
        if not self.active:
            return
        # Head always changes
        self.trail_chars[0] = random.choice(CHARS)
        # Update trail characters based on their position
        for i in range(1, self.trail):
            self.trail_timers[i] += 1
            # Change probability decreases with distance from head
            if random.random() < (1.0 / (i + 1)):
                self.trail_chars[i] = random.choice(CHARS)
                self.trail_timers[i] = 0

    def cleanup(self, stdscr):
        # Clear only the positions that were previously occupied
        for y in range(self.y, self.y + self.trail):
            if 0 <= y < self.height:
                try:
                    stdscr.addstr(y, self.x, " ")
                except curses.error:
                    pass

    def draw(self, stdscr, color_index):
        if not self.active:
            return

        # Clear previous positions
        self.cleanup(stdscr)

        # Draw visible trail
        trail_color = curses.color_pair(color_index + 1)
        head_color = curses.color_pair(color_index + 11)

        for i in range(self.trail):
            offset = i if self.direction == "down" else -i
            y = self.y - offset if self.direction == "down" else self.y + offset
            if 0 <= y < self.height:
                char = self.trail_chars[i]
                attr = curses.A_BOLD if random.random() < 0.1 else 0
                # Reverse fade calculation for upward streams
                fade_i = i if self.direction == "down" else self.trail - 1 - i
                fade = (
                    max(0, Column.TRAIL_FADE_LEVELS - fade_i) / Column.TRAIL_FADE_LEVELS
                )
                color = (
                    head_color
                    if fade_i == 0
                    else trail_color | (curses.A_BOLD if fade > 0.66 else curses.A_DIM)
                )
                try:
                    stdscr.addstr(y, self.x, char, color | attr)
                except curses.error:
                    pass


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    curses.start_color()
    curses.use_default_colors()

    # Enable window buffering to reduce flicker
    curses.cbreak()
    curses.noecho()
    stdscr.scrollok(False)
    stdscr.idlok(True)
    stdscr.leaveok(True)

    for i, (fg, _) in enumerate(COLOR_THEMES):
        curses.init_pair(i + 1, fg, -1)
        curses.init_pair(i + 11, fg, -1)

    interface = get_main_interface()
    last_recv, last_sent = get_network_io(interface)
    last_check = time.time()

    download_speed = upload_speed = 0
    download_color_index = 0
    upload_color_index = 1
    hud_visible = True
    help_overlay_visible = False
    startup_message_visible = True
    startup_message_start_time = time.time()
    STARTUP_MESSAGE_DURATION = 3.0  # Show for 3 seconds

    FRAME_DELAY = 0.05
    DENSITY_SMOOTHING = 0.2
    down_target = up_target = 0.0
    columns = []

    while True:
        try:
            height, width = stdscr.getmaxyx()
            if height < 2 or width < 2:  # Minimum size check
                time.sleep(FRAME_DELAY)
                continue

            base_density = int(width * 0.05)  # Add back base_density calculation

            if len(columns) != width:
                columns = [Column(x, height) for x in range(width)]
            else:
                for col in columns:
                    col.height = height

            # Clear the entire screen at the start of each frame
            stdscr.erase()  # Use erase() instead of clear() for less flicker

            now = time.time()

            # Check if startup message should still be visible
            if startup_message_visible:
                if now - startup_message_start_time >= STARTUP_MESSAGE_DURATION:
                    startup_message_visible = False

            if now - last_check >= 0.5:
                recv, sent = get_network_io(interface)
                delta = now - last_check
                download_speed = (recv - last_recv) / delta
                upload_speed = (sent - last_sent) / delta
                last_recv, last_sent = recv, sent
                last_check = now

            raw_down = min(width, max(base_density, int(download_speed / 10_000)))
            raw_up = min(width, max(base_density, int(upload_speed / 10_000)))
            down_target += DENSITY_SMOOTHING * (raw_down - down_target)
            up_target += DENSITY_SMOOTHING * (raw_up - up_target)

            # Count currently active columns by type
            down_active = sum(1 for c in columns if c.active and c.direction == "down")
            up_active = sum(1 for c in columns if c.active and c.direction == "up")

            # Randomly activate more columns up to density
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

            for col in columns:
                col.update()
                col.update_chars()  # Update characters before drawing
                if col.active:
                    color_index = (
                        download_color_index
                        if col.direction == "down"
                        else upload_color_index
                    )
                    trail_color = curses.color_pair(color_index + 1)
                    head_color = curses.color_pair(color_index + 11)

                    # Draw visible trail
                    for i in range(col.trail):
                        offset = i if col.direction == "down" else -i
                        y = (
                            col.y - offset
                            if col.direction == "down"
                            else col.y + offset
                        )
                        if 0 <= y < height:
                            char = col.trail_chars[i]
                            attr = curses.A_BOLD if random.random() < 0.1 else 0
                            # Reverse fade calculation for upward streams
                            fade_i = i if col.direction == "down" else col.trail - 1 - i
                            fade = (
                                max(0, Column.TRAIL_FADE_LEVELS - fade_i)
                                / Column.TRAIL_FADE_LEVELS
                            )
                            color = (
                                head_color
                                if fade_i == 0
                                else trail_color
                                | (curses.A_BOLD if fade > 0.66 else curses.A_DIM)
                            )
                            try:
                                stdscr.addstr(y, col.x, char, color | attr)
                            except curses.error:
                                pass

            if hud_visible:
                up_str = f"↑ {format_speed(upload_speed)}"
                down_str = f"↓ {format_speed(download_speed)}"
                hud_width = max(len(up_str), len(down_str))
                start_x = width - hud_width - 1
                hud_y = 0
                try:
                    stdscr.addstr(
                        hud_y,
                        start_x,
                        "↑",
                        curses.color_pair(upload_color_index + 1) | curses.A_BOLD,
                    )
                    stdscr.addstr(
                        hud_y,
                        start_x + 1,
                        f" {format_speed(upload_speed)}",
                        curses.A_BOLD,
                    )
                    stdscr.addstr(
                        hud_y + 1,
                        start_x,
                        "↓",
                        curses.color_pair(download_color_index + 1) | curses.A_BOLD,
                    )
                    stdscr.addstr(
                        hud_y + 1,
                        start_x + 1,
                        f" {format_speed(download_speed)}",
                        curses.A_BOLD,
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

            stdscr.refresh()

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

            time.sleep(FRAME_DELAY)
        except curses.error:
            # Handle curses errors gracefully, especially during resize
            time.sleep(FRAME_DELAY)
            continue


if __name__ == "__main__":
    curses.wrapper(main)
