"""
discord_receipt_bot.py
Friends type in a Discord channel → prints on your XP-80C instantly.
"""

import asyncio
from datetime import datetime

import discord
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageWin
import win32print
import win32ui


DISCORD_TOKEN  = "YOUR_BOT_TOKEN_HERE"   # from Discord Developer Portal
CHANNEL_ID     = 0      # right-click channel → Copy ID
PRINTER_NAME   = "XP-80C"
FONT_PATH      = "cour.ttf"
FONT_BOLD      = "courbd.ttf"

PRINT_PREFIX   = ""   # friends type: !print hello
ALLOWED_USERS  = []          # list of Discord user IDs to whitelist, or [] for everyone
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


def build_receipt(author: str, content: str, timestamp: datetime) -> Image.Image:
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

    total_h = len(ops) * line_h + line_h * 2
    hi_res  = Image.new("RGB", (paper_w, total_h), "white")
    draw    = ImageDraw.Draw(hi_res)
    y       = margin // 2

    for text, font, align in ops:
        x = (paper_w - font.getlength(text)) / 2 if align == "center" else margin
        draw.text((x, y), text, font=font, fill="black")
        y += line_h

    output = hi_res.resize((PAPER_PX, int(total_h / S)), Image.LANCZOS)
    output = ImageEnhance.Contrast(output).enhance(2.5).convert("L").convert("RGB")
    return output.crop((0, 0, PAPER_PX, int(y / S) + 4))


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

def send_cut():
    hp = win32print.OpenPrinter(PRINTER_NAME)
    try:
        win32print.StartDocPrinter(hp, 1, ("Cut", None, "RAW"))
        win32print.StartPagePrinter(hp)
        win32print.WritePrinter(hp, b'\x1b\x64\x03\x1d\x56\x00')
        win32print.EndPagePrinter(hp)
        win32print.EndDocPrinter(hp)
    finally:
        win32print.ClosePrinter(hp)

def print_receipt(author, content, timestamp):
    send_to_printer(build_receipt(author, content, timestamp))
    send_cut()


intents = discord.Intents.default()
intents.message_content = True
client  = discord.Client(intents=intents)

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
        if not content:
            await message.add_reaction("❓"); return

    if len(content) > MAX_MSG_LENGTH:
        await message.reply(f"⚠️ Max {MAX_MSG_LENGTH} chars!", delete_after=10); return

    print(f"{message.author.display_name}: {content[:60]}")
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, print_receipt, message.author.display_name,
            content, message.created_at.astimezone()
        )
        await message.add_reaction("🖨️")
    except Exception as e:
        await message.add_reaction("❌")
        await message.reply(f"⚠️ Print failed: {e}", delete_after=15)

if __name__ == "__main__":
    if DISCORD_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print(" Set DISCORD_TOKEN first!"); exit(1)
    client.run(DISCORD_TOKEN)
