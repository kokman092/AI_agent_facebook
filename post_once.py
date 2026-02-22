import os
import json
import textwrap
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# In GitHub Actions, secrets are passed as env vars directly (no .env file needed)
FACEBOOK_PAGE_ACCESS_TOKEN = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")
FACEBOOK_PAGE_ID = os.environ.get("FACEBOOK_PAGE_ID")
CONTENT_BANK_FILE = "facebook_image_content_bank.jsonl"

def get_next_post_from_bank():
    """Reads the first post from the JSONL bank, removes it, and returns it."""
    try:
        with open(CONTENT_BANK_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if not lines:
            print("Content bank is empty! Run generate_facebook_content.py and commit the file.")
            return None

        next_post = json.loads(lines[0].strip())
        remaining = lines[1:]

        with open(CONTENT_BANK_FILE, "w", encoding="utf-8") as f:
            f.writelines(remaining)

        print(f"Loaded post from bank. {len(remaining)} posts remaining.")
        return next_post

    except FileNotFoundError:
        print(f"{CONTENT_BANK_FILE} not found. Commit it to your GitHub repo!")
        return None
    except Exception as e:
        print(f"Error reading content bank: {e}")
        return None

def create_quote_image(caption_text):
    """Downloads a stock photo and overlays the caption as a quote-style image."""
    print("Creating quote image...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get('https://picsum.photos/1080/1080', headers=headers,
                         allow_redirects=True, timeout=15)
        r.raise_for_status()
        bg = Image.open(BytesIO(r.content)).convert("RGBA")
    except Exception as e:
        print(f"Failed to download background: {e}")
        return None

    # Dark overlay band across center
    overlay = Image.new('RGBA', bg.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = bg.size
    draw.rectangle([0, int(h * 0.2), w, int(h * 0.8)], fill=(0, 0, 0, 170))
    bg = Image.alpha_composite(bg, overlay)

    draw = ImageDraw.Draw(bg)

    # Try system fonts
    font_size = 52
    font = None
    for font_path in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                      "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                      "C:/Windows/Fonts/arialbd.ttf", "arial.ttf"]:
        try:
            font = ImageFont.truetype(font_path, font_size)
            break
        except IOError:
            continue
    if font is None:
        font = ImageFont.load_default()

    wrapped = textwrap.fill(caption_text, width=26)
    bbox = draw.textbbox((0, 0), wrapped, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = (w - tw) / 2, (h - th) / 2

    # Shadow
    draw.text((x + 3, y + 3), wrapped, font=font, fill=(0, 0, 0, 200), align="center")
    # Main text
    draw.text((x, y), wrapped, font=font, fill=(255, 255, 255, 255), align="center")

    output = "temp_post_image.jpg"
    bg.convert("RGB").save(output, "JPEG", quality=95)
    print(f"  Image created: {output} ({os.path.getsize(output) // 1024} KB)")
    return output

def post_image_to_facebook(caption, image_path):
    """Uploads the image to your Facebook Page."""
    if not FACEBOOK_PAGE_ACCESS_TOKEN or not FACEBOOK_PAGE_ID:
        print("Missing FACEBOOK_PAGE_ACCESS_TOKEN or FACEBOOK_PAGE_ID env vars!")
        return False

    url = f"https://graph.facebook.com/v21.0/{FACEBOOK_PAGE_ID}/photos"
    print("Publishing to Facebook...")

    try:
        with open(image_path, 'rb') as img:
            response = requests.post(url,
                data={'message': caption, 'access_token': FACEBOOK_PAGE_ACCESS_TOKEN},
                files={'source': ('post.jpg', img, 'image/jpeg')})
            response.raise_for_status()

        pid = response.json().get('post_id') or response.json().get('id')
        print(f"Posted! Post ID: {pid}")
        os.remove(image_path)
        return True

    except requests.exceptions.HTTPError as e:
        print(f"Facebook API error: {e}")
        if hasattr(e, 'response') and e.response:
            print(e.response.text)
        return False

if __name__ == "__main__":
    print("Facebook AI Agent (GitHub Actions mode) starting...")

    post = get_next_post_from_bank()
    if not post or 'caption' not in post:
        print("No post available. Exiting.")
        exit(1)

    caption = post['caption']
    print(f"Caption: {caption}")

    image_path = create_quote_image(caption)
    if image_path:
        post_image_to_facebook(caption, image_path)
    else:
        print("Failed to create image. Exiting.")
        exit(1)
