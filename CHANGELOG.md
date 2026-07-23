# Changelog

Version numbers were reassigned for release (the old scheme bumped the
minor version for bugfixes); the original number is in parentheses. The
notes below are from each script's own version history.

## 1.1.2  (originally 1.3)

Fixed UnicodeEncodeError on startup: Windows console defaults to cp1252 which
can't encode emoji. Added sys.stdout.reconfigure() to force UTF-8 output so log
lines print correctly in HeckNet Manager.

## 1.1.1  (originally 1.2)

Removed the duplicate cut command, which advanced the paper twice per receipt.

## 1.1.0  (originally 1.1)

Image attachments are printed alongside text.

## 1.0.0  (originally 1.0)

Initial release.

