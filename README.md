<p align="center">
  <img src="icons/tuxpaper.svg" width="120" alt="Tuxpaper Engine">
</p>

<h1 align="center">Tuxpaper Engine</h1>

<p align="center">
  <strong>Animated wallpapers for Linux — browse, tweak, and forget.</strong><br>
  Per-wallpaper settings, multi-monitor support, autostart, and a friendly GUI.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/platform-linux-lightgrey" alt="Linux">
</p>

---

A desktop app that finds your video wallpapers (Steam Workshop or local folders),
lets you preview and apply them, and remembers every tweak you make — even across
reboots and multiple monitors.

---

## 🚀 Install on Pop!\_OS / Ubuntu

Copy and paste the whole block:

```bash
# System dependencies
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv socat \
                    meson ninja-build libmpv-dev pkg-config

# Build and install mpvpaper (not in apt)
git clone https://github.com/GhostNaN/mpvpaper /tmp/mpvpaper
cd /tmp/mpvpaper && meson setup build && ninja -C build && sudo ninja -C build install
cd ~ && rm -rf /tmp/mpvpaper

# Clone and launch Tuxpaper Engine
git clone https://github.com/High-Depth/Tuxpaper ~/.local/share/Tuxpaper
chmod +x ~/.local/share/Tuxpaper/run.sh ~/.local/share/Tuxpaper/launcher.sh
~/.local/share/Tuxpaper/run.sh
```

First launch will create a Python virtualenv and install `customtkinter` + `Pillow`
automatically. After that, just run:

```bash
~/.local/share/Tuxpaper/run.sh
```

**Optional** — install a desktop shortcut so it appears in your app menu:

```bash
cd ~/.local/share/Tuxpaper && python3 install_shortcut.py
```

---

## ✨ Features

| Category | What it does |
|----------|-------------|
| **Browse** | Scan Steam Workshop & local folders; thumbnail grid with scroll |
| **Preview** | Live preview of any wallpaper before applying |
| **Scaling** | Stretch, Fit, Fill, or Center — per-wallpaper |
| **Position** | D-pad nudges the wallpaper up/down/left/right |
| **Zoom** | 10%–200% in 5% snap increments |
| **Flip & Rotate** | Mirror horizontally, rotate 90° CW/CCW |
| **Volume** | Slider + mute toggle; auto-unmutes on slider move |
| **Speed** | 0.00x–4.00x playback speed |
| **Pause/Play** | Freeze or resume any wallpaper |
| **Multi-Monitor** | All monitors as one canvas, or individual wallpapers per screen |
| **Persistence** | Every setting saved per wallpaper per monitor — restored on re-select |
| **Autostart** | Boot-time restore: headless mode reapplies last layout |
| **Reset** | Wipe all saved settings for the current wallpaper back to defaults |

---

## 🖥️ Multi-Monitor

Tuxpaper Engine auto-detects your connected displays and lets you choose:

- **All** — one wallpaper spans across every monitor as a single canvas
- **Per Monitor** — pick individual wallpapers for each screen

Each monitor gets its own settings (position, zoom, volume, speed, flip, rotation,
scaling mode). Switch between modes any time — settings are remembered per mode.

On boot, every monitor is restored to its last wallpaper with its saved settings.

---

## 🎮 Usage

### GUI mode

```bash
~/.local/share/Tuxpaper/run.sh
```

### Headless mode (boot / scripting)

Applies the last wallpaper layout without showing the window:

```bash
python3 ~/.local/share/Tuxpaper/tuxpaper.py --headless
```

Toggle **Auto-start on boot** in the GUI to create a login entry that runs
headless mode automatically.

---

## 🎯 Per-Wallpaper Settings

Every wallpaper remembers its own state — per monitor:

- Scaling mode
- Position offset (pan X/Y)
- Zoom level
- Volume %
- Playback speed
- Flip (on/off)
- Rotation (0°/90°/180°/270°)
- Pause state (paused on manual select; playing on boot)

Settings persist as JSON in `~/.config/tuxpaper/` and restore automatically
whenever you re-select a wallpaper.

---

## 📁 Project Structure

```
~/.local/share/Tuxpaper/
├── tuxpaper.py          # Main application
├── launcher.sh          # Launches mpvpaper per monitor
├── run.sh               # User-friendly runner (venv setup + launch)
├── install_shortcut.py  # Desktop entry installer
├── icons/
│   └── tuxpaper.svg     # Application icon
├── requirements.txt     # Python dependencies
└── README.md
```

Config lives in `~/.config/tuxpaper/`:

- `settings.json` — app preferences (default scaling, autostart, monitor mode)
- `last_wallpaper.json` — per-monitor wallpaper restore data
- `wallpaper_settings.json` — per-wallpaper-per-monitor settings
- `sources.json` — enabled wallpaper sources

---

## 📄 License

MIT — do what you like.
