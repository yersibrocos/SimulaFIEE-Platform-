import os

import pygame


DISPLAY_WINDOWED = "windowed"
DISPLAY_WINDOWED_LARGE = "windowed_large"
DISPLAY_FULLSCREEN = "fullscreen"


def get_display_mode():
    mode = os.environ.get("SIMULAFIEE_DISPLAY_MODE", DISPLAY_WINDOWED).lower().strip()
    if mode in {DISPLAY_WINDOWED, DISPLAY_WINDOWED_LARGE, DISPLAY_FULLSCREEN}:
        return mode
    return DISPLAY_WINDOWED


def apply_display_mode(default_size, resizable=False):
    mode = get_display_mode()
    flags = pygame.RESIZABLE if resizable else 0

    if mode == DISPLAY_FULLSCREEN:
        return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    if mode == DISPLAY_WINDOWED_LARGE:
        return pygame.display.set_mode((1600, 900), flags)
    return pygame.display.set_mode(default_size, flags)
