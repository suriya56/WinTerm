#!/usr/bin/env python3
"""Update Zed settings to use Pywal theme."""

import os
import re

zed_settings = os.path.join(os.environ["APPDATA"], "Zed", "settings.json")

with open(zed_settings, "r", encoding="utf-8") as f:
    content = f.read()

# Replace the dark theme setting
content = re.sub(r'"dark":\s*"[^"]*"', '"dark": "Pywal"', content)

with open(zed_settings, "w", encoding="utf-8") as f:
    f.write(content)

print("✓ Zed theme set to Pywal")
print("  Restart Zed to apply the theme")
