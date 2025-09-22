import time
import subprocess
import digitalio
import board
from PIL import Image, ImageDraw, ImageFont
import adafruit_rgb_display.st7789 as st7789
import sys

# --- Configuration Section ---

# 1. SPI pin definitions for the Eye-SPI Pi Beret
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)      # CORRECTED PIN for DC
reset_pin = digitalio.DigitalInOut(board.D27)  # CORRECTED PIN for Reset
BAUDRATE = 24000000

# 2. Setup SPI bus
spi = board.SPI()

# 3. Create the ST7789 display object
# This assumes you have a 240x240 pixel display.
disp = st7789.ST7789(
    spi,
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=BAUDRATE,
    width=240,
    height=240,
    x_offset=0,
    y_offset=80, # This might need adjustment (try 0 if text is off-screen)
)

# 4. Display rotation
# Try 0, 90, 180, or 270 to get the correct orientation
disp.rotation = 270

# 5. Font and color settings
font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)
font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
WHITE = "#FFFFFF"
BLACK = "#000000"

# --- Main Functions ---

def get_btc_price(currency="USD"):
    """Fetches the current BTC price in the specified currency."""
    try:
        # Command to get the price from the 'btc-rpc-explorer' Docker container
        cmd = f"docker exec CASA_RPCEXPLORER /usr/bin/node /app/api/price.js {currency}"
        price_str = subprocess.check_output(cmd, shell=True, text=True).strip()
        price_float = float(price_str)
        return f"${price_float:,.0f}" # Format with comma and no decimals
    except Exception as e:
        print(f"Error fetching price: {e}")
        return "Error"

def draw_screen(price):
    """Draws the price and other info onto the display."""
    image = Image.new("RGB", (disp.width, disp.height))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, disp.width, disp.height), outline=0, fill=BLACK)

    # "BTC Price (USD)" - Top
    draw.text((10, 5), "BTC Price (USD)", font=font_medium, fill=WHITE)

    # The Price - Center
    price_bbox = draw.textbbox((0, 0), price, font=font_large)
    price_width = price_bbox[2] - price_bbox[0]
    price_height = price_bbox[3] - price_bbox[1]
    price_x = (disp.width - price_width) // 2
    price_y = (disp.height - price_height) // 2
    draw.text((price_x, price_y), price, font=font_large, fill=WHITE)

    # Current Time - Bottom Left
    current_time = time.strftime("%H:%M:%S")
    draw.text((10, 215), current_time, font=font_small, fill=WHITE)

    # Display the image
    disp.image(image)

# --- Main Loop ---

if __name__ == "__main__":
    currency_code = "USD"
    if len(sys.argv) > 1:
        currency_code = sys.argv[1].upper()

    print("Ticker starting. Press Ctrl+C to exit.")
    print(f"Currency: {currency_code}")

    while True:
        try:
            btc_price = get_btc_price(currency_code)
            print(f"Current Price: {btc_price}")
            draw_screen(btc_price)
            time.sleep(60) # Update every 60 seconds
        except KeyboardInterrupt:
            print("\nExiting.")
            break
        except Exception as e:
            print(f"An error occurred in the main loop: {e}")
            time.sleep(30)
