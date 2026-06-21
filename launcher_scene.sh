#!/bin/bash
# Tuxpaper Engine scene wallpaper launcher
# $1 = folder path (workshop item folder containing project.json + scene.pkg)
# $2 = monitor name (e.g. "eDP-1")
# $3 = scaling mode (stretch, fit, fill, default)
# $4 = audio flag (1 = enabled, 0 = disabled)
# $5 = volume (0-100)

FOLDER="$1"
MONITOR="$2"
SCALING="${3:-fit}"
AUDIO_FLAG="${4:-1}"
VOLUME="${5:-100}"

if ! command -v linux-wallpaperengine &>/dev/null; then
    echo "linux-wallpaperengine not found"
    exit 1
fi

# Kill any existing linux-wallpaperengine for this monitor
pkill -f "linux-wallpaperengine.*--screen-root ${MONITOR}" 2>/dev/null || true
sleep 0.5

# Build command
CMD=("linux-wallpaperengine" "--screen-root" "$MONITOR" "--bg" "$FOLDER")

# Scaling (center -> fit, linux-wallpaperengine doesn't support center)
if [ "$SCALING" = "center" ]; then
    SCALING="fit"
fi
if [ "$SCALING" = "free" ]; then
    SCALING="default"
fi
if [ "$SCALING" = "stretch" ] || [ "$SCALING" = "fill" ] || [ "$SCALING" = "default" ] || [ "$SCALING" = "fit" ]; then
    CMD+=("--scaling" "$SCALING")
fi

# Audio
if [ "$AUDIO_FLAG" = "0" ]; then
    CMD+=("--silent")
fi

# Volume
if [ "$VOLUME" -lt 100 ]; then
    CMD+=("--volume" "$VOLUME")
fi

CMD+=("--disable-mouse" "--disable-parallax")
CMD+=("--ipc-file" "/tmp/tuxpaper-${MONITOR}.ctl")

nohup "${CMD[@]}" >/dev/null 2>&1 &
