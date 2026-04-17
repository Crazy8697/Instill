# st7796s.py — ST7796S TFT driver for MicroPython
# 52Pi Pico Breadboard Kit Plus (EP-0172) pinout:
#   CLK  -> GPIO 2
#   MOSI -> GPIO 3
#   CS   -> GPIO 5
#   DC   -> GPIO 6
#   RST  -> GPIO 7
# Resolution: 480x320 landscape (+90°), RGB565

from machine import Pin, SPI
import time

# RGB565 color constants
BLACK  = const(0x0000)
WHITE  = const(0xFFFF)
YELLOW = const(0xFFF0)
RED    = const(0xF800)
GREEN  = const(0x07E0)
BLUE   = const(0x001F)
GRAY   = const(0x8410)

WIDTH  = const(480)
HEIGHT = const(320)


class ST7796S:
    def __init__(self):
        self.spi = SPI(0, baudrate=20_000_000, polarity=0, phase=0,
                       sck=Pin(2), mosi=Pin(3))
        self.cs  = Pin(5, Pin.OUT, value=1)
        self.dc  = Pin(6, Pin.OUT, value=0)
        self.rst = Pin(7, Pin.OUT, value=1)
        self.width  = WIDTH
        self.height = HEIGHT
        self._init()

    # ------------------------------------------------------------------ low level

    def _cmd(self, cmd):
        self.dc(0)
        self.cs(0)
        self.spi.write(bytes([cmd]))
        self.cs(1)

    def _data(self, data):
        self.dc(1)
        self.cs(0)
        self.spi.write(data if isinstance(data, (bytes, bytearray)) else bytes([data]))
        self.cs(1)

    def _cd(self, cmd, data=None):
        self._cmd(cmd)
        if data is not None:
            self._data(data)

    # ------------------------------------------------------------------ init

    def _init(self):
        self.rst(0)
        time.sleep_ms(10)
        self.rst(1)
        time.sleep_ms(120)

        self._cmd(0x01)               # Software reset
        time.sleep_ms(200)
        self._cmd(0x11)               # Sleep out
        time.sleep_ms(500)

        self._cd(0x3A, b'\x55')       # Pixel format: 16-bit RGB565
        self._cd(0x36, b'\x28')       # MADCTL: landscape +90°, BGR
        self._cd(0xC0, b'\x80\x45')   # Power control 1
        self._cd(0xC1, b'\x13')       # Power control 2
        self._cd(0xC2, b'\xA7')       # Power control 3
        self._cd(0xC5, b'\x09')       # VCOM
        self._cd(0xE0, b'\xF0\x06\x0B\x07\x06\x05\x2E\x33\x47\x3A\x17\x16\x2E\x31')  # +gamma
        self._cd(0xE1, b'\xF0\x09\x0D\x09\x08\x23\x2E\x33\x46\x38\x13\x13\x2C\x32')  # -gamma
        self._cmd(0x21)               # INVON (panel is hardware-inverted)
        self._cmd(0x29)               # Display on
        time.sleep_ms(100)

    # ------------------------------------------------------------------ primitives

    def set_window(self, x0, y0, x1, y1):
        self._cmd(0x2A)
        self._data(bytes([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF]))
        self._cmd(0x2B)
        self._data(bytes([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF]))
        self._cmd(0x2C)

    def fill(self, color):
        self.fill_rect(0, 0, self.width, self.height, color)

    def fill_rect(self, x, y, w, h, color):
        if x < 0: w += x; x = 0
        if y < 0: h += y; y = 0
        if x >= self.width or y >= self.height: return
        if x + w > self.width:  w = self.width  - x
        if y + h > self.height: h = self.height - y
        if w <= 0 or h <= 0:
            return
        self.set_window(x, y, x + w - 1, y + h - 1)
        hi = color >> 8
        lo = color & 0xFF
        chunk = bytes([hi, lo] * 64)
        self.dc(1)
        self.cs(0)
        total = w * h
        full, rem = divmod(total, 64)
        for _ in range(full):
            self.spi.write(chunk)
        if rem:
            self.spi.write(bytes([hi, lo] * rem))
        self.cs(1)

    def hline(self, x, y, w, color):
        self.fill_rect(x, y, w, 1, color)

    def vline(self, x, y, h, color):
        self.fill_rect(x, y, 1, h, color)

    def blit_buffer(self, buf, x, y, w, h):
        self.set_window(x, y, x + w - 1, y + h - 1)
        self.dc(1)
        self.cs(0)
        self.spi.write(buf)
        self.cs(1)

    # ------------------------------------------------------------------ text

    def text(self, string, x, y, color=WHITE, bg=BLACK, scale=1):
        """Render string using the built-in 8x8 MicroPython font, scaled up."""
        import framebuf
        fw = 8 * scale
        fh = 8 * scale
        hi_fg = color >> 8;  lo_fg = color & 0xFF
        hi_bg = bg >> 8;     lo_bg = bg & 0xFF
        for i, ch in enumerate(string):
            mono = bytearray(8)
            fb = framebuf.FrameBuffer(mono, 8, 8, framebuf.MONO_HLSB)
            fb.text(ch, 0, 0, 1)
            out = bytearray(fw * fh * 2)
            for row in range(8):
                for col in range(8):
                    on = fb.pixel(col, row)
                    hi = hi_fg if on else hi_bg
                    lo = lo_fg if on else lo_bg
                    for sr in range(scale):
                        for sc in range(scale):
                            idx = ((row * scale + sr) * fw + col * scale + sc) * 2
                            out[idx]     = hi
                            out[idx + 1] = lo
            self.blit_buffer(out, x + i * fw, y, fw, fh)
