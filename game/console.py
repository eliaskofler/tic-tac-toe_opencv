"""Optional raw-mode stdin listener so 'r' can be pressed in the terminal to reset."""
import select
import sys
import termios
import tty


class ConsoleResetListener:
    """When stdin is a real terminal, puts it in cbreak mode so single keypresses (like
    'r' to reset) can be read without waiting for Enter. No-op when stdin isn't a tty."""

    def __init__(self):
        self.enabled = sys.stdin.isatty()
        self._old_settings = None

    def __enter__(self):
        if self.enabled:
            self._old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
            print("Console ready. Press 'r' here to reset the game.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.enabled and self._old_settings is not None:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._old_settings)
        return False

    def reset_requested(self):
        if not self.enabled:
            return False
        if select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.read(1)
            return key.lower() == "r"
        return False
