#!/bin/bash
set -e

REPO_URL="https://github.com/High-Depth/Tuxpaper"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/share/Tuxpaper}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}::${NC} $1"; }
ok()    { echo -e "${GREEN}  ✓${NC} $1"; }
warn()  { echo -e "${YELLOW}  ⚠${NC} $1"; }

# -- Detect distro -------------------------------------------------------
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO="$ID"
        DISTRO_LIKE="$ID_LIKE"
    else
        DISTRO="unknown"
        DISTRO_LIKE=""
    fi
}

check_supported() {
    case "$DISTRO" in
        ubuntu|pop|debian|linuxmint|elementary|zorin|kali)
            return 0
            ;;
        *)
            if echo "$DISTRO_LIKE" | grep -qi "debian"; then
                return 0
            fi
            warn "Unrecognized distro: $DISTRO"
            echo "  Tuxpaper expects an apt-based system (Ubuntu, Pop!_OS, Debian, etc.)."
            echo "  You can set INSTALL_DIR and run the manual steps yourself."
            echo ""
            read -rp "Continue anyway? [y/N] " ans
            [[ "$ans" =~ ^[yY] ]] || exit 1
            ;;
    esac
}

# -- Install system dependencies -----------------------------------------
install_deps() {
    info "Installing system dependencies..."
    sudo apt update
    sudo apt install -y git python3 python3-pip python3-venv \
                        socat meson ninja-build libmpv-dev pkg-config \
                        cmake libxrandr-dev libgl-dev libglew-dev \
                        libsdl2-dev libglfw3-dev libpulse-dev \
                        libfftw3-dev libglm-dev
    ok "System dependencies installed"
}

# -- Build & install mpvpaper --------------------------------------------
build_mpvpaper() {
    if command -v mpvpaper &>/dev/null; then
        ok "mpvpaper already installed ($(mpvpaper --version 2>/dev/null || echo 'unknown version'))"
        return
    fi

    info "Building mpvpaper from source..."
    TMPDIR=$(mktemp -d)
    git clone --depth=1 https://github.com/GhostNaN/mpvpaper "$TMPDIR/mpvpaper"
    cd "$TMPDIR/mpvpaper"
    meson setup build
    ninja -C build
    sudo ninja -C build install
    cd /tmp
    rm -rf "$TMPDIR"
    ok "mpvpaper built and installed"
}

# -- Optional: build linux-wallpaperengine (scene/web) --------------------
build_linux_wallpaperengine() {
    if command -v linux-wallpaperengine &>/dev/null; then
        ok "linux-wallpaperengine already installed"
        return
    fi
    echo ""
    read -rp "Build linux-wallpaperengine for scene & web wallpaper support? (requires 8-16 GB RAM, ~30 min) [y/N] " ans
    [[ "$ans" =~ ^[yY] ]] || { warn "Skipped — scene/web wallpapers won't be available"; return; }
    info "Building linux-wallpaperengine (this will take a while)..."
    TMPDIR=$(mktemp -d)
    git clone --recurse-submodules https://github.com/Almamu/linux-wallpaperengine "$TMPDIR/linux-wallpaperengine"
    cd "$TMPDIR/linux-wallpaperengine"
    mkdir build && cd build
    cmake -DCMAKE_BUILD_TYPE=Release ..
    make -j"$(nproc)"
    sudo make install
    sudo ln -sf /opt/linux-wallpaperengine/linux-wallpaperengine /usr/local/bin/
    cd /tmp
    rm -rf "$TMPDIR"
    ok "linux-wallpaperengine built and installed"
}

# -- Clone or update the repo --------------------------------------------
clone_repo() {
    if [ -d "$INSTALL_DIR/.git" ]; then
        info "Updating Tuxpaper Engine..."
        cd "$INSTALL_DIR"
        git pull --ff-only
        ok "Repository updated"
    else
        info "Cloning Tuxpaper Engine..."
        mkdir -p "$(dirname "$INSTALL_DIR")"
        git clone "$REPO_URL" "$INSTALL_DIR"
        ok "Repository cloned"
    fi
}

# -- Python virtual environment ------------------------------------------
setup_venv() {
    info "Setting up Python virtual environment..."
    python3 -m venv "$INSTALL_DIR/venv"
    "$INSTALL_DIR/venv/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt"
    ok "Python dependencies installed"
}

# -- Make scripts executable ---------------------------------------------
make_executable() {
    chmod +x "$INSTALL_DIR/run.sh" "$INSTALL_DIR/launcher.sh" "$INSTALL_DIR/launcher_scene.sh"
    chmod +x "$INSTALL_DIR/install.sh" 2>/dev/null || true
    chmod +x "$INSTALL_DIR/pkg_extractor.py" 2>/dev/null || true
    ok "Scripts made executable"
}

# -- Install desktop shortcut --------------------------------------------
install_shortcut() {
    info "Installing desktop shortcut..."
    "$INSTALL_DIR/venv/bin/python3" "$INSTALL_DIR/install_shortcut.py"
    ok "Desktop shortcut installed"
}

# -- Offer autostart -----------------------------------------------------
offer_autostart() {
    echo ""
    read -rp "Enable autostart (re-apply wallpaper on boot)? [y/N] " ans
    if [[ "$ans" =~ ^[yY] ]]; then
        mkdir -p "$HOME/.config/autostart"
        cat > "$HOME/.config/autostart/tuxpaper.desktop" <<-EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Tuxpaper Engine (Headless)
Comment=Re-apply last wallpaper on boot
Exec=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/tuxpaper.py --headless
Icon=$INSTALL_DIR/icons/tuxpaper.svg
Terminal=false
Categories=
NoDisplay=true
X-GNOME-Autostart-enabled=true
EOF
        chmod 644 "$HOME/.config/autostart/tuxpaper.desktop"
        ok "Autostart enabled"
    fi
}

# -- Run -----------------------------------------------------------------
launch() {
    if [ "${SKIP_LAUNCH:-0}" = "1" ]; then
        echo ""
        info "Install complete. Run '~/.local/share/Tuxpaper/run.sh' to start."
        return
    fi
    echo ""
    info "All set! Launching Tuxpaper Engine..."
    "$INSTALL_DIR/run.sh"
}

# -- Main ----------------------------------------------------------------
main() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     Tuxpaper Engine Installer        ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"
    echo ""

    detect_distro
    check_supported

    # Already in the repo directory?
    if [ -f "./tuxpaper.py" ] && [ -f "./launcher.sh" ]; then
        INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
        info "Installing from local directory: $INSTALL_DIR"
    else
        clone_repo
    fi

    install_deps
    build_mpvpaper
    build_linux_wallpaperengine
    setup_venv
    make_executable
    install_shortcut
    offer_autostart
    launch
}

main "$@"
