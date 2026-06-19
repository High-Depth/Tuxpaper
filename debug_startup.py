#!/usr/bin/env python3
"""
Debug script to test application startup process
"""

import sys
import os
sys.path.append('/home/xazel/.local/share/Tuxpaper')
os.chdir('/home/xazel/.local/share/Tuxpaper')

import customtkinter as ctk
from tuxpaper import TuxpaperApp, WallpaperScanner, WallpaperManager
import json

def test_startup_process():
    print("=== Testing Application Startup Process ===")
    
    # Test 1: Load settings
    print("\n1. Testing settings loading...")
    try:
        from tuxpaper import WallpaperScanner
        settings = WallpaperScanner.load_settings()
        print(f"   Settings loaded: {settings}")
    except Exception as e:
        print(f"   Error loading settings: {e}")
        return
    
    # Test 2: Load last wallpaper
    print("\n2. Testing last wallpaper loading...")
    try:
        last_wallpaper = WallpaperScanner.load_last_wallpaper()
        print(f"   Last wallpaper: {last_wallpaper}")
        if last_wallpaper and last_wallpaper.get("file_path"):
            file_path = last_wallpaper["file_path"]
            print(f"   File path: {file_path}")
            print(f"   File exists: {os.path.exists(file_path)}")
        else:
            print("   No last wallpaper found")
            return
    except Exception as e:
        print(f"   Error loading last wallpaper: {e}")
        return
    
    # Test 3: Test wallpaper application
    print("\n3. Testing wallpaper application...")
    try:
        file_path = last_wallpaper["file_path"]
        result = WallpaperManager.apply_wallpaper(file_path, False, "stretch")
        print(f"   Wallpaper application result: {result}")
        if result:
            print("   Wallpaper applied successfully!")
        else:
            print("   Wallpaper application failed")
    except Exception as e:
        print(f"   Error applying wallpaper: {e}")
        return
    
    print("\n=== Startup Process Test Complete ===")

if __name__ == "__main__":
    test_startup_process()