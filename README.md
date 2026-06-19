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

Built on [`mpvpaper`](https://github.com/GhostNaN/mpvpaper) and [`customtkinter`](https://github.com/TomSchimansky/CustomTkinter).

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
| **Pause/Play** | Freeze or resume the video |
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

## 🚀 Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/Tuxpaper.git
cd Tuxpaper
chmod +x run.sh launcher.sh
./run.sh
```

Install a desktop shortcut to find it in your app menu:

```bash
python3 install_shortcut.py
```

---

## 📦 Requirements

**System packages** (install manually):

- `mpvpaper` — applies the video as your wallpaper
- `socat` — IPC communication with mpv
- `python3` (≥ 3.9)

**Python packages** (auto-installed by `run.sh`):

- `customtkinter` — modern tkinter UI
- `Pillow` — image thumbnails

The launcher script creates a virtualenv and installs these automatically
on first run.

---

## 🎮 Usage

### GUI mode

```bash
./run.sh
```

Or with the alias:

```bash
tuxpaper
```

### Headless mode (boot / scripting)

Applies the last wallpaper layout without showing the window:

```bash
python3 tuxpaper.py --headless
```

The **Auto-start on boot** toggle in the UI creates a desktop entry that runs
headless mode on login.

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
- Pause state (on manual select; plays on boot)

Settings are persisted as JSON in `~/.config/tuxpaper/` and restored
automatically whenever you re-select a wallpaper.

---

## 📁 Project Structure

```
Tuxpaper/
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
