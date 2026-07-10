"""Small reusable easing curves and a color helper used throughout the UI layer."""


def tint(color, amount):
    """Blend color toward white by amount (0 = unchanged, 1 = white)."""
    return tuple(int(c + (255 - c) * amount) for c in color)


def punch_scale(t):
    """t in [0,1]: a quick squash-then-overshoot-then-settle curve for a button-press feel."""
    if t < 0.3:
        return 1.0 - 0.2 * (t / 0.3)
    elif t < 0.6:
        return 0.8 + 0.35 * ((t - 0.3) / 0.3)
    else:
        return 1.15 - 0.15 * ((t - 0.6) / 0.4)


def pop_in_scale(t):
    """t in [0,1]: grows a freshly-placed mark from small, overshoots, then settles at full size."""
    if t < 0.5:
        return 0.2 + 0.9 * (t / 0.5)
    return 1.1 - 0.1 * ((t - 0.5) / 0.5)
