#!/usr/bin/env python3
"""
Test script to verify control enabling
"""

import sys
import os
sys.path.append('/home/xazel/.local/share/Tuxpaper')
os.chdir('/home/xazel/.local/share/Tuxpaper')

import customtkinter as ctk
from tuxpaper import TuxpaperApp

class TestApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Control Test")
        self.geometry("400x300")
        
        # Create some test controls
        self.test_btn = ctk.CTkButton(self, text="Test Button", state="disabled")
        self.test_btn.pack(pady=20)
        
        # Test enabling the button
        print(f"Before enabling: {self.test_btn.cget('state')}")
        self.test_btn.configure(state="normal")
        print(f"After enabling: {self.test_btn.cget('state')}")
        
        # Test if we can access the button
        print(f"Button exists: {hasattr(self, 'test_btn')}")

if __name__ == "__main__":
    app = TestApp()
    app.mainloop()