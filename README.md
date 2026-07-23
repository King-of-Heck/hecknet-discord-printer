# Discord Printer

Minimal Discord bot: anything posted in one channel prints straight to an XP-80C.

The minimal version: one watched channel, everything posted in it prints.
Handles text messages and image attachments.

For per-channel templates, work order numbers and scheduled printing, see
[hecknet-discord-templates](https://github.com/King-of-Heck/hecknet-discord-templates).

## Setup

1. Create a bot at the [Discord Developer Portal](https://discord.com/developers/applications),
   enable the Message Content intent, and invite it to your server.
2. Put the token in `DISCORD_TOKEN`. Prefer an environment variable over
   editing the file.
3. Enable Developer Mode in Discord, right-click the channel, Copy ID, and put
   it in `CHANNEL_ID`.

`ALLOWED_USERS` restricts who can trigger a print; leave it empty to allow
anyone in the channel. `MAX_MSG_LENGTH` caps how much text one message can
print.

## Requirements

- Windows. Printing goes through the Win32 GDI API.
- Python 3.10 or later.
- An 80mm thermal printer installed as a Windows printer. Built against an
  XP-80C at 203 DPI; other 80mm printers should work if the DPI matches.

```bash
pip install -r requirements.txt
```

Set `PRINTER_NAME` in `discord_printer.py` to the printer's name as it appears in
Settings > Printers & scanners.

Receipts are rendered as images at 4x and downsampled before printing, which
is what keeps the text dark and legible on a thermal head. Courier is used
throughout; glyphs Courier lacks are composited from Segoe UI Emoji.

## Running

```bash
python discord_printer.py
```

## Versioning

Tagged releases, with the change notes in [CHANGELOG.md](CHANGELOG.md).

## Licence

MIT. See [LICENSE](LICENSE).
