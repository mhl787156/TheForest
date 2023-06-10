# Simple test for NeoPixels on Raspberry Pi
import time
import board
import neopixel

PIN_MAP = {10:board.D10, 12: board.D12, 18: board.D18, 21: board.D21}

class LEDS():

    def __init__(self, gpio_pin, num_pixels, led_groups, base_brightness):
        """
        Assume led_groups is a list of integers which represent the start id of each LED group
        """
        if gpio_pin not in PIN_MAP.keys():
            raise RuntimeError(f"GPIO Pin {gpio_pin} not supported, only {PIN_MAP}")

        self.gpio_pin = PIN_MAP[gpio_pin]
        self.num_pixels = num_pixels
        self.pixel_order = neopixel.GRB
        self.base_brightness = base_brightness

        self.pixels = neopixel.NeoPixel(
            self.gpio_pin, self.num_pixels, 
            brightness=self.base_brightness,
            auto_write=False, pixel_order=self.pixel_order
        )

        self.led_groups = [
            list(range(l1, l2))
            for l1, l2 in zip(led_groups, led_groups[1:])
        ]
        if max(led_groups) < self.num_pixels:
            self.led_groups.append(list(range(max(led_groups), self.num_pixels)))
        print("current groups:", self.led_groups)

    # Helper functions
    def colour_interp_rgb(self, pos):
        # Input a value 0 to 255 to get a color value.
        # The colours are a transition r - g - b - back to r.
        if pos < 0 or pos > 255:
            r = g = b = 0
        elif pos < 85:
            r = int(pos * 3)
            g = int(255 - pos * 3)
            b = 0
        elif pos < 170:
            pos -= 85
            r = int(255 - pos * 3)
            g = 0
            b = int(pos * 3)
        else:
            pos -= 170
            r = 0
            g = int(pos * 3)
            b = int(255 - pos * 3)
        return (r, g, b) if self.pixel_order in (neopixel.RGB, neopixel.GRB) else (r, g, b, 0)

    # Base Pixel Setting Functions
    def set_pixel_colour(self, i, r, g, b, brightness=255):
        """Set Pixel Colour, brightness: [0, 255]"""
        self.pixels[i] = (brightness*r / 255, brightness*g/255, brightness*b/255)

    def fill(self, r, g, b, brightness=255):
        colour = (brightness*r / 255, brightness*g/255, brightness*b/255)
        self.pixels.fill(colour)

    # 
    # Effects
    #
    def clear_group(self, i):
        self.fill_pixel_group(i, 0, 0, 0)

    def fill_group(self, i, r, g, b, brightness=255):
        self.set_pixel_group(self.led_groups[i], r, g, b,brightness=255)

    def fill_pixel_range(self, pixel_list, r,g,b, brightness=255):
        for i in pixel_list:
            self.set_pixel_colour(i, r,g,b, brightness)

    


    
