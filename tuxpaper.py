#!/usr/bin/env python3
"""
Tuxpaper Engine  —  Make your desktop feel alive with animated wallpapers.

Lets you browse, preview, and apply video wallpapers (from Steam Workshop or
your own folders) with per-wallpaper settings, per-monitor support, autostart,
and headless boot. All the heavy lifting is done by mpvpaper under the hood.
"""

import os, json, subprocess, re, glob, math, sys, time
import customtkinter as ctk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk


def truncate_text(text, max_length=40):
    """Chop text down to size and slap an ellipsis on it if it's too long."""
    return text if len(text) <= max_length else text[:max_length - 3] + "..."


class Wallpaper:
    """A single wallpaper — knows its title, where the video lives, and where its preview image lives."""

    def __init__(self, title, file_path, preview_path, folder_path, tags=None, content_rating="Everyone"):
        self.title = title
        self.file_path = file_path
        self.preview_path = preview_path
        self.folder_path = folder_path
        self.tags = [t.lower() for t in (tags or [])]
        self.content_rating = content_rating


class WallpaperScanner:
    """Scans Steam Workshop and local folders for video wallpapers.
    Also handles all the JSON config files behind the scenes."""

    WORKSHOP_PATHS = [
        os.path.expanduser("~/.steam/debian-installation/steamapps/workshop/content/431960"),
        os.path.expanduser("~/.local/share/Steam/steamapps/workshop/content/431960"),
        os.path.expanduser("~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/workshop/content/431960"),
    ]
    VALID_EXTENSIONS = {'.mp4', '.webm'}
    NSFW_TAGS = {
        'nsfw', '18+', 'r18', '18禁', 'explicit',
        'adult only', 'adult content', 'adult only 18+',
        'mature content', 'mature audience',
        'porn', 'porno', 'pornstar', 'pornography', 'pornographic',
        'xxx', 'hardcore', 'softcore',
        'hentai', 'ecchi', 'futanari', 'futa',
        'yaoi', 'yuri', 'shota', 'loli', 'shotacon', 'lolicon',
        'rule34', 'rule 34',
        'nudity', 'nude', 'naked', 'topless', 'bottomless',
        'sexual', 'sexually', 'intercourse', 'penetration',
        'masturbation', 'masturbate', 'ejaculate', 'ejaculation', 'orgasm',
        'blowjob', 'handjob', 'fellatio', 'cunnilingus', 'deepthroat',
        'bukakke', 'gangbang', 'orgy',
        'incest',
        'bdsm', 'fetish',
        'guro', 'ryona',
    }

    @classmethod
    def _config_dir(cls):
        d = os.path.expanduser("~/.config/tuxpaper")
        os.makedirs(d, exist_ok=True)
        return d

    @classmethod
    def get_config_path(cls):
        return os.path.join(cls._config_dir(), "sources.json")

    @classmethod
    def get_settings_path(cls):
        return os.path.join(cls._config_dir(), "settings.json")

    @classmethod
    def get_last_wallpaper_path(cls):
        return os.path.join(cls._config_dir(), "last_wallpaper.json")

    @classmethod
    def get_wallpaper_settings_path(cls):
        return os.path.join(cls._config_dir(), "wallpaper_settings.json")

    @classmethod
    def get_default_config(cls):
        return {"sources": []}

    @classmethod
    def get_default_settings(cls):
        return {
            "default_scaling_mode": "stretch",
            "autostart_enabled": True,
            "restore_last_wallpaper": True,
            "monitor_mode": "all",
        }

    @classmethod
    def load_config(cls):
        path = cls.get_config_path()
        if os.path.exists(path):
            try:
                with open(path, encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        cfg = cls.get_default_config()
        cls.save_config(cfg)
        return cfg

    @classmethod
    def save_config(cls, config):
        try:
            with open(cls.get_config_path(), 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except IOError:
            pass

    @classmethod
    def load_settings(cls):
        path = cls.get_settings_path()
        if os.path.exists(path):
            try:
                with open(path, encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        s = cls.get_default_settings()
        cls.save_settings(s)
        return s

    @classmethod
    def save_settings(cls, settings):
        try:
            with open(cls.get_settings_path(), 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except IOError:
            pass

    @classmethod
    def load_last_wallpaper(cls):
        path = cls.get_last_wallpaper_path()
        if os.path.exists(path):
            try:
                with open(path, encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return None

    @classmethod
    def save_last_wallpaper(cls, info):
        try:
            with open(cls.get_last_wallpaper_path(), 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=2, ensure_ascii=False)
        except IOError:
            pass

    @classmethod
    def _load_all_wallpaper_settings(cls):
        path = cls.get_wallpaper_settings_path()
        if os.path.exists(path):
            try:
                with open(path, encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    @classmethod
    def _save_all_wallpaper_settings(cls, all_settings):
        try:
            with open(cls.get_wallpaper_settings_path(), 'w', encoding='utf-8') as f:
                json.dump(all_settings, f, indent=2, ensure_ascii=False)
        except IOError:
            pass

    @classmethod
    def _settings_key(cls, file_path, monitor):
        """Composite key for per-wallpaper-per-monitor settings."""
        return f"{file_path}::{monitor}"

    @classmethod
    def load_wallpaper_settings(cls, file_path, monitor="all"):
        """Load settings for a wallpaper + monitor combo."""
        all_settings = cls._load_all_wallpaper_settings()
        key = cls._settings_key(file_path, monitor)
        # Try the composite key first
        if key in all_settings:
            return all_settings[key]
        # Fallback: try old-format key (no ::monitor suffix) for migration
        if monitor == "all" and file_path in all_settings:
            return all_settings[file_path]
        return {}

    @classmethod
    def save_wallpaper_settings(cls, file_path, monitor, settings):
        all_settings = cls._load_all_wallpaper_settings()
        key = cls._settings_key(file_path, monitor)
        all_settings[key] = settings
        cls._save_all_wallpaper_settings(all_settings)

    @classmethod
    def clear_wallpaper_settings(cls, file_path, monitor="all"):
        all_settings = cls._load_all_wallpaper_settings()
        key = cls._settings_key(file_path, monitor)
        if key in all_settings:
            del all_settings[key]
        cls._save_all_wallpaper_settings(all_settings)

    @classmethod
    def add_local_source(cls, path):
        config = cls.load_config()
        for source in config["sources"]:
            if source.get("type") == "local_folder" and source.get("path") == path:
                return
        config["sources"].append({"type": "local_folder", "path": path, "enabled": True})
        cls.save_config(config)

    @classmethod
    def get_workshop_path(cls):
        for p in cls.WORKSHOP_PATHS:
            if os.path.exists(p):
                return p
        return cls.WORKSHOP_PATHS[0]

    @classmethod
    def _scan_steam_workshop(cls):
        wallpapers = []
        workshop = cls.get_workshop_path()
        if not os.path.exists(workshop):
            return wallpapers

        for folder_name in os.listdir(workshop):
            folder = os.path.join(workshop, folder_name)
            if not os.path.isdir(folder):
                continue
            project_json = os.path.join(folder, "project.json")
            if not os.path.exists(project_json):
                continue
            try:
                with open(project_json, encoding='utf-8') as f:
                    data = json.load(f)
                if data.get('type', '').lower() in ('scene', 'web'):
                    continue
                title = data.get('title', f'Untitled ({folder_name})')
                file_name = data.get('file', '')
                if not file_name:
                    continue
                ext = os.path.splitext(file_name)[1].lower()
                if ext not in cls.VALID_EXTENSIONS:
                    continue
                file_path = os.path.join(folder, file_name)
                if not os.path.exists(file_path):
                    continue
                preview = None
                for e in ('preview.jpg', 'preview.png', 'preview.gif', 'preview.jpeg'):
                    p = os.path.join(folder, e)
                    if os.path.exists(p):
                        preview = p
                        break
                wallpapers.append(Wallpaper(title, file_path, preview, folder,
                                             tags=data.get('tags'),
                                             content_rating=data.get('contentrating', 'Everyone')))
            except (json.JSONDecodeError, IOError):
                continue
        return wallpapers

    @classmethod
    def _scan_local_folder(cls, folder_path):
        wallpapers = []
        if not os.path.exists(folder_path):
            return wallpapers
        try:
            for file_name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file_name)
                if not os.path.isfile(file_path):
                    continue
                ext = os.path.splitext(file_name)[1].lower()
                if ext not in cls.VALID_EXTENSIONS:
                    continue
                base = os.path.splitext(file_name)[0]
                title = base.replace('_', ' ').replace('-', ' ').title()
                preview = None
                for e in ('.jpg', '.png', '.gif', '.jpeg'):
                    p = os.path.join(folder_path, base + e)
                    if os.path.exists(p):
                        preview = p
                        break
                if not preview:
                    for e in ('preview.jpg', 'preview.png', 'preview.gif', 'preview.jpeg'):
                        p = os.path.join(folder_path, e)
                        if os.path.exists(p):
                            preview = p
                            break
                wallpapers.append(Wallpaper(title, file_path, preview, folder_path))
        except (PermissionError, OSError):
            pass
        return wallpapers

    @classmethod
    def scan_wallpapers(cls):
        wallpapers = []
        for source in cls.load_config().get("sources", []):
            if not source.get("enabled", False):
                continue
            t = source.get("type")
            if t == "steam_workshop":
                wallpapers.extend(cls._scan_steam_workshop())
            elif t == "local_folder":
                p = source.get("path")
                if p and os.path.exists(p):
                    wallpapers.extend(cls._scan_local_folder(p))
        wallpapers.sort(key=lambda w: w.title.lower())
        return wallpapers


class WallpaperManager:
    """Hands the wallpaper over to the launcher script so it stays up even when this app isn't running."""

    @staticmethod
    def kill_all():
        """Nuke every mpvpaper process — useful when switching monitor modes."""
        subprocess.run(["pkill", "-f", "mpvpaper"], capture_output=True)
        time.sleep(0.3)

    @staticmethod
    def apply_wallpaper(video_path, audio_enabled=False, scaling_mode="fit", monitor="all"):
        try:
            launcher = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launcher.sh")
            if not os.path.exists(launcher):
                messagebox.showerror("Error", f"Couldn't find the launcher script:\n{launcher}")
                return False
            subprocess.Popen([launcher, video_path, "1" if audio_enabled else "0", scaling_mode, monitor])
            return True
        except Exception as e:
            print(f"Something went wrong launching the script: {e}")
            return False


class TuxpaperApp(ctk.CTk):
    """The main window — browse wallpapers, preview them, tweak every setting you can think of."""

    def __init__(self, headless=False):
        super().__init__()
        self.settings = WallpaperScanner.load_settings()

        # All the knobs and dials start at a nice neutral default
        self.wallpapers = []
        self.current_wallpaper = None
        self.audio_enabled = False
        self.scaling_mode = self.settings.get("default_scaling_mode", "stretch")
        self.flipped = False
        self.rotation = 0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.pan_increment = 0.02
        self.pan_limit = 2.0
        self.current_speed = 1.0
        self.is_paused = False
        self.zoom_level = 0.0
        self.zoom_percent = 100
        self.volume_level = 100

        # Track pending after() callbacks to cancel on wallpaper switch
        self._pending_callbacks = []

        # Multi-monitor state
        self.monitors = self._detect_monitors()
        self.monitor_mode = self.settings.get("monitor_mode", "all")
        self.selected_monitors = list(self.monitors)  # all selected by default

        if headless:
            self._enable_controls()
            WallpaperManager.kill_all()
            self.auto_apply_last_wallpaper_on_startup()
            self.after(1500, self.destroy)
            return

        self.title("Tuxpaper Engine")
        self.geometry("1000x600")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self._build_ui()

        self._update_scaling_button_states(self.scaling_mode)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        WallpaperManager.kill_all()
        self.load_wallpapers()
        self.auto_apply_last_wallpaper_on_startup()

    # ------------------------------------------------------------------
    #  Monitor detection
    # ------------------------------------------------------------------

    def _detect_monitors(self):
        """Figure out what monitors are connected by parsing xrandr output."""
        try:
            result = subprocess.run(['xrandr', '--query'],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                monitors = []
                for line in result.stdout.split('\n'):
                    if ' connected' in line:
                        m = re.match(r'^(\S+)', line)
                        if m:
                            monitors.append(m.group(1))
                if monitors:
                    return sorted(monitors)
        except Exception:
            pass
        return ["eDP-1"]

    # ------------------------------------------------------------------
    #  UI: the whole layout in one chunk
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # -- Wallpaper grid on the right ---------------------------------
        self.main_panel = ctk.CTkFrame(self, corner_radius=0)
        self.main_panel.grid(row=0, column=1, sticky="nsew")
        self.main_panel.grid_rowconfigure(1, weight=1)
        self.main_panel.grid_columnconfigure(0, weight=1)

        # Search bar
        self.search_frame = ctk.CTkFrame(self.main_panel, fg_color="transparent")
        self.search_frame.grid(row=0, column=0, padx=20, pady=(15, 0), sticky="ew")
        self.search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text="Search wallpapers...",
                                         font=ctk.CTkFont(size=13))
        self.search_entry.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        self.search_entry.bind('<Return>', self._apply_search)

        self.search_btn = ctk.CTkButton(self.search_frame, text="🔍", width=36, height=28,
                                        command=self._apply_search, font=ctk.CTkFont(size=14))
        self.search_btn.grid(row=0, column=1, padx=(0, 3))

        self.clear_search_btn = ctk.CTkButton(self.search_frame, text="✕", width=36, height=28,
                                              command=self._clear_search, font=ctk.CTkFont(size=14))
        self.clear_search_btn.grid(row=0, column=2)

        self.wallpaper_grid = ctk.CTkScrollableFrame(self.main_panel)
        self.wallpaper_grid.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")

        # -- Sidebar on the left (preview + controls) --------------------
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")

        ctk.CTkLabel(self.sidebar, text="Preview",
                     font=ctk.CTkFont(size=20, weight="bold"))\
            .grid(row=0, column=0, padx=20, pady=(15, 5))

        self.preview_frame = ctk.CTkFrame(self.sidebar)
        self.preview_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        self.preview_frame.grid_rowconfigure(0, weight=1)
        self.preview_frame.grid_columnconfigure(0, weight=1)

        self.preview_label = ctk.CTkLabel(self.preview_frame, text="No preview available")
        self.preview_label.grid(row=0, column=0, sticky="nsew")

        self.title_label = ctk.CTkLabel(
            self.sidebar, text="Select a wallpaper",
            font=ctk.CTkFont(size=16, weight="bold"),
            wraplength=200, justify="center")
        self.title_label.grid(row=2, column=0, padx=20, pady=(5, 8), sticky="ew")

        # -- Monitor selection -------------------------------------------
        self.monitor_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.monitor_frame.grid(row=3, column=0, padx=20, pady=(0, 5), sticky="ew")
        self.monitor_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.monitor_frame, text="Display:",
                     font=ctk.CTkFont(size=12, weight="bold"))\
            .grid(row=0, column=0, columnspan=2, padx=0, pady=(0, 3), sticky="w")

        self.monitor_mode_selector = ctk.CTkSegmentedButton(
            self.monitor_frame, values=["All", "Per Monitor"],
            command=self._on_monitor_mode_change, font=ctk.CTkFont(size=12))
        self.monitor_mode_selector.grid(row=1, column=0, columnspan=2, padx=0, pady=2, sticky="ew")
        self.monitor_mode_selector.set("All" if self.monitor_mode == "all" else "Per Monitor")

        # Per-monitor toggle buttons (hidden when in All mode)
        self.monitor_btn_frame = ctk.CTkFrame(self.monitor_frame, fg_color="transparent")
        self.monitor_btn_frame.grid(row=2, column=0, columnspan=2, padx=0, pady=2, sticky="ew")

        self.monitor_buttons = {}
        for i, m in enumerate(self.monitors):
            short = m[:10]
            btn = ctk.CTkButton(self.monitor_btn_frame, text=short, height=26,
                                font=ctk.CTkFont(size=11),
                                command=lambda name=m: self._select_monitor(name))
            btn.grid(row=0, column=i, padx=2, pady=1, sticky="ew")
            self.monitor_btn_frame.grid_columnconfigure(i, weight=1)
            self.monitor_buttons[m] = btn

        self._update_monitor_button_states()

        if self.monitor_mode == "all":
            self.monitor_btn_frame.grid_remove()

        self.sidebar.grid_rowconfigure(6, weight=1)

        # -- Sources section ----------------------------------------------
        self.sources_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.sources_frame.grid(row=4, column=0, padx=20, pady=(0, 3), sticky="ew")
        self.sources_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.sources_frame, text="Sources:",
                     font=ctk.CTkFont(size=12, weight="bold"))\
            .grid(row=0, column=0, columnspan=2, padx=0, pady=(0, 2), sticky="w")

        # Steam Workshop toggle
        sources_cfg = WallpaperScanner.load_config().get("sources", [])
        self.steam_enabled = any(
            s.get("type") == "steam_workshop" and s.get("enabled")
            for s in sources_cfg
        )
        self.steam_switch = ctk.CTkSwitch(
            self.sources_frame, text="Steam Workshop",
            command=self._toggle_steam_source, font=ctk.CTkFont(size=12))
        self.steam_switch.grid(row=1, column=0, columnspan=2, padx=0, pady=1, sticky="w")
        if self.steam_enabled:
            self.steam_switch.select()

        # Add folder button
        self.add_folder_btn = ctk.CTkButton(
            self.sources_frame, text="+ Add Folder", height=24,
            command=self._add_local_source, font=ctk.CTkFont(size=11))
        self.add_folder_btn.grid(row=2, column=0, columnspan=2, padx=0, pady=2, sticky="ew")

        # Local folder list
        self.folder_list_frame = ctk.CTkFrame(self.sources_frame, fg_color="transparent")
        self.folder_list_frame.grid(row=3, column=0, columnspan=2, padx=0, pady=0, sticky="ew")
        self._rebuild_folder_list()

        # NSFW filter toggle
        self.nsfw_enabled = self.settings.get("nsfw_filter", True)
        self.nsfw_switch = ctk.CTkSwitch(
            self.sources_frame, text="Hide NSFW",
            command=self._toggle_nsfw_filter, font=ctk.CTkFont(size=12))
        self.nsfw_switch.grid(row=4, column=0, columnspan=2, padx=0, pady=(3, 0), sticky="w")
        if self.nsfw_enabled:
            self.nsfw_switch.select()

        # -- Action buttons (simplified) ---------------------------------
        self.button_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.button_frame.grid(row=5, column=0, padx=20, pady=3, sticky="ew")
        self.button_frame.grid_columnconfigure((0, 1), weight=1)

        self.apply_btn = ctk.CTkButton(self.button_frame, text="Apply Wallpaper",
                                       font=ctk.CTkFont(size=14, weight="bold"),
                                       height=35, command=self.apply_current_wallpaper,
                                       state="disabled")
        self.apply_btn.grid(row=0, column=0, columnspan=2, padx=5, pady=3, sticky="ew")

        self.autostart_switch = ctk.CTkSwitch(
            self.button_frame, text="Auto-start on boot",
            command=self.toggle_autostart, font=ctk.CTkFont(size=12))
        self.autostart_switch.grid(row=1, column=0, columnspan=2, padx=5, pady=(3, 0), sticky="ew")
        if self.is_autostart_enabled():
            self.autostart_switch.select()

        # -- All the fine-tuning controls --------------------------------
        self.controls_frame = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.controls_frame.grid(row=6, column=0, padx=20, pady=(3, 3), sticky="nsew")
        self.controls_frame.grid_columnconfigure((0, 1), weight=1)

        # Scaling mode
        ctk.CTkLabel(self.controls_frame, text="Scaling Mode:",
                     font=ctk.CTkFont(size=12, weight="bold"))\
            .grid(row=0, column=0, columnspan=2, padx=0, pady=(0, 2), sticky="w")

        self.stretch_btn = ctk.CTkButton(self.controls_frame, text="Stretch", height=28,
                                         command=lambda: self.change_scaling("stretch"),
                                         state="disabled", font=ctk.CTkFont(size=12))
        self.stretch_btn.grid(row=1, column=0, padx=(0, 3), pady=1, sticky="ew")
        self.fit_btn = ctk.CTkButton(self.controls_frame, text="Fit", height=28,
                                     command=lambda: self.change_scaling("fit"),
                                     state="disabled", font=ctk.CTkFont(size=12))
        self.fit_btn.grid(row=1, column=1, padx=(3, 0), pady=1, sticky="ew")
        self.fill_btn = ctk.CTkButton(self.controls_frame, text="Fill", height=28,
                                      command=lambda: self.change_scaling("fill"),
                                      state="disabled", font=ctk.CTkFont(size=12))
        self.fill_btn.grid(row=2, column=0, padx=(0, 3), pady=1, sticky="ew")
        self.center_btn = ctk.CTkButton(self.controls_frame, text="Center", height=28,
                                        command=lambda: self.change_scaling("center"),
                                        state="disabled", font=ctk.CTkFont(size=12))
        self.center_btn.grid(row=2, column=1, padx=(3, 0), pady=1, sticky="ew")

        self.scaling_buttons = {
            "stretch": self.stretch_btn, "fit": self.fit_btn,
            "fill": self.fill_btn, "center": self.center_btn,
        }

        # Position D-pad
        ctk.CTkLabel(self.controls_frame, text="Position:",
                     font=ctk.CTkFont(size=12, weight="bold"))\
            .grid(row=3, column=0, columnspan=2, padx=0, pady=(3, 2), sticky="w")

        pos_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        pos_frame.grid(row=4, column=0, columnspan=2, padx=0, pady=2, sticky="ew")
        pos_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.up_btn = ctk.CTkButton(pos_frame, text="↑", width=30, height=30,
                                    command=self.move_wallpaper_up, state="disabled",
                                    font=ctk.CTkFont(size=16, weight="bold"))
        self.up_btn.grid(row=0, column=1, padx=2, pady=1, sticky="ew")
        self.left_btn = ctk.CTkButton(pos_frame, text="←", width=30, height=30,
                                      command=self.move_wallpaper_left, state="disabled",
                                      font=ctk.CTkFont(size=16, weight="bold"))
        self.left_btn.grid(row=1, column=0, padx=2, pady=1, sticky="ew")
        self.reset_btn = ctk.CTkButton(pos_frame, text="✕", width=30, height=30,
                                       command=self.reset_wallpaper, state="disabled",
                                       font=ctk.CTkFont(size=16, weight="bold"))
        self.reset_btn.grid(row=1, column=1, padx=2, pady=1, sticky="ew")
        self.right_btn = ctk.CTkButton(pos_frame, text="→", width=30, height=30,
                                       command=self.move_wallpaper_right, state="disabled",
                                       font=ctk.CTkFont(size=16, weight="bold"))
        self.right_btn.grid(row=1, column=2, padx=2, pady=1, sticky="ew")
        self.down_btn = ctk.CTkButton(pos_frame, text="↓", width=30, height=30,
                                      command=self.move_wallpaper_down, state="disabled",
                                      font=ctk.CTkFont(size=16, weight="bold"))
        self.down_btn.grid(row=2, column=1, padx=2, pady=1, sticky="ew")

        # Flip + Rotate (right after position)
        self.flip_btn = ctk.CTkButton(self.controls_frame, text="⇄ Flip",
                                      font=ctk.CTkFont(size=14, weight="bold"),
                                      height=32, command=self.toggle_flip,
                                      state="disabled")
        self.flip_btn.grid(row=5, column=0, columnspan=2, padx=0, pady=2, sticky="ew")

        self.rotate_cw_btn = ctk.CTkButton(self.controls_frame, text="↻ Rotate CW",
                                           font=ctk.CTkFont(size=12, weight="bold"),
                                           height=28, command=self.rotate_cw,
                                           state="disabled")
        self.rotate_cw_btn.grid(row=6, column=0, padx=(0, 2), pady=2, sticky="ew")
        self.rotate_ccw_btn = ctk.CTkButton(self.controls_frame, text="↺ Rotate CCW",
                                            font=ctk.CTkFont(size=12, weight="bold"),
                                            height=28, command=self.rotate_ccw,
                                            state="disabled")
        self.rotate_ccw_btn.grid(row=6, column=1, padx=(2, 0), pady=2, sticky="ew")

        # Zoom slider
        ctk.CTkLabel(self.controls_frame, text="Zoom:",
                     font=ctk.CTkFont(size=12, weight="bold"))\
            .grid(row=7, column=0, columnspan=2, padx=0, pady=(3, 2), sticky="w")

        self.zoom_slider = ctk.CTkSlider(self.controls_frame, from_=10, to=200,
                                         number_of_steps=38, command=self.change_zoom,
                                         state="disabled")
        self.zoom_slider.grid(row=8, column=0, columnspan=2, padx=5, pady=2, sticky="ew")
        self.zoom_slider.set(100)
        self.zoom_label = ctk.CTkLabel(self.controls_frame, text="100%",
                                       font=ctk.CTkFont(size=12))
        self.zoom_label.grid(row=8, column=1, padx=0, pady=2, sticky="e")

        # Volume slider
        ctk.CTkLabel(self.controls_frame, text="Volume:",
                     font=ctk.CTkFont(size=12, weight="bold"))\
            .grid(row=9, column=0, columnspan=2, padx=0, pady=(3, 2), sticky="w")

        self.volume_slider = ctk.CTkSlider(self.controls_frame, from_=0, to=100,
                                           number_of_steps=100, command=self.change_volume,
                                           state="disabled")
        self.volume_slider.grid(row=10, column=0, columnspan=2, padx=5, pady=2, sticky="ew")
        self.volume_slider.set(100)
        self.volume_label = ctk.CTkLabel(self.controls_frame, text="100%",
                                         font=ctk.CTkFont(size=12))
        self.volume_label.grid(row=10, column=1, padx=0, pady=2, sticky="e")

        # Mute button (below volume)
        self.mute_btn = ctk.CTkButton(self.controls_frame, text="🔊 Unmute",
                                      font=ctk.CTkFont(size=14, weight="bold"),
                                      height=32, command=self.toggle_audio,
                                      state="disabled")
        self.mute_btn.grid(row=11, column=0, columnspan=2, padx=0, pady=2, sticky="ew")

        # Speed slider
        ctk.CTkLabel(self.controls_frame, text="Speed:",
                     font=ctk.CTkFont(size=12, weight="bold"))\
            .grid(row=12, column=0, columnspan=2, padx=0, pady=(3, 2), sticky="w")

        self.speed_slider = ctk.CTkSlider(self.controls_frame, from_=0.0, to=4.0,
                                          number_of_steps=80, command=self.change_speed,
                                          state="disabled")
        self.speed_slider.grid(row=13, column=0, columnspan=2, padx=5, pady=2, sticky="ew")
        self.speed_slider.set(1.0)
        self.speed_label = ctk.CTkLabel(self.controls_frame, text="1.00x",
                                        font=ctk.CTkFont(size=12))
        self.speed_label.grid(row=14, column=0, columnspan=2, padx=0, pady=2, sticky="w")

        # Pause button
        self.pause_btn = ctk.CTkButton(self.controls_frame, text="⏸ Pause",
                                       font=ctk.CTkFont(size=14, weight="bold"),
                                       height=32, command=self.toggle_pause,
                                       state="disabled")
        self.pause_btn.grid(row=15, column=0, columnspan=2, padx=0, pady=(3, 0), sticky="ew")

        # Refresh list button (inline in the scrollable controls)
        ctk.CTkButton(self.controls_frame, text="🔄 Refresh List",
                      command=self.load_wallpapers)\
            .grid(row=16, column=0, columnspan=2, padx=0, pady=(8, 15), sticky="ew")

        self.status_bar = ctk.CTkLabel(self, text="Ready", anchor="w")
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

    # ------------------------------------------------------------------
    #  Monitor selection helpers
    # ------------------------------------------------------------------

    def _on_monitor_mode_change(self, value):
        """Switch between All and Per Monitor mode."""
        new_mode = "all" if value == "All" else "individual"
        if new_mode == self.monitor_mode:
            return

        self._save_current_wallpaper_settings()

        if new_mode == "all":
            self.monitor_btn_frame.grid_remove()
            self.selected_monitors = list(self.monitors)
        else:
            self.monitor_btn_frame.grid()
            self.selected_monitors = [self.monitors[0]]

        self.monitor_mode = new_mode
        self.monitor_btn_frame.grid_remove() if new_mode == "all" else self.monitor_btn_frame.grid()
        self._update_monitor_button_states()
        self.settings["monitor_mode"] = new_mode
        WallpaperScanner.save_settings(self.settings)

        if self.current_wallpaper:
            self.status_bar.configure(text=f"Switched to {value} mode — reapplying...")
            WallpaperManager.kill_all()
            self.apply_current_wallpaper()

    def _select_monitor(self, monitor):
        """Select a single target monitor in per-monitor mode."""
        self.selected_monitors = [monitor]
        self._update_monitor_button_states()
        self.status_bar.configure(text=f"Selected: {monitor}")

    def _update_monitor_button_states(self):
        """Highlight the active monitor(s)."""
        for name, btn in self.monitor_buttons.items():
            if self.monitor_mode == "all" or name in self.selected_monitors:
                btn.configure(fg_color=("#3a7ebf", "#1f538d"))
            else:
                btn.configure(fg_color="transparent")

    # ------------------------------------------------------------------
    #  Source management
    # ------------------------------------------------------------------

    def _toggle_steam_source(self):
        """Enable or disable Steam Workshop scanning."""
        config = WallpaperScanner.load_config()
        found = False
        for s in config["sources"]:
            if s["type"] == "steam_workshop":
                s["enabled"] = self.steam_switch.get()
                found = True
                break
        if not found:
            config["sources"].append({
                "type": "steam_workshop",
                "enabled": self.steam_switch.get()
            })
        WallpaperScanner.save_config(config)
        self.load_wallpapers()

    def _add_local_source(self):
        """Pick a folder and add it as a wallpaper source."""
        folder = filedialog.askdirectory(title="Select a wallpaper folder")
        if not folder:
            return
        WallpaperScanner.add_local_source(folder)
        self._rebuild_folder_list()
        self.load_wallpapers()

    def _remove_local_source(self, path):
        """Remove a local folder from sources."""
        config = WallpaperScanner.load_config()
        config["sources"] = [
            s for s in config["sources"]
            if not (s.get("type") == "local_folder" and s.get("path") == path)
        ]
        WallpaperScanner.save_config(config)
        self._rebuild_folder_list()
        self.load_wallpapers()

    def _rebuild_folder_list(self):
        """Recreate the local-folder entries in the sources section."""
        for w in self.folder_list_frame.winfo_children():
            w.destroy()

        config = WallpaperScanner.load_config()
        folders = [
            s for s in config.get("sources", [])
            if s.get("type") == "local_folder"
        ]
        for i, src in enumerate(folders):
            path = src.get("path", "")
            label = ctk.CTkLabel(
                self.folder_list_frame, text=os.path.basename(path),
                font=ctk.CTkFont(size=11), anchor="w")
            label.grid(row=i, column=0, padx=(0, 2), pady=1, sticky="w")
            rm_btn = ctk.CTkButton(
                self.folder_list_frame, text="✕", width=22, height=18,
                font=ctk.CTkFont(size=10),
                command=lambda p=path: self._remove_local_source(p))
            rm_btn.grid(row=i, column=1, padx=0, pady=1, sticky="e")
            self.folder_list_frame.grid_columnconfigure(0, weight=1)

    def _toggle_nsfw_filter(self):
        """Turn the NSFW filter on or off and re-apply."""
        self.nsfw_enabled = self.nsfw_switch.get()
        self.settings["nsfw_filter"] = self.nsfw_enabled
        WallpaperScanner.save_settings(self.settings)
        self._rebuild_grid(self.search_entry.get())

    def _apply_search(self, event=None):
        """Filter the grid by the search query (Enter key or button)."""
        self._rebuild_grid(self.search_entry.get())

    def _clear_search(self):
        """Reset the search field and show all wallpapers."""
        self.search_entry.delete(0, "end")
        self._rebuild_grid()

    def _get_target_monitors(self):
        """Return the list of monitor names to send IPC/apply to."""
        if self.monitor_mode == "all":
            return ["all"]
        return list(self.selected_monitors)

    def _get_socket_path(self, monitor):
        """Get the IPC socket path for a given monitor target."""
        return f"/tmp/mpvpaper-socket-{monitor}"

    # ------------------------------------------------------------------
    #  Wallpaper grid
    # ------------------------------------------------------------------

    def load_wallpapers(self):
        """Scan for wallpapers and fill the grid with thumbnails."""
        self.status_bar.configure(text="Scanning...")
        self.update()

        self.wallpapers = WallpaperScanner.scan_wallpapers()
        if not self.wallpapers:
            for w in self.wallpaper_grid.winfo_children():
                w.destroy()
            sources = WallpaperScanner.load_config().get("sources", [])
            if not sources or not any(s.get("enabled") for s in sources):
                self.status_bar.configure(
                    text="No sources enabled — toggle Steam Workshop or add a folder in the sidebar")
            else:
                self.status_bar.configure(text="No wallpapers found")
            return

        self._rebuild_grid()

    def _rebuild_grid(self, query=None):
        """Rebuild the wallpaper grid, optionally filtering by search query."""
        for w in self.wallpaper_grid.winfo_children():
            w.destroy()

        filtered = list(self.wallpapers)

        # NSFW filter
        if self.nsfw_switch.get():
            filtered = [
                w for w in filtered
                if not any(t in WallpaperScanner.NSFW_TAGS for t in w.tags)
                and w.content_rating not in ("Mature", "Questionable")
                and not any(t in w.title.lower() for t in WallpaperScanner.NSFW_TAGS)
            ]

        # Search query filter
        if query:
            q = query.strip().lower()
            if q:
                filtered = [
                    w for w in filtered
                    if q in w.title.lower()
                    or any(q in tag for tag in w.tags)
                ]

        if not filtered:
            self.status_bar.configure(text="No wallpapers match your filters")
            return

        columns = 4
        for i, wp in enumerate(filtered):
            row, col = divmod(i, columns)
            item = ctk.CTkFrame(self.wallpaper_grid, fg_color="transparent")
            item.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

            thumb = None
            if wp.preview_path and os.path.exists(wp.preview_path):
                try:
                    img = Image.open(wp.preview_path)
                    if img.format == 'GIF':
                        img.seek(0)
                        img = img.convert('RGB')
                    img.thumbnail((100, 100), Image.Resampling.LANCZOS)
                    thumb = ctk.CTkImage(light_image=img, dark_image=img, size=(100, 100))
                except Exception:
                    pass

            name = truncate_text(wp.title, max_length=20)
            btn = ctk.CTkButton(item, text=name, image=thumb, compound="top",
                                anchor="center", width=100,
                                height=130 if thumb else 30,
                                command=lambda w=wp: self.select_wallpaper(w))
            btn.pack(fill="both", expand=True)
            self.wallpaper_grid.grid_columnconfigure(col, weight=1)

        total = len(self.wallpapers)
        shown = len(filtered)
        if shown < total:
            self.status_bar.configure(text=f"Showing {shown} of {total} wallpapers")
        else:
            self.status_bar.configure(text=f"Found {total} wallpapers")
        self._bind_mousewheel()

    def _bind_mousewheel(self):
        try:
            inner = self.wallpaper_grid._scroll_frame
            inner.bind('<Button-4>', self._scroll_up, add='+')
            inner.bind('<Button-5>', self._scroll_down, add='+')
            for child in inner.winfo_children():
                child.bind('<Button-4>', self._scroll_up, add='+')
                child.bind('<Button-5>', self._scroll_down, add='+')
                for sub in child.winfo_children():
                    sub.bind('<Button-4>', self._scroll_up, add='+')
                    sub.bind('<Button-5>', self._scroll_down, add='+')
        except Exception:
            pass

    def _scroll_up(self, event):
        self.wallpaper_grid._parent_canvas.yview_scroll(-3, "units")

    def _scroll_down(self, event):
        self.wallpaper_grid._parent_canvas.yview_scroll(3, "units")

    # ------------------------------------------------------------------
    #  Selecting and applying wallpapers
    # ------------------------------------------------------------------

    def select_wallpaper(self, wp):
        """Pick a wallpaper and apply to all monitors (per-monitor mode) or one all-mode instance."""
        for cb in self._pending_callbacks:
            self.after_cancel(cb)
        self._pending_callbacks.clear()

        self._save_current_wallpaper_settings()
        self.current_wallpaper = wp
        self.title_label.configure(text=wp.title)
        self._reset_state()
        self._reset_ui_widgets()
        self._enable_controls()

        # In per-monitor mode: only the selected monitor gets the wallpaper
        targets = self._get_target_monitors()
        for monitor in targets:
            try:
                if WallpaperManager.apply_wallpaper(wp.file_path, self.audio_enabled,
                                                    self.scaling_mode, monitor):
                    self.status_bar.configure(text=f"Applied to {monitor}: {wp.title}")
                    self._save_wallpaper_info(monitor)
                    cb1 = self.after(500, lambda m=monitor: self._send_scaling_ipc("stretch", m))
                    self._pending_callbacks.append(cb1)
                    cb2 = self.after(1000, lambda m=monitor: self._restore_wallpaper_settings(
                        wp.file_path, restore_pause=True, monitor=m))
                    self._pending_callbacks.append(cb2)
                else:
                    self.status_bar.configure(text=f"Failed to apply to {monitor}: {wp.title}")
            except Exception as e:
                self.status_bar.configure(text=f"Error applying to {monitor}: {e}")

        self._load_preview(wp)
        self.status_bar.configure(text=f"Selected: {wp.title}")

    def apply_current_wallpaper(self):
        """Re-apply the currently selected wallpaper to all monitors with current settings."""
        if not self.current_wallpaper:
            return
        scaling_mode = self.scaling_mode
        # Apply to the selected monitor(s) only
        targets = self._get_target_monitors()

        self._reset_state()
        self._reset_ui_widgets()
        self._enable_controls()
        self._update_scaling_button_states(scaling_mode)

        for monitor in targets:
            if WallpaperManager.apply_wallpaper(self.current_wallpaper.file_path,
                                                self.audio_enabled, scaling_mode, monitor):
                self._save_wallpaper_info(monitor)

        # Restore per-monitor settings after all instances are running
        for monitor in targets:
            self.after(500, lambda m=monitor: self._send_scaling_ipc("stretch", m))
            self.after(1000, lambda m=monitor: self._restore_wallpaper_settings(
                self.current_wallpaper.file_path, restore_pause=False, monitor=m))

        self._save_current_wallpaper_settings()
        self.status_bar.configure(text=f"Applied: {self.current_wallpaper.title}")

    def _reset_state(self):
        """Put all the knobs back to square one."""
        self.audio_enabled = False
        self.scaling_mode = "stretch"
        self.flipped = False
        self.rotation = 0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.current_speed = 1.0
        self.is_paused = False
        self.zoom_level = 0.0
        self.zoom_percent = 100
        self.volume_level = 100

    def _reset_ui_widgets(self):
        """Reset all the visible widgets to their default values."""
        self.pause_btn.configure(text="⏸ Pause")
        self.mute_btn.configure(text="🔊 Unmute")
        self.zoom_slider.set(100)
        self.zoom_label.configure(text="100%")
        self.volume_slider.set(100)
        self.volume_label.configure(text="100%")
        self.speed_slider.set(1.0)
        self.speed_label.configure(text="1.00x")
        self._update_scaling_button_states(self.scaling_mode)

    def _enable_controls(self):
        """Flip every control to 'normal' so the user can tweak stuff.
        Safe to call before the UI is built (handy for headless mode)."""
        for attr in ('apply_btn', 'mute_btn', 'flip_btn', 'reset_btn',
                     'pause_btn', 'rotate_cw_btn', 'rotate_ccw_btn'):
            if hasattr(self, attr):
                getattr(self, attr).configure(state="normal")
        if hasattr(self, 'scaling_buttons'):
            for btn in self.scaling_buttons.values():
                btn.configure(state="normal")
        for attr in ('up_btn', 'down_btn', 'left_btn', 'right_btn'):
            if hasattr(self, attr):
                getattr(self, attr).configure(state="normal")
        for attr in ('zoom_slider', 'volume_slider', 'speed_slider'):
            if hasattr(self, attr):
                getattr(self, attr).configure(state="normal")

    def _build_wallpaper_info(self, monitor="all"):
        """Package up the current wallpaper info into a dict for saving."""
        return {
            "file_path": self.current_wallpaper.file_path,
            "scaling_mode": self.scaling_mode,
            "audio_enabled": self.audio_enabled,
            "title": self.current_wallpaper.title,
            "monitor": monitor,
        }

    def _save_wallpaper_info(self, monitor="all"):
        """Save current wallpaper info so it can be restored on boot."""
        if self.settings.get("restore_last_wallpaper", True):
            info = self._build_wallpaper_info(monitor)
            existing = WallpaperScanner.load_last_wallpaper()
            if isinstance(existing, dict) and "monitors" in existing:
                monitors_dict = existing.get("monitors", {})
            else:
                monitors_dict = {}
            monitors_dict[monitor] = info
            WallpaperScanner.save_last_wallpaper({
                "mode": self.monitor_mode,
                "monitors": monitors_dict,
            })
        self.settings["default_scaling_mode"] = self.scaling_mode
        self.settings["monitor_mode"] = self.monitor_mode
        WallpaperScanner.save_settings(self.settings)

    def _load_preview(self, wp):
        """Load and display the preview image for a wallpaper."""
        if wp.preview_path and os.path.exists(wp.preview_path):
            try:
                img = Image.open(wp.preview_path)
                if img.format == 'GIF':
                    img.seek(0)
                    img = img.convert('RGB')
                ow, oh = img.size
                scale = min(180 / ow, 120 / oh)
                new_size = (int(ow * scale), int(oh * scale))
                img_resized = img.resize(new_size, Image.Resampling.LANCZOS)
                self.preview_image = ctk.CTkImage(light_image=img_resized,
                                                  dark_image=img_resized,
                                                  size=new_size)
                self.preview_label.configure(image=self.preview_image, text="")
                self.preview_label.update_idletasks()
                self.preview_label.update()
            except Exception as e:
                print(f"Couldn't load preview: {e}")
                self.preview_label.configure(image=None, text="Preview error")
                self.preview_label.update()
        else:
            self.preview_image = None
            self.preview_label.configure(image=None, text="No preview")
            self.preview_label.update()

    # ------------------------------------------------------------------
    #  Scaling
    # ------------------------------------------------------------------

    def _update_scaling_button_states(self, active_mode):
        """Highlight whichever scaling mode button is active, dim the rest."""
        if not hasattr(self, 'scaling_buttons'):
            return
        for mode, btn in self.scaling_buttons.items():
            if mode == active_mode:
                btn.configure(fg_color=("#3a7ebf", "#1f538d"))
            else:
                btn.configure(fg_color="transparent")

    def change_scaling(self, scaling_mode):
        """Swap how the wallpaper fills your screen."""
        if not self.current_wallpaper:
            return
        try:
            self.scaling_mode = scaling_mode
            self._update_scaling_button_states(scaling_mode)
            targets = self._get_target_monitors()

            for m in targets:
                socket = self._get_socket_path(m)
                if not os.path.exists(socket):
                    continue

                # Reset position, speed, and pause
                self.pan_x = self.pan_y = 0.0
                self._send_ipc_command("video-pan-x", 0.0, socket)
                self._send_ipc_command("video-pan-y", 0.0, socket)

                self.current_speed = 1.0
                self.speed_slider.set(1.0)
                self.speed_label.configure(text="1.00x")
                self._send_ipc_command("speed", 1.0, socket)

                self.is_paused = False
                self.pause_btn.configure(text="⏸ Pause")
                self._send_ipc_command("pause", False, socket)

                if scaling_mode == "stretch":
                    self.zoom_percent = 100
                    self.zoom_level = 0.0
                    self.zoom_slider.set(100)
                    self.zoom_label.configure(text="100%")
                    self._send_ipc_command("video-zoom", 0.0, socket)

                self._send_scaling_ipc(scaling_mode, m)

            self.status_bar.configure(text=f"Scaling set to {scaling_mode.capitalize()}")
            self._save_current_wallpaper_settings()
        except Exception as e:
            self.status_bar.configure(text=f"Error: {str(e)}")

    # ------------------------------------------------------------------
    #  IPC — talking to the running mpv instance(s)
    # ------------------------------------------------------------------

    def _get_screen_resolution(self):
        """Figure out the primary monitor's resolution (or guess 1080p)."""
        try:
            result = subprocess.run(['xrandr', '--query'],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if ' connected' in line:
                        m = re.search(r'([0-9]+)x([0-9]+)', line)
                        if m:
                            return int(m.group(1)), int(m.group(2))
        except Exception:
            pass
        return 1920, 1080

    def _send_ipc_command(self, property_name, value, socket=None):
        """Send a JSON IPC command to a specific mpv socket."""
        if not socket or not os.path.exists(socket):
            return
        try:
            cmd = json.dumps({"command": ["set_property", property_name, value]}) + '\n'
            p = subprocess.Popen(['socat', '-', socket],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True)
            p.communicate(input=cmd, timeout=5)
        except Exception:
            pass

    def _send_ipc_to_targets(self, property_name, value):
        """Send an IPC command to all currently active monitor(s)."""
        for m in self._get_target_monitors():
            self._send_ipc_command(property_name, value, self._get_socket_path(m))

    def _send_scaling_ipc(self, scaling_mode, monitor="all"):
        """Send the appropriate panscan (and optionally zoom) commands for a scaling mode."""
        socket = self._get_socket_path(monitor)
        if not os.path.exists(socket):
            return
        try:
            if scaling_mode == "center":
                cmd1 = json.dumps({"command": ["set_property", "panscan", 0.0]})
                cmd2 = json.dumps({"command": ["set_property", "video-zoom", 0.0]})
                p1 = subprocess.Popen(['socat', '-', socket],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True)
                p1.communicate(input=cmd1 + '\n', timeout=5)
                p2 = subprocess.Popen(['socat', '-', socket],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True)
                p2.communicate(input=cmd2 + '\n', timeout=5)
                return
            panscan = {"stretch": 1.0, "fit": 0.0, "fill": 0.8}.get(scaling_mode, 0.0)
            cmd = json.dumps({"command": ["set_property", "panscan", panscan]})
            p = subprocess.Popen(['socat', '-', socket],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True)
            p.communicate(input=cmd + '\n', timeout=5)
        except Exception:
            pass

    # ------------------------------------------------------------------
    #  Position controls
    # ------------------------------------------------------------------

    def _update_wallpaper_position(self):
        """Send the current pan values to mpv and save."""
        self._send_ipc_to_targets("video-pan-x", self.pan_x)
        self._send_ipc_to_targets("video-pan-y", self.pan_y)
        self._save_current_wallpaper_settings()

    def move_wallpaper_up(self):
        if self.pan_y > -self.pan_limit:
            self.pan_y -= self.pan_increment
            self._update_wallpaper_position()

    def move_wallpaper_down(self):
        if self.pan_y < self.pan_limit:
            self.pan_y += self.pan_increment
            self._update_wallpaper_position()

    def move_wallpaper_left(self):
        if self.pan_x > -self.pan_limit:
            self.pan_x -= self.pan_increment
            self._update_wallpaper_position()

    def move_wallpaper_right(self):
        if self.pan_x < self.pan_limit:
            self.pan_x += self.pan_increment
            self._update_wallpaper_position()

    # ------------------------------------------------------------------
    #  Zoom
    # ------------------------------------------------------------------

    def change_zoom(self, value):
        """Adjust the zoom slider. Snaps to 5% increments for sanity."""
        if not self.current_wallpaper:
            return
        self.zoom_percent = round(float(value) / 5) * 5
        self.zoom_level = math.log2(self.zoom_percent / 100.0)
        self.zoom_label.configure(text=f"{self.zoom_percent}%")
        self._send_ipc_to_targets("video-zoom", self.zoom_level)
        self._save_current_wallpaper_settings()

    # ------------------------------------------------------------------
    #  Volume
    # ------------------------------------------------------------------

    def change_volume(self, value):
        """Turn the volume knob. Auto-unmutes if you move it while muted."""
        if not self.current_wallpaper:
            return
        self.volume_level = int(round(float(value)))
        self.volume_label.configure(text=f"{self.volume_level}%")
        self._send_ipc_to_targets("volume", self.volume_level)
        if self.volume_level > 0 and not self.audio_enabled:
            self.audio_enabled = True
            self.mute_btn.configure(text="🔇 Mute")
            self._send_ipc_to_targets("mute", False)
            self.status_bar.configure(text="Audio unmuted")
        self._save_current_wallpaper_settings()

    # ------------------------------------------------------------------
    #  Speed
    # ------------------------------------------------------------------

    def change_speed(self, value):
        """Change playback speed — anything from 0x to 4x."""
        if not self.current_wallpaper:
            return
        self.current_speed = round(float(value), 2)
        self.speed_label.configure(text=f"{self.current_speed:.2f}x")
        self._send_ipc_to_targets("speed", self.current_speed)
        self._save_current_wallpaper_settings()

    def reset_speed(self):
        """Put speed back to 1x."""
        self.current_speed = 1.0
        self.speed_slider.set(1.0)
        self.speed_label.configure(text="1.00x")
        if self.current_wallpaper:
            self._send_ipc_to_targets("speed", 1.0)

    # ------------------------------------------------------------------
    #  Pause / Play
    # ------------------------------------------------------------------

    def toggle_pause(self):
        if not self.current_wallpaper:
            return
        try:
            self.is_paused = not self.is_paused
            if self.is_paused:
                self.pause_btn.configure(text="▶ Play")
                self.status_bar.configure(text="Wallpaper paused")
            else:
                self.pause_btn.configure(text="⏸ Pause")
                self.status_bar.configure(text="Wallpaper playing")
            self._send_ipc_to_targets("pause", self.is_paused)
            self._save_current_wallpaper_settings()
        except Exception as e:
            self.status_bar.configure(text=f"Error toggling pause: {e}")

    def reset_pause_state(self):
        """Un-pause the wallpaper."""
        self.is_paused = False
        self.pause_btn.configure(text="⏸ Pause")
        if self.current_wallpaper:
            self._send_ipc_to_targets("pause", False)

    # ------------------------------------------------------------------
    #  Audio
    # ------------------------------------------------------------------

    def toggle_audio(self):
        """Mute or unmute the wallpaper audio via mpv's 'cycle audio' command."""
        if not self.current_wallpaper:
            return
        try:
            any_socket = False
            for m in self._get_target_monitors():
                socket = self._get_socket_path(m)
                if not os.path.exists(socket):
                    continue
                any_socket = True
                p = subprocess.Popen(['socat', '-', socket],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True)
                p.communicate(input='cycle audio\n', timeout=5)
            if not any_socket:
                self.status_bar.configure(text="Error: No wallpaper running")
                return
            self.audio_enabled = not self.audio_enabled
            if self.audio_enabled:
                self.mute_btn.configure(text="🔇 Mute")
                self.status_bar.configure(text="Audio enabled")
            else:
                self.mute_btn.configure(text="🔊 Unmute")
                self.status_bar.configure(text="Audio disabled")
            self._save_current_wallpaper_settings()
        except subprocess.TimeoutExpired:
            self.status_bar.configure(text="Error: Command timeout")
        except subprocess.CalledProcessError as e:
            self.status_bar.configure(text=f"Error: Could not toggle audio ({e})")
        except FileNotFoundError:
            self.status_bar.configure(text="Error: socat not found")
        except Exception as e:
            self.status_bar.configure(text=f"Error: {e}")

    # ------------------------------------------------------------------
    #  Flip
    # ------------------------------------------------------------------

    def toggle_flip(self):
        """Mirror the wallpaper horizontally (or un-mirror it)."""
        if not self.current_wallpaper:
            return
        try:
            self.flipped = not self.flipped
            if self.flipped:
                self._send_ipc_to_targets("vf", "@flip:hflip")
                self.flip_btn.configure(text="⇄ Unflip")
                self.status_bar.configure(text="Wallpaper flipped horizontally")
            else:
                self._send_ipc_to_targets("vf", "")
                self.flip_btn.configure(text="⇄ Flip")
                self.status_bar.configure(text="Wallpaper unflipped")
            self._save_current_wallpaper_settings()
        except Exception as e:
            self.status_bar.configure(text=f"Error: {e}")

    # ------------------------------------------------------------------
    #  Rotation
    # ------------------------------------------------------------------

    def rotate_cw(self):
        """Spin the wallpaper 90° clockwise."""
        if not self.current_wallpaper:
            return
        self.rotation = (self.rotation + 90) % 360
        self._send_ipc_to_targets("video-rotate", self.rotation)
        self.status_bar.configure(text=f"Rotated {self.rotation}°")
        self._save_current_wallpaper_settings()

    def rotate_ccw(self):
        """Spin the wallpaper 90° counter-clockwise."""
        if not self.current_wallpaper:
            return
        self.rotation = (self.rotation - 90) % 360
        self._send_ipc_to_targets("video-rotate", self.rotation)
        self.status_bar.configure(text=f"Rotated {self.rotation}°")
        self._save_current_wallpaper_settings()

    def reset_rotation(self):
        """Take the wallpaper back to 0°."""
        self.rotation = 0
        if self.current_wallpaper:
            self._send_ipc_to_targets("video-rotate", 0)

    # ------------------------------------------------------------------
    #  Reset — wipe everything back to defaults
    # ------------------------------------------------------------------

    def reset_wallpaper(self):
        """Clear all saved settings for this wallpaper and start fresh."""
        if not self.current_wallpaper:
            return

        targets = self._get_target_monitors()
        for m in targets:
            WallpaperScanner.clear_wallpaper_settings(self.current_wallpaper.file_path, m)

        self._reset_state()
        self._reset_ui_widgets()

        for m in targets:
            socket = self._get_socket_path(m)
            if os.path.exists(socket):
                self._send_ipc_command("video-pan-x", 0.0, socket)
                self._send_ipc_command("video-pan-y", 0.0, socket)
                self._send_ipc_command("video-zoom", 0.0, socket)
                self._send_ipc_command("volume", 100, socket)
                self._send_ipc_command("speed", 1.0, socket)
                self._send_ipc_command("video-rotate", 0, socket)

            WallpaperManager.apply_wallpaper(self.current_wallpaper.file_path,
                                             self.audio_enabled, self.scaling_mode, m)

        self._enable_controls()
        self._reset_ui_widgets()
        self.status_bar.configure(text=f"Reset: {self.current_wallpaper.title}")
        self._save_current_wallpaper_settings()

    # ------------------------------------------------------------------
    #  Auto-start
    # ------------------------------------------------------------------

    def get_autostart_path(self):
        d = os.path.expanduser("~/.config/autostart")
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, "tuxpaper.desktop")

    def enable_autostart(self):
        path = self.get_autostart_path()
        script = os.path.abspath(__file__)
        venv = os.path.join(os.path.dirname(script), "venv", "bin", "python")
        python = venv if os.path.exists(venv) else "python3"
        entry = f"""[Desktop Entry]
Type=Application
Name=Tuxpaper Engine
Comment=Animated wallpaper manager
Exec={python} {script} --headless
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(entry)
            return True
        except IOError:
            return False

    def disable_autostart(self):
        path = self.get_autostart_path()
        try:
            if os.path.exists(path):
                os.remove(path)
            return True
        except IOError:
            return False

    def is_autostart_enabled(self):
        return os.path.exists(self.get_autostart_path())

    def toggle_autostart(self):
        if self.autostart_switch.get() == 1:
            if self.enable_autostart():
                self.status_bar.configure(text="Auto-start enabled")
            else:
                self.status_bar.configure(text="Failed to enable auto-start")
                self.autostart_switch.deselect()
        else:
            if self.disable_autostart():
                self.status_bar.configure(text="Auto-start disabled")
            else:
                self.status_bar.configure(text="Failed to disable auto-start")
                self.autostart_switch.select()

    # ------------------------------------------------------------------
    #  Startup / restore
    # ------------------------------------------------------------------

    def auto_apply_last_wallpaper_on_startup(self):
        """On boot, restore each monitor to its last wallpaper."""
        if not self.settings.get("restore_last_wallpaper", True):
            return
        last = WallpaperScanner.load_last_wallpaper()

        if not last:
            return

        # Handle old format (single wallpaper, no monitor info)
        if isinstance(last, dict) and "file_path" in last and "monitors" not in last:
            file_path = last.get("file_path", "")
            if os.path.exists(file_path):
                self._enable_controls()
                targets = self._get_target_monitors()
                for m in targets:
                    scaling = last.get("scaling_mode", "stretch")
                    audio = last.get("audio_enabled", False)
                    if WallpaperManager.apply_wallpaper(file_path, audio, scaling, m):
                        self.scaling_mode = scaling
                        self.audio_enabled = audio
                        self.current_wallpaper = self._create_temp_wallpaper_object(file_path, last)
                        self._update_scaling_button_states(scaling)
                        self.status_bar.configure(
                            text=f"Auto-Applied: {last.get('title', 'Last Wallpaper')}")
                        if hasattr(self, 'title_label') and self.current_wallpaper:
                            self.title_label.configure(text=self.current_wallpaper.title)
                        self.after(500, lambda x=m: self._send_scaling_ipc("stretch", x))
                        self.after(1000, lambda x=m: self._restore_wallpaper_settings(
                            file_path, restore_pause=False, monitor=m))
            return

        # New format: per-monitor
        monitors_info = last.get("monitors", {})
        for monitor, info in monitors_info.items():
            file_path = info.get("file_path", "")
            if not os.path.exists(file_path):
                continue
            self._enable_controls()
            scaling = info.get("scaling_mode", "stretch")
            audio = info.get("audio_enabled", False)

            if WallpaperManager.apply_wallpaper(file_path, audio, scaling, monitor):
                self.scaling_mode = scaling
                self.audio_enabled = audio
                self.current_wallpaper = self._create_temp_wallpaper_object(file_path, info)
                self._update_scaling_button_states(scaling)
                self.status_bar.configure(
                    text=f"Auto-Applied to {monitor}: {info.get('title', 'Wallpaper')}")
                if hasattr(self, 'title_label') and self.current_wallpaper:
                    self.title_label.configure(text=self.current_wallpaper.title)
                self.after(500, lambda x=monitor: self._send_scaling_ipc("stretch", x))
                self.after(1000, lambda x=monitor: self._restore_wallpaper_settings(
                    file_path, restore_pause=False, monitor=x))

    def _create_temp_wallpaper_object(self, file_path, info):
        """Build a minimal Wallpaper stand-in for when we're restoring state on boot."""
        try:
            class TempWallpaper:
                def __init__(self, path, title):
                    self.file_path = path
                    self.title = title
                    self.preview_path = None
                    self.folder_path = os.path.dirname(path)
            return TempWallpaper(file_path, info.get("title", os.path.basename(file_path)))
        except Exception as e:
            print(f"Failed to create temp wallpaper: {e}")
            return None

    # ------------------------------------------------------------------
    #  Per-wallpaper settings persistence
    # ------------------------------------------------------------------

    def _save_current_wallpaper_settings(self):
        """Persist settings for the current wallpaper on all active monitors."""
        try:
            if not self.settings.get("restore_last_wallpaper", True) or not self.current_wallpaper:
                return

            targets = self._get_target_monitors()
            for monitor in targets:
                all_settings = {
                    "scaling_mode": self.scaling_mode,
                    "pan_x": self.pan_x,
                    "pan_y": self.pan_y,
                    "zoom_percent": self.zoom_percent,
                    "zoom_level": self.zoom_level,
                    "volume_level": self.volume_level,
                    "current_speed": self.current_speed,
                    "audio_enabled": self.audio_enabled,
                    "flipped": self.flipped,
                    "is_paused": self.is_paused,
                    "rotation": self.rotation,
                }
                WallpaperScanner.save_wallpaper_settings(
                    self.current_wallpaper.file_path, monitor, all_settings)

            self.settings["default_scaling_mode"] = self.scaling_mode
            self.settings["monitor_mode"] = self.monitor_mode
            WallpaperScanner.save_settings(self.settings)
        except Exception as e:
            print(f"Oops, couldn't save wallpaper settings: {e}")

    def _restore_wallpaper_settings(self, file_path, restore_pause=True, monitor="all"):
        """Re-apply every saved setting for a wallpaper on a specific monitor."""
        settings = WallpaperScanner.load_wallpaper_settings(file_path, monitor)
        if not settings:
            return

        saved_scaling = settings.get("scaling_mode", "stretch")
        self.scaling_mode = saved_scaling
        self._update_scaling_button_states(saved_scaling)

        self.pan_x = settings.get("pan_x", 0.0)
        self.pan_y = settings.get("pan_y", 0.0)

        self.zoom_percent = settings.get("zoom_percent", 100)
        self.zoom_level = settings.get("zoom_level", 0.0)
        self.zoom_slider.set(self.zoom_percent)
        self.zoom_label.configure(text=f"{self.zoom_percent}%")

        self.volume_level = settings.get("volume_level", 100)
        self.volume_slider.set(self.volume_level)
        self.volume_label.configure(text=f"{self.volume_level}%")

        self.current_speed = settings.get("current_speed", 1.0)
        self.speed_slider.set(self.current_speed)
        self.speed_label.configure(text=f"{self.current_speed:.2f}x")

        self.audio_enabled = settings.get("audio_enabled", False)
        self.mute_btn.configure(text="🔇 Mute" if self.audio_enabled else "🔊 Unmute")

        self.flipped = settings.get("flipped", False)
        self.flip_btn.configure(text="⇄ Unflip" if self.flipped else "⇄ Flip")

        self.rotation = settings.get("rotation", 0)

        if restore_pause:
            self.is_paused = settings.get("is_paused", False)
        else:
            self.is_paused = False
        self.pause_btn.configure(text="▶ Play" if self.is_paused else "⏸ Pause")

        self._save_current_wallpaper_settings()

        socket = self._get_socket_path(monitor)
        self.after(800, lambda: self._send_scaling_ipc(saved_scaling, monitor))
        self.after(900, lambda: self._send_ipc_command("video-pan-x", self.pan_x, socket))
        self.after(950, lambda: self._send_ipc_command("video-pan-y", self.pan_y, socket))
        self.after(1000, lambda: self._send_ipc_command("video-zoom", self.zoom_level, socket))
        self.after(1100, lambda: self._send_ipc_command("volume", self.volume_level, socket))
        self.after(1200, lambda: self._send_ipc_command("speed", self.current_speed, socket))
        if self.audio_enabled:
            self.after(1300, lambda: self._send_ipc_command("mute", False, socket))
        if self.flipped:
            self.after(1400, lambda: self._send_ipc_command("vf", "@flip:hflip", socket))
        if self.rotation:
            self.after(1450, lambda: self._send_ipc_command("video-rotate", self.rotation, socket))
        self.after(1500, lambda: self._send_ipc_command("pause", self.is_paused, socket))

    # ------------------------------------------------------------------
    #  Cleanup
    # ------------------------------------------------------------------

    def on_closing(self):
        self._save_current_wallpaper_settings()
        self.destroy()


if __name__ == "__main__":
    headless = "--headless" in sys.argv
    app = TuxpaperApp(headless=headless)
    if not headless:
        app.mainloop()
