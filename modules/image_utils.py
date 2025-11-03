import os
import sys
import glob
from pathlib import Path
from mimetypes import guess_type
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Error: The 'Pillow' library is required. Please install it: pip install Pillow")
    sys.exit(1)

def is_emoji(char):
    """
    Checks if a character is in a common emoji Unicode range.
    This is more reliable than font.getmask().
    """
    # U+1F300 to U+1F5FF (Misc Symbols and Pictographs, includes 🔮 1F52E, 📈 1F4C8, 🔥 1F525, 🔙 1F519)
    if '\U0001F300' <= char <= '\U0001F5FF':
        return True
    # U+1F600 to U+1F64F (Emoticons)
    if '\U0001F600' <= char <= '\U0001F64F':
        return True
    # U+1F900 to U+1F9FF (Supplemental Symbols, includes 🤪 1F92A)
    if '\U0001F900' <= char <= '\U0001F9FF':
        return True
    # U+2600 to U+27BF (Misc Symbols, includes ✅ 2705)
    if '\u2600' <= char <= '\u27BF':
        return True
    # Symbols and Pictographs Extended-A (U+1FA70 to U+1FAFF)
    if '\U0001FA70' <= char <= '\U0001FAFF': 
        return True
    # Add more ranges if needed
    return False

# --- REVISED FUNCTION ---
def find_font(glob_pattern, name_for_log=""):
    """Finds a single font file matching a glob pattern across common system dirs."""
    if not name_for_log: name_for_log = glob_pattern

    # Prioritize specific known paths, especially for system fonts like Apple Emoji
    if glob_pattern == 'Apple Color Emoji.ttc':
        apple_path = '/System/Library/Fonts/Apple Color Emoji.ttc'
        if Path(apple_path).is_file():
            print(f"✅ Found {name_for_log} font at: {apple_path} (Hardcoded path)")
            return apple_path
        # If not found, fall through to search other dirs

    font_dirs_to_search = [
        os.path.expanduser('~/Library/Fonts/'), # Mac User
        '/Library/Fonts/',                      # Mac System
        '/System/Library/Fonts/',               # Mac System
        '/System/Library/Fonts/Core/',          # Mac System (alternate)
        '/usr/share/fonts/',                    # Linux Common
        '/usr/local/share/fonts/',              # Linux Local
        os.path.expanduser('~/.fonts/'),        # Linux User
        'C:\\Windows\\Fonts\\'                  # Windows
    ]

    all_found_fonts = []
    for font_dir in font_dirs_to_search:
        if not Path(font_dir).is_dir(): continue # Skip if dir doesn't exist
        # Use recursive glob (**) to find files in subdirectories
        search_path = os.path.join(font_dir, '**', glob_pattern)
        try:
            # Use Path.glob for better compatibility and handling
            found = list(Path(font_dir).glob(f'**/{glob_pattern}'))
            if found:
                all_found_fonts.extend(str(p) for p in found) # Convert Path objects to strings
        except Exception as e:
            print(f"  ⚠️ Error searching in {font_dir}: {e}") # Log errors during search

    if all_found_fonts:
        all_found_fonts.sort() # Sort for consistency

        # Prioritize Noto Sans Regular if searching for it
        if 'Noto*Sans*Regular' in glob_pattern:
            for f in all_found_fonts:
                if f.endswith('NotoSans-Regular.ttf'):
                    print(f"✅ Found {name_for_log} font at: {f} (Prioritized)")
                    return f
            # If specific regular not found, try any Noto Sans Regular variant
            for f in all_found_fonts:
                 if 'NotoSans' in f and 'Regular' in f and f.endswith('.ttf'):
                      print(f"✅ Found {name_for_log} font at: {f} (Prioritized Variant)")
                      return f

        # Prioritize Noto Color Emoji if searching for it
        if 'Noto*Color*Emoji' in glob_pattern:
            for f in all_found_fonts:
                if 'NotoColorEmoji.ttf' in f: # Exact match preferred
                    print(f"✅ Found {name_for_log} font at: {f} (Prioritized)")
                    return f
            # Fallback to any Noto Color Emoji variant
            for f in all_found_fonts:
                 if 'Noto' in f and 'Color' in f and 'Emoji' in f and f.endswith('.ttf'):
                      print(f"✅ Found {name_for_log} font at: {f} (Prioritized Variant)")
                      return f

        # If no priority match or not searching for priority fonts, use the first found
        font_path = all_found_fonts[0]
        print(f"✅ Found {name_for_log} font at: {font_path} (First match)")
        return font_path

    print(f"⚠️ WARNING: Could not find any {name_for_log} font for pattern '{glob_pattern}'")
    return None

# --- REVISED FUNCTION ---

def draw_text_with_fallback(draw, xy, text, fill, text_font, emoji_font_path, font_size):
    """Draws text char-by-char, trying emoji font if needed."""
    current_x = xy[0]
    y_pos = xy[1]
    emoji_font_instance = None # Lazy load emoji font

    # Attempt to load the emoji font instance ONCE if needed and possible
    # We try loading at the target size first, then fallback to 96 if that specific error occurs
    def get_emoji_font():
        nonlocal emoji_font_instance
        if emoji_font_instance or not emoji_font_path:
            return emoji_font_instance

        font_index = 0 # Assume first font in collection if .ttc/.otc
        try:
            emoji_font_instance = ImageFont.truetype(emoji_font_path, size=font_size, index=font_index)
        except (IOError, OSError) as e:
            if "invalid pixel size" in str(e).lower(): # Specific FreeType error
                try:
                    print(f"  ℹ️ Emoji font size {font_size} invalid, trying fallback size 96...")
                    emoji_font_instance = ImageFont.truetype(emoji_font_path, size=96, index=font_index)
                except (IOError, OSError) as e2:
                    print(f"  ❌ DEBUG: Failed to load emoji font at size {font_size} AND 96: {e2}")
                    emoji_font_instance = None # Fallback failed
            else:
                print(f"  ❌ DEBUG: Failed to load emoji font '{emoji_font_path}': {e}")
                emoji_font_instance = None # Other error
        except Exception as e: # Catch any other font loading errors
             print(f"  ❌ DEBUG: Unexpected error loading emoji font '{emoji_font_path}': {e}")
             emoji_font_instance = None
        return emoji_font_instance


    for char in text:
        font_to_use = text_font # Default to text font

        if is_emoji(char):
            loaded_emoji_font = get_emoji_font()
            if loaded_emoji_font:
                # Check if the specific emoji glyph exists in the loaded emoji font
                # Using getbbox might be more reliable than getmask across Pillow versions
                try:
                    bbox = loaded_emoji_font.getbbox(char)
                    # A valid bbox is usually (x0, y0, x1, y1) where x0 < x1 or y0 < y1
                    # A zero-width glyph might have x0==x1, check this condition
                    if bbox and (bbox[2] > bbox[0] or bbox[3] > bbox[1]):
                         font_to_use = loaded_emoji_font
                    # else: # Glyph not found or zero-width, keep using text_font (might render tofu)
                         # print(f"  ⚠️ Emoji '{char}' not found or zero-width in emoji font, using text font.")
                except Exception:
                     # print(f"  ⚠️ Error checking glyph for '{char}' in emoji font, using text font.")
                     pass # Keep using text_font on error
            # else: # Emoji font failed to load, keep using text_font

        # Draw the single character
        try:
            draw.text((current_x, y_pos), char, font=font_to_use, fill=fill)
        except Exception as e:
             print(f"  ❌ Error drawing character '{char}': {e}")
             continue # Skip drawing this char if it errors out

        # Increment X position using the font actually used
        try:
            # Use getlength if available (older Pillow)
             advance = font_to_use.getlength(char)
        except AttributeError:
             try:
                  # Use getbbox otherwise (newer Pillow)
                  bbox = font_to_use.getbbox(char)
                  # Advance is the width from the bounding box
                  advance = bbox[2] - bbox[0] if bbox else 0
             except Exception:
                  advance = font_size * 0.6 # Estimate if getbbox also fails
        except Exception:
             advance = font_size * 0.6 # General fallback estimate

        current_x += advance


# --- REVISED FUNCTION ---

def create_scrolling_gif(
    text,
    output_filename="post.gif",
    width=1200,
    height=628,
    bg_color="#e7973c", # Orange
    text_color="#FFFFFF" # White
):
    """Generates an animated GIF with scrolling text."""

    print(f"🎨 Starting GIF generation for text: \"{text}\"")
    # --- 1. Setup Fonts ---
    font_size = int(height * 0.15) # Aim for ~94px on 628 height
    print(f"  Target font size: {font_size}px")

    # Find font PATHS first
    text_font_path = find_font('*Noto*Sans*Regular*.ttf', "Text")
    emoji_font_path = find_font('Apple Color Emoji.ttc', "Apple Emoji") # Prioritize Apple
    if not emoji_font_path:
        emoji_font_path = find_font('*Noto*Color*Emoji*.ttf', "Noto Emoji") # Fallback to Noto

    text_font = None # Will hold the loaded ImageFont object

    # Load the primary text font
    try:
        if text_font_path:
            text_font = ImageFont.truetype(text_font_path, size=font_size)
            print(f"  Text font loaded: {text_font_path}")
        else:
            print("  ⚠️ Text font path not found. Falling back to Pillow default.")
            text_font = ImageFont.load_default()
            # Default font is small, adjust size estimate - This might not work well
            font_size = 20 # Arbitrary small size for default
    except (IOError, OSError) as e:
        print(f"  ❌ CRITICAL Error loading text font '{text_font_path}': {e}. Falling back to default.")
        text_font = ImageFont.load_default()
        font_size = 20
    except Exception as e:
         print(f"  ❌ CRITICAL Unexpected error loading text font '{text_font_path}': {e}. Falling back to default.")
         text_font = ImageFont.load_default()
         font_size = 20


    if not emoji_font_path:
        print("  ⚠️ No emoji font path found. Emojis may render as '□' (tofu) using the text font.")
        # Emoji font instance will remain None in draw_text_with_fallback

    # --- 2. Calculate Text Dimensions ---
    print("  Calculating text dimensions...")
    total_text_width = 0
    max_char_height = 0
    temp_emoji_font = None # To cache loaded emoji font for measurements

    # Helper to get emoji font for measurement, similar to drawing logic
    def get_emoji_font_for_measure():
        nonlocal temp_emoji_font
        if temp_emoji_font or not emoji_font_path: return temp_emoji_font
        font_index = 0
        try:
            temp_emoji_font = ImageFont.truetype(emoji_font_path, size=font_size, index=font_index)
        except (IOError, OSError) as e:
            if "invalid pixel size" in str(e).lower():
                try: temp_emoji_font = ImageFont.truetype(emoji_font_path, size=96, index=font_index)
                except Exception: temp_emoji_font = None
            else: temp_emoji_font = None
        except Exception: temp_emoji_font = None
        return temp_emoji_font

    for char in text:
        font_used_for_measure = text_font # Assume text font
        char_width = 0
        char_height = 0

        if is_emoji(char):
            loaded_emoji_font = get_emoji_font_for_measure()
            if loaded_emoji_font:
                 # Check if glyph exists before assuming emoji font for measurement
                try:
                    bbox = loaded_emoji_font.getbbox(char)
                    if bbox and (bbox[2] > bbox[0] or bbox[3] > bbox[1]):
                         font_used_for_measure = loaded_emoji_font
                except Exception:
                     pass # Stick with text_font if check fails

        # Get width and height using the determined font
        try:
            bbox = font_used_for_measure.getbbox(char)
            if bbox:
                 char_width = bbox[2] - bbox[0]
                 char_height = bbox[3] - bbox[1]
            else: # Fallback for space or chars with no bbox
                 char_width = font_used_for_measure.getlength(char) if hasattr(font_used_for_measure, 'getlength') else font_size * 0.3
                 char_height = font_size # Estimate height
        except AttributeError: # Fallback for older Pillow getlength
            try:
                char_width = font_used_for_measure.getlength(char)
                char_height = font_size # Estimate height
            except Exception:
                char_width = font_size * 0.6 # Estimate width if all fails
                char_height = font_size
        except Exception as e:
             print(f"    DEBUG: Error getting bbox/length for char '{char}': {e}")
             char_width = font_size * 0.6 # Estimate width
             char_height = font_size     # Estimate height


        total_text_width += char_width
        max_char_height = max(max_char_height, char_height)

    # --- Use calculated dimensions ---
    text_height = max_char_height if max_char_height > 0 else font_size # Use calculated height or estimate
    y_pos = (height - text_height) // 2 # Center vertically based on calculated max height
    gap = width // 3 # Gap between text repetitions
    total_scroll_width = int(total_text_width) + gap
    print(f"  Calculated text width: {total_text_width:.2f}px, max height: {text_height}px")
    print(f"  Total scroll width (text + gap): {total_scroll_width}px")

    # --- 3. Animation Parameters ---
    scroll_speed = 10 # Pixels per frame
    frame_duration_ms = 40 # 40ms = 25 FPS

    if total_scroll_width <= 0:
        print("❌ Error: Calculated total scroll width is zero or negative. Cannot generate animation.")
        return None

    num_frames = total_scroll_width // scroll_speed
    if num_frames <= 0:
        print("❌ Error: Calculated number of frames is zero or less. Increase text length or decrease scroll speed.")
        return None
    frames = []
    print(f"  Animation: {num_frames} frames, {scroll_speed}px/frame, {frame_duration_ms}ms/frame")

    # --- 4. Generate Frames ---
    print(f"⏳ Generating {num_frames} frames...")
    for i in range(num_frames):
        img = Image.new('RGB', (width, height), color=bg_color)
        d = ImageDraw.Draw(img)

        current_x_pos = width - (i * scroll_speed) # Start off-screen right, scroll left

        # Draw the text instance that scrolls across the screen
        draw_text_with_fallback(d, (current_x_pos, y_pos), text, text_color, text_font, emoji_font_path, font_size)

        # Draw the *next* instance of the text following it, separated by the gap
        # Its starting position is current_x_pos + text_width + gap = current_x_pos + total_scroll_width
        draw_text_with_fallback(d, (current_x_pos + total_scroll_width, y_pos), text, text_color, text_font, emoji_font_path, font_size)

        # Draw the *previous* instance if needed (for seamless loop start)
        # Its starting position is current_x_pos - total_scroll_width
        draw_text_with_fallback(d, (current_x_pos - total_scroll_width, y_pos), text, text_color, text_font, emoji_font_path, font_size)


        frames.append(img)
        # Simple progress indicator
        if (i + 1) % (num_frames // 10 or 1) == 0:
            print(f"  ...frame {i+1}/{num_frames}")


    # --- 5. Save the GIF ---
    print(f"💾 Saving GIF as '{output_filename}'...")
    try:
        frames[0].save(
            output_filename,
            save_all=True,
            append_images=frames[1:],
            duration=frame_duration_ms,
            loop=0, # 0 = loop forever
            optimize=True # Try to reduce file size
        )
        print(f"✅ GIF saved successfully!")
        return output_filename
    except Exception as e:
        print(f"❌ Error saving GIF: {e}")
        return None