"""A tiny synthesizer for simple, chip-tune-ish sound effects, so the game can have
sound everywhere without needing a pile of external audio assets."""
import numpy as np
import pygame

SAMPLE_RATE = 44100


def _envelope(n, fade_in, fade_out):
    """A linear fade-in/out window, to avoid audible clicks at the start/end."""
    env = np.ones(n)
    fi = min(fade_in, n // 2)
    fo = min(fade_out, n // 2)
    if fi > 0:
        env[:fi] = np.linspace(0, 1, fi)
    if fo > 0:
        env[-fo:] = np.linspace(1, 0, fo)
    return env


def tone(freq, duration, wave="sine", fade=0.015):
    """A steady tone at freq Hz for duration seconds."""
    n = int(SAMPLE_RATE * duration)
    t = np.arange(n) / SAMPLE_RATE
    if wave == "square":
        samples = np.sign(np.sin(2 * np.pi * freq * t))
    else:
        samples = np.sin(2 * np.pi * freq * t)
    fade_n = int(SAMPLE_RATE * fade)
    return samples * _envelope(n, fade_n, fade_n)


def sweep(freq_start, freq_end, duration, fade=0.01):
    """A tone that glides from freq_start to freq_end over duration seconds."""
    n = int(SAMPLE_RATE * duration)
    t = np.arange(n) / SAMPLE_RATE
    freq_t = np.linspace(freq_start, freq_end, n)
    phase = 2 * np.pi * np.cumsum(freq_t) / SAMPLE_RATE
    samples = np.sin(phase)
    fade_n = int(SAMPLE_RATE * fade)
    return samples * _envelope(n, fade_n, fade_n)


def silence(duration):
    return np.zeros(int(SAMPLE_RATE * duration))


def to_sound(*waveforms, volume=0.5):
    """Concatenates one or more float waveforms (each in [-1, 1]) into a single
    pygame Sound, matched to the mixer's actual init format."""
    samples = np.concatenate(waveforms) if len(waveforms) > 1 else waveforms[0]
    init = pygame.mixer.get_init()
    if init is None:
        raise RuntimeError("pygame.mixer must be initialized before synthesizing sounds")
    freq, size, channels = init
    amplitude = 2 ** (abs(size) - 1) - 1
    wave = np.clip(samples * volume, -1, 1) * amplitude
    dtype = np.int16 if abs(size) == 16 else np.int8
    wave = wave.astype(dtype)
    if channels == 2:
        wave = np.column_stack([wave, wave])
    return pygame.sndarray.make_sound(np.ascontiguousarray(wave))
