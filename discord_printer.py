"""
Discord to receipt printer.

Anything posted in one watched Discord channel prints immediately. Handles
text messages and image attachments.

    python discord_printer.py
"""

import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import io
from datetime import datetime

import requests
import discord
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageWin, ImageFilter
import win32print
import win32ui


DISCORD_TOKEN  = "YOUR_BOT_TOKEN_HERE"   # from the Discord Developer Portal
CHANNEL_ID     = 0                       # right-click the channel -> Copy ID
PRINTER_NAME   = "XP-80C"
FONT_PATH      = "cour.ttf"
FONT_BOLD      = "courbd.ttf"

PRINT_PREFIX   = ""
ALLOWED_USERS  = []
MAX_MSG_LENGTH = 500


PRINTER_DPI  = 203
PAPER_MM     = 80
PAPER_PX     = int(PAPER_MM / 25.4 * PRINTER_DPI)
MARGIN_PX    = 10
TEXT_PX      = PAPER_PX - 2 * MARGIN_PX
FONT_SIZE    = 36
RENDER_SCALE = 4


def load_font(bold=False, size=None):
    size = size or FONT_SIZE
    path = FONT_BOLD if bold else FONT_PATH
    try:
        return ImageFont.truetype(path, size * RENDER_SCALE)
    except OSError:
        return ImageFont.load_default()


def fetch_and_dither_image(url: str, width_px: int = TEXT_PX) -> Image.Image:
    """Download an image, resize to paper width, and Floyd-Steinberg dither to B&W."""
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert("RGB")

    w, h = img.size
    new_h = int(h * width_px / w)
    img = img.resize((width_px, new_h), Image.LANCZOS)

    img = img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(1.8)
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    img = img.convert("1", dither=Image.FLOYDSTEINBERG)
    return img.convert("RGB")


def build_receipt(author: str, content: str, timestamp: datetime,
                  attachment_imgs: list) -> Image.Image:
    S       = RENDER_SCALE
    paper_w = PAPER_PX * S
    margin  = MARGIN_PX * S
    text_w  = TEXT_PX * S
    line_h  = (FONT_SIZE + 6) * S

    font_n  = load_font(bold=False)
    font_b  = load_font(bold=True)
    font_sm = load_font(bold=False, size=FONT_SIZE - 6)
    DIVIDER = "─" * int(text_w / (FONT_SIZE * S * 0.62))

    ops = []
    def add(text, bold=False, align="left", small=False):
        ops.append((text, font_sm if small else (font_b if bold else font_n), align))
    def div(): add(DIVIDER)

    add("STEALER'S CHAT", bold=True, align="center")
    add(timestamp.strftime("%A, %B %d %Y"), align="center", small=True)
    add(timestamp.strftime("@ %I:%M %p"), align="center", small=True)
    div()
    add(f"FROM: {author}", bold=True)
    div()

    if content.strip():
        for paragraph in content.splitlines():
            if not paragraph.strip():
                add(" ")
                continue
            line = ""
            for word in paragraph.split():
                test = (line + " " + word).strip()
                if font_n.getlength(test) <= text_w:
                    line = test
                else:
                    if line: add(line)
                    line = word
            if line: add(line)
        div()

    add("beep boop!", align="center", small=True)

    text_block_h = len(ops) * line_h + line_h * 2
    hi_res = Image.new("RGB", (paper_w, text_block_h), "white")
    draw   = ImageDraw.Draw(hi_res)
    y      = margin // 2

    for text, font, align in ops:
        x = (paper_w - font.getlength(text)) / 2 if align == "center" else margin
        draw.text((x, y), text, font=font, fill="black")
        y += line_h

    text_out_h = int(text_block_h / S)
    output = hi_res.resize((PAPER_PX, text_out_h), Image.LANCZOS)
    output = ImageEnhance.Contrast(output).enhance(2.5).convert("L").convert("RGB")
    output = output.crop((0, 0, PAPER_PX, int(y / S) + 4))

    if attachment_imgs:
        parts = [output]
        for att_img in attachment_imgs:
            gap = Image.new("RGB", (PAPER_PX, 6), "white")
            parts.append(gap)
            parts.append(att_img)

        total_h = sum(p.size[1] for p in parts)
        combined = Image.new("RGB", (PAPER_PX, total_h), "white")
        paste_y = 0
        for p in parts:
            combined.paste(p, (0, paste_y))
            paste_y += p.size[1]
        return combined

    return output


def send_to_printer(img: Image.Image):
    hdc = win32ui.CreateDC()
    hdc.CreatePrinterDC(PRINTER_NAME)
    pw = hdc.GetDeviceCaps(110)
    if img.width != pw:
        img = img.resize((pw, int(img.height * pw / img.width)), Image.LANCZOS)
    hdc.StartDoc("Discord Receipt")
    hdc.StartPage()
    ImageWin.Dib(img).draw(hdc.GetHandleOutput(), (0, 0, img.width, img.height))
    hdc.EndPage()
    hdc.EndDoc()
    hdc.DeleteDC()


def print_receipt(author, content, timestamp, attachment_imgs):
    send_to_printer(build_receipt(author, content, timestamp, attachment_imgs))
   


intents = discord.Intents.default()
intents.message_content = True
client  = discord.Client(intents=intents)

SUPPORTED_IMG_TYPES = (".jpg", ".jpeg", ".png", ".gif", ".webp")

@client.event
async def on_ready():
    print(f" Bot ready: {client.user} — watching channel {CHANNEL_ID}")

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user: return
    if message.channel.id != CHANNEL_ID: return
    if ALLOWED_USERS and message.author.id not in ALLOWED_USERS: return

    content = message.content

    if PRINT_PREFIX:
        if not content.startswith(PRINT_PREFIX): return
        content = content[len(PRINT_PREFIX):].strip()

    image_attachments = [
        a for a in message.attachments
        if any(a.filename.lower().endswith(ext) for ext in SUPPORTED_IMG_TYPES)
    ]

    has_content = content.strip() or image_attachments
    if not has_content: return

    if len(content) > MAX_MSG_LENGTH:
        await message.reply(f"⚠️ Max {MAX_MSG_LENGTH} chars!", delete_after=10)
        return

    print(f"{message.author.display_name}: {content[:60]}"
          + (f" + {len(image_attachments)} image(s)" if image_attachments else ""))

    try:
        def prepare():
            imgs = []
            for att in image_attachments:
                try:
                    imgs.append(fetch_and_dither_image(att.url))
                except Exception as e:
                    print(f"Could not load image {att.filename}: {e}")
            print_receipt(message.author.display_name, content,
                          message.created_at.astimezone(), imgs)

        await asyncio.get_event_loop().run_in_executor(None, prepare)
        await message.add_reaction("🖨️")

    except Exception as e:
        print(f"Error: {e}")
        await message.add_reaction("❌")
        await message.reply(f"⚠️ Print failed: {e}", delete_after=15)

if __name__ == "__main__":
    if DISCORD_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Set DISCORD_TOKEN at the top of the file first.")
        exit(1)
    if not CHANNEL_ID:
        print("Set CHANNEL_ID at the top of the file first.")
        exit(1)
    client.run(DISCORD_TOKEN)
