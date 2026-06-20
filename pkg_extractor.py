"""Wallpaper Engine PKG scene file extractor.

PKG format (PKGV0022):
  [Header]        16 bytes
  [Directory]     N entries with name + size
  [File Data]     Concatenated raw file data

Header (16 bytes):
  - count_or_flag: uint32 LE (typically 8)
  - magic:         4 bytes "PKGV"
  - version:       4 bytes "0022"
  - entry_count:   uint32 LE

Directory Entry (variable):
  - name_len:  uint32 LE
  - name:      UTF-8 string (name_len bytes)
  - padding:   uint32 LE (typically 0)
  - file_size: uint32 LE
"""

import struct, os, json, hashlib


def parse_pkg(data: bytes) -> dict:
    if len(data) < 16:
        raise ValueError("File too small for PKG header")

    magic = data[4:8].decode("ascii", errors="replace")
    version = data[8:12].decode("ascii", errors="replace")
    entry_count = struct.unpack("<I", data[12:16])[0]

    if magic != "PKGV":
        raise ValueError(f"Invalid PKG magic: {magic}")

    info = {"magic": magic, "version": version, "entry_count": entry_count, "entries": []}

    pos = 16
    for _ in range(entry_count):
        if pos + 4 > len(data):
            break

        name_len = struct.unpack("<I", data[pos : pos + 4])[0]
        pos += 4

        if name_len == 0 or name_len > 500:
            break

        name = data[pos : pos + name_len].decode("utf-8", errors="replace").rstrip("\x00")
        pos += name_len

        if pos + 8 > len(data):
            break

        pos += 4
        file_size = struct.unpack("<I", data[pos : pos + 4])[0]
        pos += 4

        info["entries"].append({"name": name, "size": file_size})

    return info


def extract_pkg(data: bytes, output_dir: str) -> list:
    if len(data) < 16:
        raise ValueError("File too small for PKG header")

    entry_count = struct.unpack("<I", data[12:16])[0]
    os.makedirs(output_dir, exist_ok=True)

    entries = []
    pos = 16

    for _ in range(entry_count):
        if pos + 4 > len(data):
            break

        name_len = struct.unpack("<I", data[pos : pos + 4])[0]
        pos += 4

        if name_len == 0 or name_len > 500:
            break

        name = data[pos : pos + name_len].decode("utf-8", errors="replace").rstrip("\x00")
        pos += name_len

        if pos + 8 > len(data):
            break

        pos += 4
        file_size = struct.unpack("<I", data[pos : pos + 4])[0]
        pos += 4

        entries.append({"name": name, "size": file_size})

    data_pos = pos
    extracted = []

    for entry in entries:
        file_data = data[data_pos : data_pos + entry["size"]]
        filepath = os.path.join(output_dir, entry["name"])
        filedir = os.path.dirname(filepath)
        os.makedirs(filedir, exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(file_data)
        extracted.append((filepath, entry["size"]))
        data_pos += entry["size"]

    return extracted


def extract_pkg_file(pkg_path: str, output_dir: str) -> list:
    with open(pkg_path, "rb") as f:
        data = f.read()
    return extract_pkg(data, output_dir)


def get_cache_dir(pkg_path: str) -> str:
    h = hashlib.md5(pkg_path.encode()).hexdigest()[:12]
    return os.path.expanduser(f"~/.cache/tuxpaper/pkg/{h}")


def extract_to_cache(pkg_path: str) -> str | None:
    cache_dir = get_cache_dir(pkg_path)
    manifest_path = os.path.join(cache_dir, "_extracted.flag")
    if os.path.exists(manifest_path):
        return cache_dir
    try:
        extract_pkg_file(pkg_path, cache_dir)
        with open(manifest_path, "w") as f:
            f.write("1")
        return cache_dir
    except Exception as e:
        print(f"Failed to extract {pkg_path}: {e}")
        return None


def find_video_in_extracted(extract_dir: str) -> str | None:
    project_json = os.path.join(extract_dir, "project.json")
    if os.path.exists(project_json):
        try:
            with open(project_json, encoding="utf-8") as f:
                data = json.load(f)
            file_name = data.get("file", "")
            if file_name:
                video = os.path.join(extract_dir, file_name)
                if os.path.exists(video):
                    return video
        except (json.JSONDecodeError, IOError):
            pass

    for root, dirs, files in os.walk(extract_dir):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in (".mp4", ".webm", ".avi", ".mov", ".mkv"):
                return os.path.join(root, f)

    return None


def find_preview_in_extracted(extract_dir: str) -> str | None:
    for name in ("preview.jpg", "preview.png", "preview.gif", "preview.jpeg"):
        p = os.path.join(extract_dir, name)
        if os.path.exists(p):
            return p
    return None


def get_project_info(extract_dir: str) -> dict | None:
    project_json = os.path.join(extract_dir, "project.json")
    if os.path.exists(project_json):
        try:
            with open(project_json, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return None
