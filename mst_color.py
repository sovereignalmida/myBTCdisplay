import time
import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display import st7735 as st7735r
import requests
import json

# --- Configuration ---
RPC_USER = ""
RPC_PASS = "aloha108"
LOGO_PATH = "/home/casaroot/TBM_LCD_FIXED/images/penguinLogo.png"

cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = digitalio.DigitalInOut(board.D24)
BAUDRATE = 24000000

# Backlight control
backlight = digitalio.DigitalInOut(board.D18)
backlight.direction = digitalio.Direction.OUTPUT
backlight.value = True

# Setup SPI bus
spi = board.SPI()

# Create the ST7735R display object
disp = st7735r.ST7735R(
    spi, cs=cs_pin, dc=dc_pin, rst=reset_pin,
    baudrate=BAUDRATE, 
    bgr=True,  # Try False if colors look wrong
    rotation=90, 
    invert=False,  # Changed from True to False
)

# Font settings
font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)

# Define actual colors (RGB tuples)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
ORANGE = (255, 140, 0)  # Bitcoin orange
GREEN = (0, 255, 0)
BLUE = (0, 100, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
CYAN = (0, 255, 255)

# --- Data Fetching Function ---
def get_btc_price(currency="USD"):
    url = "http://192.168.1.116:3002/api/price"
    try:
        response = requests.get(url, auth=(RPC_USER, RPC_PASS), timeout=5)
        response.raise_for_status()
        data = response.json()
        price_value = data.get(currency.lower())
        
        if price_value is not None:
            price_float = float(price_value)
            return f"${price_float:,.0f}"
        else:
            return "Error"
    except (requests.exceptions.RequestException, json.JSONDecodeError):
        return "Error"

# --- Screen Drawing Functions ---

def get_display_dims():
    """Gets the correct width and height based on rotation."""
    if disp.rotation % 180 == 90:
        return disp.height, disp.width
    return disp.width, disp.height

def test_colors():
    """Test function to verify display shows colors correctly."""
    width, height = get_display_dims()
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    
    # Draw colored rectangles
    colors = [RED, GREEN, BLUE, YELLOW]
    labels = ["RED", "GREEN", "BLUE", "YELLOW"]
    section_width = width // 4
    
    for i, (color, label) in enumerate(zip(colors, labels)):
        x = i * section_width
        draw.rectangle((x, 0, x + section_width, height), fill=color)
        # Add label
        draw.text((x + 5, height // 2), label, font=font_small, fill=BLACK)
    
    disp.image(image)
    print("Displaying color test for 5 seconds...")
    time.sleep(5)

def draw_logo_screen():
    """Draws the logo screen with proper color preservation for purple gradient."""
    width, height = get_display_dims()
    
    try:
        # Load the logo directly without initial conversion
        logo_original = Image.open(LOGO_PATH)
        
        # Convert to RGB to ensure color preservation
        # This keeps the purple gradient and white penguin
        if logo_original.mode == 'P':
            # If it's palette mode, convert via RGBA to preserve colors
            logo = logo_original.convert('RGBA').convert('RGB')
        elif logo_original.mode == 'RGBA':
            # If RGBA, composite onto black background to preserve purple
            background = Image.new('RGB', logo_original.size, (0, 0, 0))
            background.paste(logo_original, (0, 0), logo_original)
            logo = background
        else:
            # Otherwise just ensure it's RGB
            logo = logo_original.convert('RGB')
        
        # Create the display image with black background
        image = Image.new('RGB', (width, height), color=(0, 0, 0))
        
        # Calculate the scaling to fit the display while maintaining aspect ratio
        # Leave a small border
        border = 5
        max_width = width - (2 * border)
        max_height = height - (2 * border)
        
        # Calculate scale factor
        scale_w = max_width / logo.width
        scale_h = max_height / logo.height
        scale = min(scale_w, scale_h)
        
        # Calculate new size
        new_width = int(logo.width * scale)
        new_height = int(logo.height * scale)
        
        # Resize using LANCZOS for best quality
        logo_resized = logo.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Calculate position to center the logo
        x = (width - new_width) // 2
        y = (height - new_height) // 2
        
        # Paste the resized logo
        image.paste(logo_resized, (x, y))
        
        # Display the image
        disp.image(image)
        
        print(f"Logo displayed - Original mode: {logo_original.mode}, Size: {logo_original.size}")
        
    except FileNotFoundError:
        # If logo not found, show error message
        image = Image.new('RGB', (width, height), color=(0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, width-1, height-1), outline=RED, width=2)
        draw.text((10, height//2 - 10), "Logo Not Found", font=font_medium, fill=RED)
        disp.image(image)
    except Exception as e:
        # Show any other errors
        print(f"Error loading logo: {e}")
        image = Image.new('RGB', (width, height), color=(0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.text((10, 10), "Logo Error", font=font_medium, fill=RED)
        draw.text((10, 40), str(e)[:25], font=font_small, fill=WHITE)
        disp.image(image)

def draw_price_screen(price):
    """Draws the price and other info onto the display with colors."""
    width, height = get_display_dims()
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    
    # Create gradient-like background effect with rectangles
    draw.rectangle((0, 0, width, height), outline=0, fill=BLACK)
    
    # Draw a subtle border
    draw.rectangle((0, 0, width-1, height-1), outline=BLUE, width=1)
    
    # Draw "BTC Price" label in Bitcoin orange
    title = "BTC Price (USD)"
    title_bbox = draw.textbbox((0, 0), title, font=font_medium)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    draw.text((title_x, 5), title, font=font_medium, fill=ORANGE)
    
    # Draw decorative line under title
    draw.line((10, 30, width-10, 30), fill=ORANGE, width=2)
    
    # Draw the price with color based on status
    if price == "Error":
        price_color = RED
        # Add error indicator
        draw.text((10, height - 40), "⚠", font=font_medium, fill=RED)
    else:
        price_color = GREEN  # Green for successful price fetch
    
    price_bbox = draw.textbbox((0, 0), price, font=font_large)
    price_width = price_bbox[2] - price_bbox[0]
    price_height = price_bbox[3] - price_bbox[1]
    price_x = (width - price_width) // 2
    price_y = (height - price_height) // 2 + 5  # Slightly lower for balance
    
    # Draw price with shadow effect
    draw.text((price_x + 2, price_y + 2), price, font=font_large, fill=(50, 50, 50))  # Shadow
    draw.text((price_x, price_y), price, font=font_large, fill=price_color)
    
    # Draw time in cyan color at bottom
    current_time = time.strftime("%H:%M:%S")
    time_bbox = draw.textbbox((0, 0), current_time, font=font_small)
    time_width = time_bbox[2] - time_bbox[0]
    time_x = (width - time_width) // 2
    draw.text((time_x, height - 20), current_time, font=font_small, fill=CYAN)
    
    # Add small status indicator dots
    indicator_y = height - 10
    if price != "Error":
        draw.ellipse((10, indicator_y, 15, indicator_y + 5), fill=GREEN)  # Connected indicator
    else:
        draw.ellipse((10, indicator_y, 15, indicator_y + 5), fill=RED)  # Error indicator
    
    disp.image(image)

def draw_splash_screen():
    """Draw an initial splash screen with colors."""
    width, height = get_display_dims()
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    
    # Gradient-like effect with rectangles
    for i in range(0, height, 10):
        color_value = int(255 * (1 - i / height))
        color = (0, 0, color_value)  # Blue gradient
        draw.rectangle((0, i, width, i + 10), fill=color)
    
    # Draw title
    title = "BTC Ticker"
    title_bbox = draw.textbbox((0, 0), title, font=font_large)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    draw.text((title_x, height // 2 - 20), title, font=font_large, fill=YELLOW)
    
    # Draw subtitle
    subtitle = "Initializing..."
    subtitle_bbox = draw.textbbox((0, 0), subtitle, font=font_small)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    subtitle_x = (width - subtitle_width) // 2
    draw.text((subtitle_x, height // 2 + 20), subtitle, font=font_small, fill=WHITE)
    
    disp.image(image)

# --- UPDATED Main Loop ---
print("Multi-screen ticker starting. Press Ctrl+C to exit.")

# Show splash screen first
draw_splash_screen()
time.sleep(2)

# Optional: Run color test on first boot (comment out if not needed)
print("Running color test...")
test_colors()

while True:
    try:
        # --- Show Logo Screen ---
        print("Displaying logo screen...")
        draw_logo_screen()
        time.sleep(15)  # Show for 15 seconds
        
        # --- Show Price Screen ---
        print("Displaying price screen...")
        btc_price = get_btc_price("USD")
        print(f"Current Price: {btc_price}")
        draw_price_screen(btc_price)
        time.sleep(45)  # Show for 45 seconds
        
    except KeyboardInterrupt:
        print("\nExiting.")
        # Clear display before exit
        width, height = get_display_dims()
        image = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, width, height), fill=BLACK)
        draw.text((10, height // 2), "Goodbye!", font=font_medium, fill=YELLOW)
        disp.image(image)
        time.sleep(1)
        break
    except Exception as e:
        print(f"An error occurred in the main loop: {e}")
        # Show error on display
        width, height = get_display_dims()
        image = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, width, height), fill=BLACK)
        draw.text((10, 10), "ERROR", font=font_medium, fill=RED)
        draw.text((10, 40), str(e)[:20], font=font_small, fill=WHITE)
        disp.image(image)
        time.sleep(30)
