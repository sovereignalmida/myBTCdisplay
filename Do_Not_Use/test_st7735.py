import board
import digitalio
import displayio
from PIL import Image, ImageDraw, ImageFont
import adafruit_st7735r as st7735r
from adafruit_bus_device import spi_device

# --- Configuration Section for ST7735R ---
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = digitalio.DigitalInOut(board.D27)
BAUDRATE = 24000000

# Configure the backlight pin
backlight = digitalio.DigitalInOut(board.D18)
backlight.direction = digitalio.Direction.OUTPUT
backlight.value = True # Turn backlight on

# --- Create the Display Bus ---
displayio.release_displays()
spi = board.SPI()
spi_dev = spi_device.SPIDevice(spi, cs_pin, baudrate=BAUDRATE)
display_bus = displayio.FourWire(spi_dev, command=dc_pin, reset=reset_pin)

# Create the ST7735R display object
disp = st7735r.ST7735R(
    display_bus,
    width=128,
    height=160,
    bgr=True, 
    rotation=90,
)

# Get the display's dimensions
if disp.rotation % 180 == 90:
    height = disp.width
    width = disp.height
else:
    width = disp.width
    height = disp.height

# Create a blank image for drawing
image = Image.new("RGB", (width, height))
draw = ImageDraw.Draw(image)
draw.rectangle((0, 0, width, height), outline=0, fill="black")

# --- Draw some GFX shapes ---
draw.rectangle((10, 10, width - 10, 20), outline=0, fill="red")
draw.rectangle((10, 30, width - 10, height - 10), outline="green", width=2)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
draw.text((20, 40), "Hello!", font=font, fill="blue")

# Display the image on the screen
disp.image(image)

print("Test complete. The screen should show shapes and text.")
