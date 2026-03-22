#!/usr/bin/env python3
"""
Wallpaper watcher - automatically updates terminal colors when wallpaper changes.
Shows Windows notification on color change.
"""

import ctypes
import glob
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

PYWAL_COLORS = os.path.join(os.path.expanduser("~"), ".cache", "wal", "colors.json")
FASTFETCH_CONFIG = os.path.join(
    os.path.expanduser("~"), ".config", "fastfetch", "config.jsonc"
)
FASTFETCH_TEMPLATE = os.path.join(
    os.path.expanduser("~"), ".config", "fastfetch", "config.jsonc.template"
)
WALLPAPER_CACHE = os.path.join(
    os.path.expanduser("~"), ".config", "fastfetch", ".wallpaper_cache"
)
ZED_THEMES_DIR = os.path.join(
    os.path.expanduser("~"), "AppData", "Roaming", "Zed", "themes"
)
ZED_THEME_FILE = os.path.join(ZED_THEMES_DIR, "pywal_theme.json")

CHECK_INTERVAL = 5  # Check every 5 seconds
LAST_UPDATE_TIME = 0  # Track last update time for debouncing
UPDATE_COOLDOWN = 3  # Minimum seconds between updates


def show_notification(title, message):
    """Show Windows toast notification."""
    try:
        from winotify import Notification

        notif = Notification(
            app_id="Wallpaper Watcher",
            title=title,
            msg=message,
            icon=os.path.join(os.path.dirname(__file__), "icon.ico")
            if os.path.exists(os.path.join(os.path.dirname(__file__), "icon.ico"))
            else None,
        )
        notif.show()
    except:
        # Fallback: use PowerShell notification
        try:
            ps_script = f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

            $template = @"
            <toast>
                <visual>
                    <binding template="ToastText02">
                        <text id="1">{title}</text>
                        <text id="2">{message}</text>
                    </binding>
                </visual>
            </toast>
"@

            $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
            $xml.LoadXml($template)
            $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Wallpaper Watcher").Show($toast)
"""
            subprocess.run(["powershell", "-Command", ps_script], capture_output=True)
        except Exception as e:
            print(f"  Notification failed: {e}")


def get_current_wallpaper():
    """Get current wallpaper path from Windows registry."""
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_READ
        )
        wallpaper, _ = winreg.QueryValueEx(key, "WallPaper")
        winreg.CloseKey(key)
        if wallpaper and os.path.exists(wallpaper):
            return wallpaper
    except Exception as e:
        print(f"  Registry read error: {e}")

    # Fallback: check pywal's last wallpaper
    try:
        if os.path.exists(PYWAL_COLORS):
            with open(PYWAL_COLORS, "r") as f:
                pywal = json.load(f)
                wp = pywal.get("wallpaper")
                if wp and os.path.exists(wp):
                    return wp
    except:
        pass

    return None


def get_file_hash(filepath):
    """Get hash of file to detect changes."""
    if not filepath or not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None


def load_cached_hash():
    """Load cached wallpaper hash."""
    if os.path.exists(WALLPAPER_CACHE):
        with open(WALLPAPER_CACHE, "r") as f:
            return f.read().strip()
    return None


def save_cached_hash(hash_value):
    """Save wallpaper hash to cache."""
    with open(WALLPAPER_CACHE, "w") as f:
        f.write(hash_value)


def get_windows_terminal_settings_path():
    """Find Windows Terminal settings.json path."""
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if not local_appdata:
        return None

    pattern = os.path.join(
        local_appdata,
        "Packages",
        "Microsoft.WindowsTerminal*_*",
        "LocalState",
        "settings.json",
    )
    matches = glob.glob(pattern)
    return matches[0] if matches else None


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

    if "schemes" not in settings:
        settings["schemes"] = []

    settings["schemes"] = [s for s in settings["schemes"] if s.get("name") != "Pywal"]
    settings["schemes"].append(color_scheme)

    if "profiles" not in settings:
        settings["profiles"] = {"defaults": {}}

    if "defaults" not in settings["profiles"]:
        settings["profiles"]["defaults"] = {}

    settings["profiles"]["defaults"]["colorScheme"] = "Pywal"

    try:
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        print("  Windows Terminal config updated (reopen to apply)")
        return True
    except Exception as e:
        print(f"  Error writing Windows Terminal settings: {e}")
        return False


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

    pywal_marker = "-- PYWAL_COLORS_START"
    if pywal_marker in content:
        pattern = r"-- PYWAL_COLORS_START.*?-- PYWAL_COLORS_END"
        replacement = f"{pywal_marker}\n    colors = {{{colors_table}    }}\n    -- PYWAL_COLORS_END"
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    else:
        if "config = wezterm.config_builder()" in content:
            content = content.replace(
                "config = wezterm.config_builder()",
                f"config = wezterm.config_builder()\n\n-- Pywal colors\n{pywal_marker}\n    colors = {{{colors_table}    }}\n    -- PYWAL_COLORS_END",
            )
        else:
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


def update_zed(colors, special):
    """Update Zed editor theme with pywal colors."""
    # Ensure themes directory exists
    os.makedirs(ZED_THEMES_DIR, exist_ok=True)

    # Build Zed theme JSON
    zed_theme = {
        "$schema": "https://zed.dev/schema/theme.json",
        "name": "Pywal",
        "author": "Wallpaper Watcher",
        "themes": [
            {
                "appearance": "dark",
                "style": {
                    "background": special.get("background", "#000000"),
                    "foreground": special.get("foreground", "#FFFFFF"),
                    "border": special.get("background", "#000000"),
                    "border.variant": special.get("foreground", "#FFFFFF"),
                    "editor.foreground": special.get("foreground", "#FFFFFF"),
                    "editor.background": special.get("background", "#000000"),
                    "editor.gutter.background": special.get("background", "#000000"),
                    "editor.subheader.background": special.get("background", "#000000"),
                    "editor.active_line.background": colors.get("color0", "#1a1a1a"),
                    "editor.highlighted_line.background": colors.get(
                        "color4", "#2d2d2d"
                    ),
                    "editor.line_number": colors.get("color8", "#808080"),
                    "editor.active_line_number": special.get("foreground", "#FFFFFF"),
                    "predictive": colors.get("color8", "#808080"),
                    "hint": colors.get("color8", "#808080"),
                    "link_text": colors.get("color4", "#0066cc"),
                    "link_visited": colors.get("color5", "#9933cc"),
                    "terminal.background": special.get("background", "#000000"),
                    "terminal.foreground": special.get("foreground", "#FFFFFF"),
                    "terminal.bright_foreground": special.get("foreground", "#FFFFFF"),
                    "terminal.dim_foreground": colors.get("color8", "#808080"),
                    "terminal.black": colors.get("color0", "#000000"),
                    "terminal.red": colors.get("color1", "#FF0000"),
                    "terminal.green": colors.get("color2", "#00FF00"),
                    "terminal.yellow": colors.get("color3", "#FFFF00"),
                    "terminal.blue": colors.get("color4", "#0000FF"),
                    "terminal.magenta": colors.get("color5", "#FF00FF"),
                    "terminal.cyan": colors.get("color6", "#00FFFF"),
                    "terminal.white": colors.get("color7", "#FFFFFF"),
                    "terminal.bright_black": colors.get("color8", "#808080"),
                    "terminal.bright_red": colors.get("color9", "#FF0000"),
                    "terminal.bright_green": colors.get("color10", "#00FF00"),
                    "terminal.bright_yellow": colors.get("color11", "#FFFF00"),
                    "terminal.bright_blue": colors.get("color12", "#0000FF"),
                    "terminal.bright_magenta": colors.get("color13", "#FF00FF"),
                    "terminal.bright_cyan": colors.get("color14", "#00FFFF"),
                    "terminal.bright_white": colors.get("color15", "#FFFFFF"),
                    "terminal.dim_black": colors.get("color0", "#000000"),
                    "terminal.dim_red": colors.get("color1", "#FF0000"),
                    "terminal.dim_green": colors.get("color2", "#00FF00"),
                    "terminal.dim_yellow": colors.get("color3", "#FFFF00"),
                    "terminal.dim_blue": colors.get("color4", "#0000FF"),
                    "terminal.dim_magenta": colors.get("color5", "#FF00FF"),
                    "terminal.dim_cyan": colors.get("color6", "#00FFFF"),
                    "terminal.dim_white": colors.get("color7", "#FFFFFF"),
                    "players": [
                        {
                            "background": colors.get("color4", "#0066cc"),
                            "cursor": special.get("foreground", "#FFFFFF"),
                            "selection": colors.get("color4", "#003366"),
                            "name": colors.get("color4", "#0066cc"),
                        },
                        {
                            "background": colors.get("color5", "#9933cc"),
                            "cursor": special.get("foreground", "#FFFFFF"),
                            "selection": colors.get("color5", "#330066"),
                            "name": colors.get("color5", "#9933cc"),
                        },
                        {
                            "background": colors.get("color6", "#009999"),
                            "cursor": special.get("foreground", "#FFFFFF"),
                            "selection": colors.get("color6", "#003333"),
                            "name": colors.get("color6", "#009999"),
                        },
                    ],
                    "syntax": {
                        "attribute": {"color": colors.get("color4", "#0066cc")},
                        "boolean": {"color": colors.get("color5", "#9933cc")},
                        "comment": {
                            "color": colors.get("color8", "#808080"),
                            "font_style": "italic",
                        },
                        "comment.doc": {
                            "color": colors.get("color8", "#808080"),
                            "font_style": "italic",
                        },
                        "constant": {"color": colors.get("color5", "#9933cc")},
                        "constructor": {"color": colors.get("color4", "#0066cc")},
                        "embedded": {"color": colors.get("color3", "#FFAA00")},
                        "emphasis": {
                            "color": colors.get("color1", "#FF0000"),
                            "font_style": "italic",
                        },
                        "emphasis.strong": {
                            "color": colors.get("color1", "#FF0000"),
                            "font_style": "bold",
                        },
                        "enum": {"color": colors.get("color3", "#FFAA00")},
                        "function": {"color": colors.get("color4", "#0066cc")},
                        "hint": {"color": colors.get("color8", "#808080")},
                        "keyword": {"color": colors.get("color5", "#9933cc")},
                        "label": {"color": colors.get("color5", "#9933cc")},
                        "link_text": {"color": colors.get("color6", "#009999")},
                        "link_uri": {"color": colors.get("color6", "#009999")},
                        "number": {"color": colors.get("color5", "#9933cc")},
                        "operator": {"color": colors.get("color1", "#FF0000")},
                        "parameter": {"color": colors.get("color3", "#FFAA00")},
                        "preproc": {"color": colors.get("color5", "#9933cc")},
                        "punctuation": {"color": colors.get("color7", "#FFFFFF")},
                        "punctuation.bracket": {
                            "color": colors.get("color7", "#FFFFFF")
                        },
                        "punctuation.delimiter": {
                            "color": colors.get("color7", "#FFFFFF")
                        },
                        "punctuation.list_marker": {
                            "color": colors.get("color7", "#FFFFFF")
                        },
                        "punctuation.special": {
                            "color": colors.get("color7", "#FFFFFF")
                        },
                        "string": {"color": colors.get("color2", "#00AA00")},
                        "string.escape": {"color": colors.get("color5", "#9933cc")},
                        "string.regex": {"color": colors.get("color3", "#FFAA00")},
                        "string.special": {"color": colors.get("color3", "#FFAA00")},
                        "string.special.symbol": {
                            "color": colors.get("color5", "#9933cc")
                        },
                        "tag": {"color": colors.get("color1", "#FF0000")},
                        "text.literal": {"color": special.get("foreground", "#FFFFFF")},
                        "title": {"color": colors.get("color4", "#0066cc")},
                        "type": {"color": colors.get("color3", "#FFAA00")},
                        "type.interface": {"color": colors.get("color3", "#FFAA00")},
                        "type.super": {"color": colors.get("color3", "#FFAA00")},
                        "variable": {"color": special.get("foreground", "#FFFFFF")},
                        "variable.member": {
                            "color": special.get("foreground", "#FFFFFF")
                        },
                        "variable.parameter": {
                            "color": colors.get("color3", "#FFAA00")
                        },
                        "variable.special": {"color": colors.get("color1", "#FF0000")},
                    },
                },
            }
        ],
    }

    try:
        with open(ZED_THEME_FILE, "w", encoding="utf-8") as f:
            json.dump(zed_theme, f, indent=2)

        # Also update Zed settings to use Pywal theme
        zed_settings = os.path.join(os.environ["APPDATA"], "Zed", "settings.json")
        if os.path.exists(zed_settings):
            with open(zed_settings, "r", encoding="utf-8") as f:
                settings_content = f.read()
            settings_content = re.sub(
                r'"dark":\s*"[^"]*"', '"dark": "Pywal"', settings_content
            )
            with open(zed_settings, "w", encoding="utf-8") as f:
                f.write(settings_content)

        print("  Zed theme updated")
        return True
    except Exception as e:
        print(f"  Error writing Zed theme: {e}")
        return False


def reload_zed():
    """Note: Zed theme is updated automatically, manual reload required."""
    # Zed CLI doesn't support reload-window on Windows
    # Theme file is already updated by update_zed()
    # User needs to manually reload: Ctrl+Shift+P -> "reload window"
    # This preserves your session (open files, tabs, etc.)
    print("  Zed theme updated (Ctrl+Shift+P → reload window)")
    return True


def send_color_sequences():
    """Send ANSI color sequences to update running terminal sessions."""
    if not os.path.exists(PYWAL_COLORS):
        return False

    try:
        with open(PYWAL_COLORS, "r") as f:
            pywal = json.load(f)

        colors = pywal.get("colors", {})
        special = pywal.get("special", {})

        seq = []
        seq.append(f"\033]11;{special.get('background', '#000000')}\007")
        seq.append(f"\033]10;{special.get('foreground', '#ffffff')}\007")
        seq.append(f"\033]12;{special.get('cursor', '#ffffff')}\007")

        for i in range(16):
            color_key = f"color{i}"
            color_val = colors.get(color_key, "#000000")
            seq.append(f"\033]4;{i};{color_val}\007")

        seq_file = os.path.join(os.path.dirname(PYWAL_COLORS), "sequences")
        with open(seq_file, "w") as f:
            f.write("".join(seq))

        try:
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            written = ctypes.c_ulong()
            full_seq = "".join(seq)
            kernel32.WriteConsoleA(
                handle, full_seq, len(full_seq), ctypes.byref(written), None
            )
        except:
            pass

        print("  Sent color sequences")
        return True
    except Exception as e:
        print(f"  Error sending color sequences: {e}")
        return False


def reload_wezterm():
    """Signal WezTerm to reload config."""
    try:
        result = subprocess.run(
            ["wezterm", "cli", "reload-config"], capture_output=True, timeout=5
        )
        if result.returncode == 0:
            print("  WezTerm reloaded")
            return True
    except:
        pass
    return False


def update_fastfetch():
    """Update fastfetch config and terminals with pywal colors."""
    if not os.path.exists(PYWAL_COLORS):
        print(f"  Pywal colors not found at {PYWAL_COLORS}")
        return False

    try:
        with open(PYWAL_COLORS, "r") as f:
            pywal = json.load(f)

        colors = pywal.get("colors", {})
        special = pywal.get("special", {})

        print(f"  Found {len(colors)} colors")

        template_path = (
            FASTFETCH_TEMPLATE
            if os.path.exists(FASTFETCH_TEMPLATE)
            else FASTFETCH_CONFIG
        )
        with open(template_path, "r") as f:
            template = f.read()

        replacements = 0
        for i in range(1, 10):
            placeholder = f"%color{i}%"
            color_key = f"color{i}"
            color_value = colors.get(color_key, "#FFFFFF")
            if placeholder in template:
                template = template.replace(placeholder, color_value)
                replacements += 1

        with open(FASTFETCH_CONFIG, "w") as f:
            f.write(template)

        print(f"  Updated fastfetch ({replacements} colors)")

        update_windows_terminal(colors, special)
        update_wezterm(colors, special)
        update_zed(colors, special)
        send_color_sequences()
        reload_wezterm()
        reload_zed()

        return True

    except Exception as e:
        print(f"  Error updating: {e}")
        return False


def main():
    print("=" * 50)
    print("👁️  Wallpaper Watcher Started")
    print("=" * 50)
    print(f"Checking every {CHECK_INTERVAL} seconds")
    print(f"Pywal colors: {PYWAL_COLORS}")
    print("Press Ctrl+C to stop\n")

    # Generate initial colors if pywal colors don't exist
    wallpaper = get_current_wallpaper()
    if wallpaper and not os.path.exists(PYWAL_COLORS):
        print("🎨 Generating initial colors...")
        subprocess.run(
            ["wal", "--backend", "haishoku", "-i", wallpaper, "-q"], check=False
        )
        update_fastfetch()
        show_notification("Wallpaper Colors Ready", "Initial colors generated")

    last_hash = load_cached_hash()
    last_wallpaper = None
    last_update_time = 0

    try:
        while True:
            wallpaper = get_current_wallpaper()

            if wallpaper:
                if wallpaper != last_wallpaper:
                    print(f"\n🖼️  Wallpaper changed!")
                    print(f"  Path: {wallpaper}")
                    last_wallpaper = wallpaper

                current_hash = get_file_hash(wallpaper)

                if current_hash and current_hash != last_hash:
                    # Debounce: skip if too soon after last update
                    current_time = time.time()
                    if current_time - last_update_time < UPDATE_COOLDOWN:
                        print(f"  (Skipping - too soon after last update)")
                        time.sleep(CHECK_INTERVAL)
                        continue

                    print(f"\n🎨 Generating new colors...")

                    # Generate new colors with pywal using haishoku backend
                    # (wal backend has ImageMagick issues on Windows)
                    subprocess.run(
                        ["wal", "--backend", "haishoku", "-i", wallpaper, "-q"],
                        check=False,
                    )

                    # Update all configs
                    if update_fastfetch():
                        print("  ✓ Colors updated!")
                        last_update_time = current_time
                        show_notification(
                            "Wallpaper Colors Updated",
                            "Reopen terminals to apply new colors",
                        )
                    else:
                        print("  ✗ Update failed")
                        show_notification(
                            "Update Failed", "Could not update terminal colors"
                        )

                    last_hash = current_hash
                    save_cached_hash(current_hash)

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n👋 Watcher stopped.")


if __name__ == "__main__":
    main()
