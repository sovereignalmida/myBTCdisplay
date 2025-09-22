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

def check_logo_colors():
    """Check the actual colors in the logo file."""
    try:
        logo = Image.open(LOGO_PATH).convert('RGB')
        pixels = logo.load()
        
        # Sample center pixel
        x, y = logo.width // 2, logo.height // 2
        color = pixels[x, y]
        print(f"Center pixel RGB: {color}")
        print(f"  R={color[0]}, G={color[1]}, B={color[2]}")
        
        if color[0] > color[2]:
            print("  -> More red than blue (should be purple/magenta)")
        elif color[2] > color[0]:
            print("  -> More blue than red (should be blue/cyan)")
            
    except Exception as e:
        print(f"Error checking colors: {e}")

# Call it before your main loop:
print("Checking logo colors...")
check_logo_colors()

def draw_logo_screen():
    """Draws the logo screen FULL SCREEN with simple purple correction."""
    width, height = get_display_dims()
    
    try:
        # Load the logo
        logo_original = Image.open(LOGO_PATH).convert('RGB')
        
        # Create black background
        display_image = Image.new('RGB', (width, height), (0, 0, 0))
        
        # Calculate sizing - NO MARGIN, FULL SCREEN
        scale = min(width / logo_original.width, height / logo_original.height)
        new_width = int(logo_original.width * scale)
        new_height = int(logo_original.height * scale)
        
        # Resize the logo to fill the screen
        logo_resized = logo_original.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Simple color correction - adjust purple pixels
        pixels = logo_resized.load()
        for y in range(logo_resized.height):
            for x in range(logo_resized.width):
                r, g, b = pixels[x, y]
                
                # If it's purple (blue > red, minimal green)
                if b > r and g < 30 and b > 30:
                    # Convert to "pure purple" - equal red and blue
                    intensity = min(b, 180)  # Cap at 180 to avoid over-saturation
                    pixels[x, y] = (intensity, 0, intensity)
                # Keep white/light pixels as they are
                elif r > 200 and g > 200 and b > 200:
                    pixels[x, y] = (255, 255, 255)
                # Keep black/dark pixels as they are
                elif r < 30 and g < 30 and b < 30:
                    pixels[x, y] = (0, 0, 0)
        
        # Calculate position to center (should be 0,0 or very close if full screen)
        x = (width - new_width) // 2
        y = (height - new_height) // 2
        
        # Paste the logo
        display_image.paste(logo_resized, (x, y))
        
        # Send to display
        disp.image(display_image)
        
        print("Logo displayed FULL SCREEN with perfect purple!")
        
    except Exception as e:
        print(f"Error loading logo: {e}")


def draw_price_screen(price):
    """Draws the price screen with smaller icons and fonts for better fit."""
    width, height = get_display_dims()
    
    try:
        # Try to load background, or create purple gradient if not found
        try:
            background_path = "/home/casaroot/TBM_LCD_FIXED/images/Screen1@288x.png"
            display_image = Image.open(background_path).convert('RGB')
            display_image = display_image.resize((width, height), Image.Resampling.LANCZOS)
            
            # Apply purple correction
            pixels = display_image.load()
            for y in range(display_image.height):
                for x in range(display_image.width):
                    r, g, b = pixels[x, y]
                    if b > r and g < 30 and b > 30:
                        intensity = min(b, 180)
                        pixels[x, y] = (intensity, 0, intensity)
        except:
            # Create purple gradient background if image not found
            display_image = Image.new('RGB', (width, height))
            draw_temp = ImageDraw.Draw(display_image)
            for i in range(height):
                purple_val = int(100 + (i / height) * 28)
                draw_temp.rectangle((0, i, width, i+1), fill=(purple_val, 0, purple_val))
        
        draw = ImageDraw.Draw(display_image)
        
        # SMALLER Icon size
        icon_size = 16  # Reduced from 38
        
        # Load and place Bitcoin icon
        try:
            btc_icon = Image.open("/home/casaroot/TBM_LCD_FIXED/images/bitcoin_seeklogo.png").convert('RGBA')
            btc_icon.thumbnail((icon_size, icon_size), Image.Resampling.LANCZOS)
            display_image.paste(btc_icon, (8, 12), btc_icon if btc_icon.mode == 'RGBA' else None)
        except:
            draw.ellipse((8, 12, 8+icon_size, 12+icon_size), fill=ORANGE)
            draw.text((16, 16), "B", font=font_small, fill=WHITE)
        
        # Load and place Satoshi icon
        try:
            sat_icon = Image.open("/home/casaroot/TBM_LCD_FIXED/images/Satoshi_regular_elipse.png").convert('RGBA')
            sat_icon.thumbnail((icon_size, icon_size), Image.Resampling.LANCZOS)
            y_pos = height // 2 + 8
            display_image.paste(sat_icon, (8, y_pos), sat_icon if sat_icon.mode == 'RGBA' else None)
        except:
            y_pos = height // 2 + 8
            draw.ellipse((8, y_pos, 8+icon_size, y_pos+icon_size), fill=ORANGE)
            draw.text((16, y_pos+4), "S", font=font_small, fill=WHITE)
        
        # Process and display Bitcoin price
        if price != "Error":
            # Clean price string
            price_display = price.replace("$", "").replace(",", "")
            
            # SMALLER Dynamic font sizing for BTC price
            if len(price_display) <= 5:
                btc_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
            elif len(price_display) == 6:
                btc_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            else:
                btc_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            
            # Add commas back for display
            price_with_commas = f"{int(price_display):,}"
            
            # Position BTC price (adjusted for smaller icon)
            btc_x = icon_size + 15
            btc_y = 14
            draw.text((btc_x, btc_y), price_with_commas, font=btc_font, fill=WHITE)
            
            # Draw USD label after price
            price_bbox = draw.textbbox((btc_x, btc_y), price_with_commas, font=btc_font)
            usd_x = price_bbox[2] + 3
            draw.text((usd_x, btc_y + 2), "USD", font=font_small, fill=WHITE)
            
            # Calculate and display Sats per USD
            try:
                price_float = float(price_display)
                sats_per_usd = int(100000000 / price_float)
                sats_str = f"{sats_per_usd:,}"
                
                # SMALLER Dynamic font sizing for Sats
                if len(str(sats_per_usd)) <= 3:
                    sats_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
                elif len(str(sats_per_usd)) <= 4:
                    sats_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
                else:
                    sats_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
                
                # Position Sats value
                sats_x = icon_size + 15
                sats_y = height // 2 + 10
                draw.text((sats_x, sats_y), sats_str, font=sats_font, fill=WHITE)
                
            except:
                draw.text((icon_size + 15, height // 2 + 10), "---", font=font_medium, fill=WHITE)
        else:
            draw.text((icon_size + 15, 15), "Loading...", font=font_medium, fill=YELLOW)
        
        # Draw "SATS / USD" label (bottom left)
        draw.text((10, height - 22), "SATS / USD", font=font_small, fill=WHITE)
        
        # Keep temperature display (bottom right)
        try:
            import subprocess
            temp_result = subprocess.run(['vcgencmd', 'measure_temp'], stdout=subprocess.PIPE, timeout=1)
            temp_string = temp_result.stdout.decode('utf-8')
            temp = temp_string.replace("temp=","").replace("'C","").strip()
            temperature = f"{int(float(temp))}°C"
            draw.text((width - 38, height - 22), temperature, font=font_small, fill=WHITE)
        except:
            pass
        
        # Display the complete image
        disp.image(display_image)
        
    except Exception as e:
        print(f"Error in price screen: {e}")

def draw_time_screen():
    """Draws a time and date screen with purple background - no decorative lines."""
    width, height = get_display_dims()
    
    try:
        # Try to load background, or create purple gradient
        try:
            background_path = "/home/casaroot/TBM_LCD_FIXED/images/Screen1@288x.png"
            display_image = Image.open(background_path).convert('RGB')
            display_image = display_image.resize((width, height), Image.Resampling.LANCZOS)
            
            # Apply purple correction
            pixels = display_image.load()
            for y in range(display_image.height):
                for x in range(display_image.width):
                    r, g, b = pixels[x, y]
                    if b > r and g < 30 and b > 30:
                        intensity = min(b, 180)
                        pixels[x, y] = (intensity, 0, intensity)
        except:
            # Create purple gradient background
            display_image = Image.new('RGB', (width, height))
            draw_temp = ImageDraw.Draw(display_image)
            for i in range(height):
                purple_val = int(100 + (i / height) * 28)
                draw_temp.rectangle((0, i, width, i+1), fill=(purple_val, 0, purple_val))
        
        draw = ImageDraw.Draw(display_image)
        
        # Get current date and time
        import datetime
        current_dt = datetime.datetime.now()
        
        # Format time (12-hour with AM/PM)
        time_string = current_dt.strftime('%-I:%M %p')
        
        # Get day of week
        day_string = current_dt.strftime('%A')
        
        # Get month and date
        month_string = current_dt.strftime('%B %-d')
        
        # Get year
        year_string = current_dt.strftime('%Y')
        
        # Define fonts for each element
        time_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        day_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        date_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        
        # Calculate centered positions
        # Time at top
        time_bbox = draw.textbbox((0, 0), time_string, font=time_font)
        time_width = time_bbox[2] - time_bbox[0]
        time_x = (width - time_width) // 2
        draw.text((time_x, 15), time_string, font=time_font, fill=WHITE)
        
        # Day of week in middle
        day_bbox = draw.textbbox((0, 0), day_string, font=day_font)
        day_width = day_bbox[2] - day_bbox[0]
        day_x = (width - day_width) // 2
        draw.text((day_x, height // 2 - 15), day_string, font=day_font, fill=YELLOW)
        
        # Date below day
        month_bbox = draw.textbbox((0, 0), month_string, font=date_font)
        month_width = month_bbox[2] - month_bbox[0]
        month_x = (width - month_width) // 2
        draw.text((month_x, height // 2 + 15), month_string, font=date_font, fill=WHITE)
        
        # Year at bottom
        year_bbox = draw.textbbox((0, 0), year_string, font=date_font)
        year_width = year_bbox[2] - year_bbox[0]
        year_x = (width - year_width) // 2
        draw.text((year_x, height - 30), year_string, font=date_font, fill=CYAN)
        
        # NO DECORATIVE LINES - removed the orange vertical lines
        
        # Display the image
        disp.image(display_image)
        
    except Exception as e:
        print(f"Error in time screen: {e}")

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
    title = "MyBTCBox"
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

while True:
    try:
        # --- Show Logo Screen ---
        print("Displaying logo screen...")
        draw_logo_screen()
        time.sleep(5)  # Show for 10 seconds
        
        # --- Show Price Screen ---
        print("Displaying price screen...")
        btc_price = get_btc_price("USD")
        print(f"Current Price: {btc_price}")
        draw_price_screen(btc_price)
        time.sleep(20)  # Show for 30 seconds
        
        # --- Show Time/Date Screen ---
        print("Displaying time screen...")
        draw_time_screen()
        time.sleep(20)  # Show for 10 seconds
        
        # --- Show Price Screen Again (updated) ---
        print("Displaying price screen...")
        btc_price = get_btc_price("USD")
        print(f"Current Price: {btc_price}")
        draw_price_screen(btc_price)
        time.sleep(20)  # Show for 30 seconds
        
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
        time.sleep(30)
