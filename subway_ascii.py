"""Subway Surfers, but it's a terminal: a tiny auto-playing ASCII endless runner.

Run it in a terminal (`python subway_ascii.py`, q to quit), or embed it: the IDA/Binja plugins
paint Game.render() with Qt, and the Ghidra script runs `python subway_ascii.py --stream` and
paints the frames it prints. Arrow keys / WASD take over from the autopilot for a few seconds.
"""

import os
import queue
import random
import sys
import threading
import time

LANES = 3
LANE_W = 9
WIDTH = LANES * LANE_W
HEIGHT = 20
RUNNER_ROW = HEIGHT - 3
JUMP_STEPS = 4
ROLL_STEPS = 4
MANUAL_STEPS = 120  # how long a keypress keeps the autopilot off
BUSTED_STEPS = 30

TRAIN, BARRIER, OVERHEAD, COIN = "train", "barrier", "overhead", "coin"

# (characters, color) pairs for hosts that colorize; the first and last rendered lines are HUD.
PALETTE = (
    ("┌─┐│▒▓◘└┬┘", "#e05a4f"),  # trains (and the BUSTED box)
    ("●", "#ffd23f"),  # coins
    ("O/\\|()@", "#4fc3f7"),  # runner
    ("▄▀█", "#ff9a3c"),  # barriers
    ("║═", "#6b6b6b"),  # rails and sleepers
    ("·_", "#4a4a4a"),  # gravel and jump shadow
)
HUD_COLOR = "#ffffff"
DEFAULT_COLOR = "#c8c8c8"
_COLOR_OF = {ch: color for chars, color in PALETTE for ch in chars}


def color_of(ch):
    return _COLOR_OF.get(ch, DEFAULT_COLOR)


RUN_FRAMES = ((" O ", "/|\\", "/ \\"), (" O ", "\\|/", "| |"))
JUMP_SPRITE = ("\\O/", " | ", "/ \\")
ROLL_SPRITE = ("(@)",)
KEYS = {"left": "left", "right": "right", "up": "up", "down": "down", "a": "left", "d": "right", "w": "up", "s": "down"}


class Obj:
    __slots__ = ("kind", "lane", "y", "length")

    def __init__(self, kind, lane, y, length=1):
        self.kind, self.lane, self.y, self.length = kind, lane, y, length

    @property
    def front(self):
        return self.y + self.length - 1

    def covers(self, row):
        return self.y <= row <= self.front


class Game:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.reset()

    def reset(self):
        self.objs = []
        self.lane = 1
        self.jump = self.roll = 0
        self.steps = self.score = self.coins = 0
        self.spawn_in = 4
        self.manual = 0
        self.busted = 0

    @property
    def multiplier(self):
        return 1 + min(self.steps // 400, 4)

    def interval_ms(self):
        """Delay until the next step; the game speeds up as you go."""
        return max(45, 110 - self.steps // 40)

    def press(self, key):
        action = KEYS.get(key.strip().lower())
        if action and not self.busted:
            self.manual = MANUAL_STEPS
            self._act(action)

    def _act(self, action):
        if action == "left" and self.lane > 0:
            self.lane -= 1
        elif action == "right" and self.lane < LANES - 1:
            self.lane += 1
        elif action == "up" and not self.jump:
            self.jump, self.roll = JUMP_STEPS, 0
        elif action == "down" and not self.roll:
            self.roll, self.jump = ROLL_STEPS, 0

    def step(self):
        if self.busted:
            self.busted -= 1
            if not self.busted:
                self.reset()
            return
        self.steps += 1
        if self.manual:
            self.manual -= 1
        else:
            self._autopilot()

        for o in self.objs:
            o.y += 1
        self.objs = [o for o in self.objs if o.y < HEIGHT]
        for o in self.objs:
            if o.lane != self.lane or not o.covers(RUNNER_ROW):
                continue
            if o.kind == COIN:
                o.kind = None
                self.coins += 1
                self.score += 10 * self.multiplier
            elif o.kind == TRAIN or (o.kind == BARRIER and not self.jump) or (o.kind == OVERHEAD and not self.roll):
                self.busted = BUSTED_STEPS
                return
        self.objs = [o for o in self.objs if o.kind]

        self.jump = max(0, self.jump - 1)
        self.roll = max(0, self.roll - 1)
        self.score += self.multiplier
        self._spawn()

    def _train_dist(self, lane):
        """Steps until the nearest train in `lane` reaches the runner (0 = alongside, 99 = none)."""
        dist = 99
        for o in self.objs:
            if o.kind == TRAIN and o.lane == lane and o.y < RUNNER_ROW:
                dist = min(dist, max(0, RUNNER_ROW - o.front))
        return dist

    def _autopilot(self):
        def value(lane):
            coins = sum(1 for o in self.objs if o.kind == COIN and o.lane == lane and RUNNER_ROW - 10 <= o.y <= RUNNER_ROW)
            return min(self._train_dist(lane), 14) * 10 + coins

        best = max(range(LANES), key=lambda lane: (value(lane), -abs(lane - self.lane)))
        if value(best) > value(self.lane):
            nxt = self.lane + (1 if best > self.lane else -1)
            if self._train_dist(nxt) > 1:  # don't sidestep into a train's flank
                self.lane = nxt

        for o in self.objs:
            if o.lane == self.lane and o.front == RUNNER_ROW - 1:
                if o.kind == BARRIER and not self.jump:
                    self._act("up")
                elif o.kind == OVERHEAD and not self.roll:
                    self._act("down")

    def _spawn(self):
        self.spawn_in -= 1
        if self.spawn_in > 0:
            return
        lanes = list(range(LANES))
        self.rng.shuffle(lanes)
        pick = self.rng.random()
        height = 1
        if pick < 0.45:  # one or two trains, never all three, coins in a free lane
            n = 1 if self.rng.random() < 0.6 else 2
            height = self.rng.randint(5, 10)
            for lane in lanes[:n]:
                self._add(TRAIN, lane, height)
            self._coins(lanes[n], height)
        elif pick < 0.65:
            for lane in lanes[: self.rng.randint(1, 3)]:
                self._add(BARRIER, lane)
        elif pick < 0.8:
            for lane in lanes[: self.rng.randint(1, 2)]:
                self._add(OVERHEAD, lane)
        else:
            height = self.rng.randint(4, 8)
            self._coins(lanes[0], height)
        self.spawn_in = height + self.rng.randint(4, 7)

    def _add(self, kind, lane, length=1):
        self.objs.append(Obj(kind, lane, -length, length))

    def _coins(self, lane, length):
        for i in range(0, length, 2):
            self._add(COIN, lane)
            self.objs[-1].y -= i

    def render(self):
        grid = [[" "] * WIDTH for _ in range(HEIGHT)]
        for r, row in enumerate(grid):
            for lane in range(LANES):
                x = lane * LANE_W
                if (r - self.steps + lane * 2) % 4 == 0:
                    row[x] = "·"
                row[x + 1] = row[x + 7] = "║"
                if (r - self.steps) % 3 == 0:
                    row[x + 2 : x + 7] = "═════"

        for o in self.objs:
            x = o.lane * LANE_W + 1
            for i in range(o.length):
                r = o.y + i
                if not 0 <= r < HEIGHT:
                    continue
                if o.kind == COIN:
                    grid[r][x + 3] = "●"
                else:
                    grid[r][x : x + 7] = _art(o, i)

        center = self.lane * LANE_W + 4
        if self.roll:
            sprite, top = ROLL_SPRITE, RUNNER_ROW
        elif self.jump:
            sprite, top = JUMP_SPRITE, RUNNER_ROW - 4
            grid[RUNNER_ROW][center] = "_"
        else:
            sprite, top = RUN_FRAMES[(self.steps // 2) % 2], RUNNER_ROW - 2
        for i, line in enumerate(sprite):
            for j, ch in enumerate(line):
                if ch != " ":
                    grid[top + i][center - 1 + j] = ch

        if self.busted:
            box = ("┌───────────────┐", "│   BUSTED!!    │", f"│ score {self.score:07d} │", "└───────────────┘")
            x = (WIDTH - len(box[0])) // 2
            for i, line in enumerate(box):
                grid[HEIGHT // 2 - 2 + i][x : x + len(line)] = line

        hud = f" SCORE {self.score:07d}  x{self.multiplier}  ● {self.coins:03d}"
        footer = " YOU   ←→ lane ↑ jump ↓ roll" if self.manual else " AUTO  ←→↑↓ / WASD to play"
        return "\n".join([hud] + ["".join(row) for row in grid] + [footer])


def _art(o, i):
    if o.kind == BARRIER:
        return "▄▀▄▀▄▀▄"
    if o.kind == OVERHEAD:
        return "█▀▀▀▀▀█"
    if i == 0:
        return "┌─────┐"
    if i == o.length - 1:
        return "└┬───┬┘"
    if i == o.length - 2:
        return "│◘   ◘│"
    return "│▓▒▓▒▓│" if i % 3 == 1 else "│▒▒▒▒▒│"


def _stream_keys(game):
    """--stream mode: the host writes one key name per line to our stdin."""
    keys = queue.SimpleQueue()

    def reader():
        for line in sys.stdin:
            keys.put(line)

    threading.Thread(target=reader, daemon=True).start()

    def poll():
        while not keys.empty():
            game.press(keys.get())

    return poll


def _terminal_keys(game):
    if os.name == "nt":
        import msvcrt

        os.system("")  # enables ANSI escape handling in the Windows console
        arrows = {"K": "left", "M": "right", "H": "up", "P": "down"}

        def poll():
            while msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ("\x00", "\xe0"):
                    ch = arrows.get(msvcrt.getwch(), "")
                if ch == "q":
                    raise KeyboardInterrupt
                game.press(ch)

        return poll

    import atexit
    import select
    import termios
    import tty

    if not sys.stdin.isatty():
        return lambda: None
    fd = sys.stdin.fileno()
    atexit.register(termios.tcsetattr, fd, termios.TCSADRAIN, termios.tcgetattr(fd))
    tty.setcbreak(fd)
    arrows = {"\x1b[D": "left", "\x1b[C": "right", "\x1b[A": "up", "\x1b[B": "down"}

    def poll():
        while select.select([sys.stdin], [], [], 0)[0]:
            ch = os.read(fd, 3).decode(errors="ignore")
            if ch == "q":
                raise KeyboardInterrupt
            game.press(arrows.get(ch, ch))

    return poll


def main():
    stream = "--stream" in sys.argv
    sys.stdout.reconfigure(encoding="utf-8")
    game = Game()
    poll_keys = _stream_keys(game) if stream else _terminal_keys(game)
    if not stream:
        sys.stdout.write("\x1b[2J\x1b[?25l")
    try:
        while True:
            poll_keys()
            game.step()
            # Stream frames end with a form-feed line; terminal frames redraw from the top-left.
            sys.stdout.write(game.render() + "\n\f\n" if stream else "\x1b[H" + game.render())
            sys.stdout.flush()
            time.sleep(game.interval_ms() / 1000)
    except (KeyboardInterrupt, OSError):  # OSError: the host closed our pipe
        pass
    finally:
        if not stream:
            sys.stdout.write("\x1b[?25h\n")


if __name__ == "__main__":
    main()
