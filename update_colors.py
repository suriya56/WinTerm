#!/usr/bin/env python3
"""
Update fastfetch config, Windows Terminal and WezTerm colors with pywal colors.
Run this script whenever your wallpaper changes.
"""

import glob
import json
import os
import re

PYWAL_COLORS = os.path.join(os.path.expanduser("~"), ".cache", "wal", "colors.json")
FASTFETCH_CONFIG = os.path.join(
    os.path.expanduser("~"), ".config", "fastfetch", "config.jsonc"
)
FASTFETCH_TEMPLATE = os.path.join(
    os.path.expanduser("~"), ".config", "fastfetch", "config.jsonc.template"
)


def get_windows_terminal_settings_path():
    """Find Windows Terminal settings.json path."""
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if not local_appdata:
        return None

    # Windows Terminal settings location
    pattern = os.path.join(
        local_appdata,
        "Packages",
        "Microsoft.WindowsTerminal*_*",
        "LocalState",
        "settings.json",
    )
    matches = glob.glob(pattern)
    return matches[0] if matches else None


def get_wezterm_config_path():
    """Find WezTerm config.lua path."""
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, ".wezterm.lua"),
        os.path.join(home, ".config", "wezterm", "wezterm.lua"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def update_wezterm(colors, special):
    """Update WezTerm config with pywal colors."""
    config_path = get_wezterm_config_path()
    if not config_path:
        print("  WezTerm config not found")
        return False

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"  Error reading WezTerm config: {e}")
        return False

    # Build colors table for WezTerm
    wezterm_colors = {
        "foreground": special.get("foreground", "#FFFFFF"),
        "background": special.get("background", "#000000"),
        "cursor_bg": special.get("cursor", "#FFFFFF"),
        "cursor_fg": special.get("background", "#000000"),
        "selection_bg": special.get("background", "#000000"),
        "selection_fg": special.get("foreground", "#FFFFFF"),
        "ansi": [
            colors.get("color0", "#000000"),
            colors.get("color1", "#FF0000"),
            colors.get("color2", "#00FF00"),
            colors.get("color3", "#FFFF00"),
            colors.get("color4", "#0000FF"),
            colors.get("color5", "#FF00FF"),
            colors.get("color6", "#00FFFF"),
            colors.get("color7", "#FFFFFF"),
        ],
        "brights": [
            colors.get("color8", "#808080"),
            colors.get("color9", "#FF0000"),
            colors.get("color10", "#00FF00"),
            colors.get("color11", "#FFFF00"),
            colors.get("color12", "#0000FF"),
            colors.get("color13", "#FF00FF"),
            colors.get("color14", "#00FFFF"),
            colors.get("color15", "#FFFFFF"),
        ],
    }

    # Generate colors table string
    colors_table = f"""
    ansi = {{
      '{wezterm_colors["ansi"][0]}',
      '{wezterm_colors["ansi"][1]}',
      '{wezterm_colors["ansi"][2]}',
      '{wezterm_colors["ansi"][3]}',
      '{wezterm_colors["ansi"][4]}',
      '{wezterm_colors["ansi"][5]}',
      '{wezterm_colors["ansi"][6]}',
      '{wezterm_colors["ansi"][7]}',
    }},
    brights = {{
      '{wezterm_colors["brights"][0]}',
      '{wezterm_colors["brights"][1]}',
      '{wezterm_colors["brights"][2]}',
      '{wezterm_colors["brights"][3]}',
      '{wezterm_colors["brights"][4]}',
      '{wezterm_colors["brights"][5]}',
      '{wezterm_colors["brights"][6]}',
      '{wezterm_colors["brights"][7]}',
    }},
    foreground = '{wezterm_colors["foreground"]}',
    background = '{wezterm_colors["background"]}',
    cursor_bg = '{wezterm_colors["cursor_bg"]}',
    cursor_fg = '{wezterm_colors["cursor_fg"]}',
    selection_bg = '{wezterm_colors["selection_bg"]}',
    selection_fg = '{wezterm_colors["selection_fg"]}',
"""

    # Check if pywal colorscheme exists
    pywal_marker = "-- PYWAL_COLORS_START"
    if pywal_marker in content:
        # Replace existing pywal colors
        pattern = r"-- PYWAL_COLORS_START.*?-- PYWAL_COLORS_END"
        replacement = f"{pywal_marker}\n    colors = {{{colors_table}    }}\n    -- PYWAL_COLORS_END"
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    else:
        # Add new pywal colors after config = wezterm.config_builder()
        if "config = wezterm.config_builder()" in content:
            content = content.replace(
                "config = wezterm.config_builder()",
                f"config = wezterm.config_builder()\n\n-- Pywal colors\n{pywal_marker}\n    colors = {{{colors_table}    }}\n    -- PYWAL_COLORS_END",
            )
        else:
            # Append before return statement
            content = content.replace(
                "return config",
                f"-- Pywal colors\n{pywal_marker}\n    colors = {{{colors_table}    }}\n    -- PYWAL_COLORS_END\n\nreturn config",
            )

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"  Error writing WezTerm config: {e}")
        return False


def update_windows_terminal(colors, special):
    """Update Windows Terminal color scheme."""
    settings_path = get_windows_terminal_settings_path()
    if not settings_path:
        print("  Windows Terminal settings not found")
        return False

    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
    except Exception as e:
        print(f"  Error reading Windows Terminal settings: {e}")
        return False

    # Create pywal color scheme
    color_scheme = {
        "name": "Pywal",
        "background": special.get("background", "#000000"),
        "foreground": special.get("foreground", "#FFFFFF"),
        "cursorColor": special.get("cursor", "#FFFFFF"),
        "selectionBackground": special.get("background", "#000000"),
        "black": colors.get("color0", "#000000"),
        "red": colors.get("color1", "#FF0000"),
        "green": colors.get("color2", "#00FF00"),
        "yellow": colors.get("color3", "#FFFF00"),
        "blue": colors.get("color4", "#0000FF"),
        "purple": colors.get("color5", "#FF00FF"),
        "cyan": colors.get("color6", "#00FFFF"),
        "white": colors.get("color7", "#FFFFFF"),
        "brightBlack": colors.get("color8", "#808080"),
        "brightRed": colors.get("color9", "#FF0000"),
        "brightGreen": colors.get("color10", "#00FF00"),
        "brightYellow": colors.get("color11", "#FFFF00"),
        "brightBlue": colors.get("color12", "#0000FF"),
        "brightPurple": colors.get("color13", "#FF00FF"),
        "brightCyan": colors.get("color14", "#00FFFF"),
        "brightWhite": colors.get("color15", "#FFFFFF"),
    }

    # Update or add color scheme
    if "schemes" not in settings:
        settings["schemes"] = []

    # Remove existing Pywal scheme if present
    settings["schemes"] = [s for s in settings["schemes"] if s.get("name") != "Pywal"]
    settings["schemes"].append(color_scheme)

    # Set as default for all profiles
    if "profiles" not in settings:
        settings["profiles"] = {"defaults": {}}

    if "defaults" not in settings["profiles"]:
        settings["profiles"]["defaults"] = {}

    settings["profiles"]["defaults"]["colorScheme"] = "Pywal"

    try:
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        return True
    except Exception as e:
        print(f"  Error writing Windows Terminal settings: {e}")
        return False


def main():
    # Load pywal colors
    if not os.path.exists(PYWAL_COLORS):
        print(f"Pywal colors not found at {PYWAL_COLORS}")
        print("Run 'wal -i <wallpaper>' first to generate colors.")
        return

    with open(PYWAL_COLORS, "r") as f:
        pywal = json.load(f)

    colors = pywal.get("colors", {})
    special = pywal.get("special", {})

    # Read template
    template_path = (
        FASTFETCH_TEMPLATE if os.path.exists(FASTFETCH_TEMPLATE) else FASTFETCH_CONFIG
    )
    with open(template_path, "r") as f:
        template = f.read()

    # Substitute color placeholders
    for i in range(1, 10):
        placeholder = f"%color{i}%"
        color_key = f"color{i}"
        color_value = colors.get(color_key, "#FFFFFF")
        template = template.replace(placeholder, color_value)

    # Write updated config
    with open(FASTFETCH_CONFIG, "w") as f:
        f.write(template)

    print("✓ Fastfetch config updated with pywal colors!")
    print(f"  Using colors from: {PYWAL_COLORS}")

    # Update Windows Terminal
    if update_windows_terminal(colors, special):
        print("✓ Windows Terminal color scheme updated!")
        print("  Restart Windows Terminal or open a new tab to see changes.")
    else:
        print("✗ Could not update Windows Terminal")

    # Update WezTerm
    if update_wezterm(colors, special):
        print("✓ WezTerm color scheme updated!")
        print("  WezTerm will reload automatically.")
    else:
        print("✗ Could not update WezTerm")


if __name__ == "__main__":
    main()
