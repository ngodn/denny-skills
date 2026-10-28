#!/usr/bin/env python3
"""Move the pointer with Hyprland and click or scroll through a temporary uinput mouse.

  pointer.py move X Y
  pointer.py click X Y [--button left|right|middle] [--double]
  pointer.py scroll X Y AMOUNT        (negative scrolls down)

X and Y are global layout pixels (see `hyprctl monitors`), not screenshot pixels.
Needs write access to /dev/uinput; no extra packages.
"""
import argparse, fcntl, os, struct, subprocess, sys, time

UI_SET_EVBIT, UI_SET_KEYBIT, UI_SET_RELBIT = 0x40045564, 0x40045565, 0x40045566
UI_DEV_CREATE, UI_DEV_DESTROY = 0x5501, 0x5502
EV_SYN, EV_KEY, EV_REL = 0, 1, 2
REL_X, REL_Y, REL_WHEEL = 0, 1, 8
BUTTONS = {"left": 0x110, "right": 0x111, "middle": 0x112}


def move(x, y):
    # Hyprland 0.56+ takes Lua dispatchers; older builds take the plain form.
    for cmd in ([f"hl.dsp.cursor.move({{x={x},y={y}}})"], ["movecursor", str(x), str(y)]):
        out = subprocess.run(["hyprctl", "dispatch", *cmd], capture_output=True, text=True).stdout
        if out.strip() == "ok":
            pos = subprocess.run(["hyprctl", "cursorpos"], capture_output=True, text=True).stdout.strip()
            if pos == f"{x}, {y}":
                return
    sys.exit(f"cursor did not reach {x},{y} (last hyprctl output: {out.strip()!r})")


class Mouse:
    def __enter__(self):
        self.fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
        for bit, code in [(UI_SET_EVBIT, EV_KEY), (UI_SET_EVBIT, EV_REL)]:
            fcntl.ioctl(self.fd, bit, code)
        for b in BUTTONS.values():
            fcntl.ioctl(self.fd, UI_SET_KEYBIT, b)
        for r in (REL_X, REL_Y, REL_WHEEL):
            fcntl.ioctl(self.fd, UI_SET_RELBIT, r)
        # struct uinput_user_dev: name[80], input_id, ff_effects_max, abs arrays
        os.write(self.fd, b"agent-pointer".ljust(80, b"\0") + struct.pack("HHHHi", 3, 1, 1, 1, 0) + b"\0" * (4 * 64 * 4))
        fcntl.ioctl(self.fd, UI_DEV_CREATE)
        time.sleep(0.6)  # the compositor needs a moment to pick up the new device
        return self

    def ev(self, t, c, v):
        os.write(self.fd, struct.pack("llHHi", 0, 0, t, c, v))
        if t != EV_SYN:
            os.write(self.fd, struct.pack("llHHi", 0, 0, EV_SYN, 0, 0))

    def __exit__(self, *_):
        time.sleep(0.2)
        fcntl.ioctl(self.fd, UI_DEV_DESTROY)
        os.close(self.fd)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["move", "click", "scroll"])
    p.add_argument("x", type=int)
    p.add_argument("y", type=int)
    p.add_argument("amount", type=int, nargs="?", default=0)
    p.add_argument("--button", choices=BUTTONS, default="left")
    p.add_argument("--double", action="store_true")
    a = p.parse_args()
    move(a.x, a.y)
    if a.action == "move":
        return
    with Mouse() as m:
        if a.action == "scroll":
            for _ in range(abs(a.amount)):
                m.ev(EV_REL, REL_WHEEL, 1 if a.amount > 0 else -1)
                time.sleep(0.03)
            return
        for _ in range(2 if a.double else 1):
            m.ev(EV_KEY, BUTTONS[a.button], 1)
            time.sleep(0.05)
            m.ev(EV_KEY, BUTTONS[a.button], 0)
            time.sleep(0.08)


if __name__ == "__main__":
    main()
