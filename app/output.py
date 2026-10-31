"""Puts frames on the screen by writing straight to the Linux framebuffer. No desktop, X or GL, so the screen works
on a Pi Zero with only the kernel's display driver."""

from pathlib import Path

import pygame

import clockface

SYS = Path("/sys/class/graphics/fb0")
DEVICE = "/dev/fb0"
_FORMATS = {16: (0xF800, 0x07E0, 0x001F, 0), 32: (0xFF0000, 0x00FF00, 0x0000FF, 0)}


def probe():
    """(width, height, bits per pixel, bytes per row) of fb0, or None until the display driver has it ready."""
    try:
        w, h = (int(v) for v in (SYS / "virtual_size").read_text().strip().split(","))
        return w, h, int((SYS / "bits_per_pixel").read_text()), int((SYS / "stride").read_text())
    except (OSError, ValueError):
        return None


class Framebuffer:

    def __init__(self, width, height, bpp, stride, path=DEVICE):
        if bpp not in _FORMATS:
            raise ValueError(f"unsupported framebuffer depth {bpp}")
        self.width, self.height, self.stride = width, height, stride
        self.frame = pygame.Surface((width, height), 0, bpp, _FORMATS[bpp])
        self.row = width * bpp // 8
        self.file = open(path, "r+b", buffering=0)

    def logical_size(self, rotate):
        """The size to draw at: turned on its side when the TV is."""
        if rotate in (90, 270):
            return self.height, self.width
        return self.width, self.height

    def show(self, surface, rotate):
        self.frame.blit(pygame.transform.rotate(surface, rotate) if rotate else surface, (0, 0))
        data = self.frame.get_buffer().raw
        pitch = self.frame.get_pitch()
        if pitch != self.stride:
            data = b"".join(data[y * pitch:y * pitch + self.row].ljust(self.stride, b"\0")
                            for y in range(self.height))
        self.file.seek(0)
        self.file.write(data)


def logical_surface(size):
    return pygame.Surface(size, 0, 32, clockface.MASKS)
