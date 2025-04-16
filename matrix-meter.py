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


class Column:
    TRAIL_FADE_LEVELS = 5  # Move constant to class level

    def __init__(self, x, height):
        self.x = x
        self.height = height
        self.last_positions = set()  # Track positions that need to be cleared
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
        self.last_positions.clear()

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

    def cleanup(self, stdscr):
        # Clear only the positions that were previously occupied
        for y in self.last_positions:
            if 0 <= y < self.height:
                try:
                    stdscr.addstr(y, self.x, " ")
                except curses.error:
                    pass
        self.last_positions.clear()

    def draw(self, stdscr, color_index):
        if not self.active:
            return

        # Clear previous positions
        self.cleanup(stdscr)

        # Track new positions
        new_positions = set()
        trail_color = curses.color_pair(color_index + 1)
        head_color = curses.color_pair(color_index + 11)

        # Draw visible trail
        for i in range(self.trail):
            offset = i if self.direction == "down" else -i
            y = self.y - offset if self.direction == "down" else self.y + offset
            if 0 <= y < self.height:
                new_positions.add(y)
                char = random.choice(CHARS)
                attr = curses.A_BOLD if random.random() < 0.1 else 0
                fade = max(0, self.TRAIL_FADE_LEVELS - i) / self.TRAIL_FADE_LEVELS
                color = (
                    head_color
                    if i == 0
                    else trail_color | (curses.A_BOLD if fade > 0.66 else curses.A_DIM)
                )
                try:
                    stdscr.addstr(y, self.x, char, color | attr)
                except curses.error:
                    pass

        self.last_positions = new_positions


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
                            char = random.choice(CHARS)
                            attr = curses.A_BOLD if random.random() < 0.1 else 0
                            fade = (
                                max(0, Column.TRAIL_FADE_LEVELS - i)
                                / Column.TRAIL_FADE_LEVELS
                            )
                            color = (
                                head_color
                                if i == 0
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

            stdscr.refresh()

            key = stdscr.getch()
            if key != -1:
                if key == ord("q"):
                    break
                elif key == ord("h"):
                    hud_visible = not hud_visible
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
