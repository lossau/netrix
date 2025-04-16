import curses
import random
import time
import psutil


CHARS = "日ﾊﾐﾋｰｳｼﾅﾓﾆｻﾜﾂｵﾘｱﾎﾃﾏｹﾒｴｶｷﾑﾕﾗｾﾈｽﾀﾇﾍ012345789Z:・.\"=*+-<>¦｜╌ｸ"
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
    for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
        if bps < 1024:
            return f"{bps:.1f} {unit}"
        bps /= 1024
    return f"{bps:.1f} TB/s"


class Column:
    def __init__(self, direction, height):
        self.direction = direction
        self.height = height
        self.active = False
        self.y = random.randint(0, height - 1)
        self.trail = random.randint(5, max(5, height // 2))

    def reset(self, height=None):
        if height:
            self.height = height
        self.y = random.randint(0, self.height - 1)
        self.trail = random.randint(5, max(5, self.height // 2))


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    curses.start_color()
    curses.use_default_colors()

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
    TRAIL_FADE_LEVELS = 5
    down_target = up_target = 0.0
    columns = []

    while True:
        height, width = stdscr.getmaxyx()
        base_density = int(width * 0.05)

        # Resize column array if needed
        while len(columns) < width:
            direction = random.choice(["down", "up"])
            columns.append(Column(direction, height))
        while len(columns) > width:
            columns.pop()

        for col in columns:
            col.height = height  # Update height on resize

        stdscr.erase()
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

        down_count = sum(
            1 for c in columns if c.active and c.direction == "down")
        up_count = sum(1 for c in columns if c.active and c.direction == "up")

        for target, active, direction in [
            (down_target, down_count, "down"),
            (up_target, up_count, "up"),
        ]:
            if active < int(target):
                available = [
                    c for c in columns if not c.active and c.direction == direction]
                for c in random.sample(available, min(len(available), int(target) - active)):
                    c.active = True
                    c.reset(height)
            elif active > int(target):
                active_cols = [
                    c for c in columns if c.active and c.direction == direction]
                for c in random.sample(active_cols, active - int(target)):
                    c.active = False

        for x, col in enumerate(columns[:width]):
            if not col.active:
                continue

            color_index = download_color_index if col.direction == "down" else upload_color_index
            trail_color = curses.color_pair(color_index + 1)
            head_color = curses.color_pair(color_index + 11)

            for i in range(col.trail):
                offset = i if col.direction == "down" else -i
                y = (col.y + offset) % height
                if not (0 <= y < height):
                    continue
                char = random.choice(CHARS)
                attr = curses.A_BOLD if random.random() < 0.1 else 0
                fade = max(0, TRAIL_FADE_LEVELS - i) / TRAIL_FADE_LEVELS
                color = (
                    head_color if i == 0 else
                    trail_color | (curses.A_BOLD if fade >
                                   0.66 else curses.A_DIM)
                )
                try:
                    stdscr.addstr(y, x, char, color | attr)
                except curses.error:
                    pass

            col.y = (
                col.y + 1) % height if col.direction == "down" else (col.y - 1) % height

        if hud_visible:
            # Format speeds
            up_str = f"↑ {format_speed(upload_speed)}"
            down_str = f"↓ {format_speed(download_speed)}"

            # Determine max HUD width (the longer of the two lines)
            hud_width = max(len(up_str), len(down_str))

            # Position HUD at top right
            start_x = width - hud_width - 1
            hud_y = 0

            # Draw upload line with colored arrow
            try:
                stdscr.addstr(hud_y, start_x, "↑", curses.color_pair(
                    upload_color_index + 1) | curses.A_BOLD)
                stdscr.addstr(hud_y, start_x + 1,
                              f" {format_speed(upload_speed)}", curses.A_BOLD)
            except curses.error:
                pass

            # Draw download line with colored arrow
            try:
                stdscr.addstr(
                    hud_y + 1, start_x, "↓", curses.color_pair(download_color_index + 1) | curses.A_BOLD)
                stdscr.addstr(hud_y + 1, start_x + 1,
                              f" {format_speed(download_speed)}", curses.A_BOLD)
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
                download_color_index = (
                    download_color_index + 1) % len(COLOR_THEMES)
            elif key == ord("u"):
                upload_color_index = (
                    upload_color_index + 1) % len(COLOR_THEMES)
            elif key == ord("c"):
                download_color_index = (
                    download_color_index + 1) % len(COLOR_THEMES)
                upload_color_index = (
                    upload_color_index + 1) % len(COLOR_THEMES)

        time.sleep(FRAME_DELAY)


if __name__ == "__main__":
    curses.wrapper(main)
