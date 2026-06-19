#!/bin/bash
# Tuxpaper Engine launcher
# $1 = video path
# $2 = audio flag (1 = audio enabled, 0 = audio disabled)
# $3 = scaling mode (unused here, handled via IPC)
# $4 = monitor name (e.g. "eDP-1", "HDMI-1", or "all")

VIDEO="$1"
AUDIO_FLAG="$2"
MONITOR="${4:-all}"

# Use "all" for all-monitors mode
MPV_OUTPUT="$MONITOR"
if [ "$MONITOR" = "all" ]; then
    MPV_OUTPUT="*"
fi

SOCKET="/tmp/mpvpaper-socket-${MONITOR}"

# Kill only the mpvpaper using this socket path — works for both "all" and per-monitor
pkill -f "input-ipc-server=${SOCKET}" 2>/dev/null || true
sleep 0.2

# Set audio option based on flag
if [ "$AUDIO_FLAG" = "0" ]; then
    AUDIO_OPTION="no-audio"
else
    AUDIO_OPTION=""
fi

MPV_OPTIONS="loop input-ipc-server=${SOCKET}"
if [ -n "$AUDIO_OPTION" ]; then
    MPV_OPTIONS="$AUDIO_OPTION $MPV_OPTIONS"
fi

nohup mpvpaper -o "$MPV_OPTIONS" "$MPV_OUTPUT" "$VIDEO" >/dev/null 2>&1 &

