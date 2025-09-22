import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
# The correct import path from your example
from adafruit_rgb_display import st7735 as st7735r

# --- FINAL Configuration ---
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = digitalio.DigitalInOut(board.D24) # The correct Reset pin from your example
BAUDRATE = 24000000

# Our working backlight code
backlight = digitalio.DigitalInOut(board.D18)
backlight.direction = digitalio.Direction.OUTPUT
backlight.value = True

# Setup SPI bus
spi = board.SPI()

# Create the ST7735R display object using the simple, correct initialization
disp = st7735r.ST7735R(
    spi,
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=BAUDRATE,
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
draw.rectangle((10, 10, width - 20, 20), outline=0, fill="red")
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
draw.text((20, 40), "SUCCESS!", font=font, fill="green")

# Display the image on the screen
disp.image(image)

print("Final test complete. The screen should now be working correctly.")

