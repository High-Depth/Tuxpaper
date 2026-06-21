#!/usr/bin/env python3
"""Tuxpaper Engine — desktop shortcut installer."""

import os, sys, subprocess

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_DIR = os.path.expanduser("~/.local/share/applications")
DESKTOP_FILE = os.path.join(DESKTOP_DIR, "tuxpaper.desktop")
ICON = os.path.join(PROJECT_DIR, "icons", "tuxpaper.svg")
RUN_SCRIPT = os.path.join(PROJECT_DIR, "run.sh")
REPO_DESKTOP = os.path.join(PROJECT_DIR, "tuxpaper.desktop")


def _write_desktop(path):
    exec_cmd = RUN_SCRIPT
    icon = ICON if os.path.exists(ICON) else "preferences-desktop-wallpaper"

    content = f"""[Desktop Entry]
Version=1.3
Type=Application
Name=Tuxpaper Engine
GenericName=Animated Wallpaper Manager
Comment=Manage and apply animated wallpapers
Exec={exec_cmd}
Icon={icon}
Terminal=false
Categories=Utility;Settings;DesktopSettings;GTK;
Keywords=wallpaper;background;video;animated;mpvpaper;
StartupNotify=true
Path={PROJECT_DIR}
"""

    with open(path, 'w') as f:
        f.write(content)
    os.chmod(path, 0o755)
    print(f"Shortcut created: {path}")


def create_desktop():
    os.makedirs(DESKTOP_DIR, exist_ok=True)
    _write_desktop(DESKTOP_FILE)
    _write_desktop(REPO_DESKTOP)

    try:
        subprocess.run(['update-desktop-database', DESKTOP_DIR],
                       check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def main():
    print("=" * 50)
    print("Tuxpaper Engine — Shortcut Installer")
    print("=" * 50)
    create_desktop()
    print("Done! Look for 'Tuxpaper Engine' in your app menu.")


if __name__ == "__main__":
    main()
