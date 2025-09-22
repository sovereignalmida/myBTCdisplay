import digitalio
import board
from PIL import Image
import adafruit_rgb_display.st7789 as st7789

# --- Configuration Section ---
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = digitalio.DigitalInOut(board.D27) # Correct for the Eye-SPI Beret

BAUDRATE = 24000000

# Configure the backlight pin
backlight = digitalio.DigitalInOut(board.D18)
backlight.direction = digitalio.Direction.OUTPUT
backlight.value = True # Turn backlight on

# Setup SPI bus
spi = board.SPI()

# Create the ST7789 display object using the correct recipe for a 240x240 screen
disp = st7789.ST7789(
    spi,
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=BAUDRATE,
    height=240, 
    y_offset=80,
)

# Set rotation - We'll start with 180 as suggested by the Adafruit example
disp.rotation = 90

# Load an image.
image_path = "/home/casaroot/TBM_LCD_FIXED/images/umbrel_logo.png"

try:
    print(f"Loading image from {image_path}...")
    image = Image.open(image_path)

    # Resize the image to fit the display.
    image = image.resize((disp.width, disp.height))
    
    # Convert to RGB
    image_rgb = image.convert("RGB")
    
    # Display the image.
    disp.image(image_rgb)
    print("Image displayed successfully!")

except FileNotFoundError:
    print(f"ERROR: Image not found at {image_path}")
except Exception as e:
    print(f"An error occurred: {e}")
