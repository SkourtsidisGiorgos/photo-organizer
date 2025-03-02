#!/usr/bin/env python3
"""
Photo Organizer - A tool to organize, clean, and convert your photo collection
"""
import os
import sys
import tkinter as tk
from pathlib import Path
import importlib.util

# Add parent directory to path so we can import necessary modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Check for required packages
REQUIRED_PACKAGES = [
    ('PIL', 'pillow'),           # Image processing
    ('rawpy', 'rawpy'),          # RAW image processing
    ('cv2', 'opencv-python'),    # Computer vision for blur detection
    ('tqdm', 'tqdm'),            # Progress bars
    ('imageio', 'imageio'),      # Image I/O
    ('humanize', 'humanize'),    # Human-readable file sizes
    ('psutil', 'psutil')         # System utilities for disk space
]

def check_dependencies():
    """Check if required packages are installed, offer to install if missing"""
    missing_packages = []
    
    for package_name, pip_name in REQUIRED_PACKAGES:
        try:
            importlib.util.find_spec(package_name)
        except ImportError:
            missing_packages.append((package_name, pip_name))
    
    if missing_packages:
        print("Missing required packages:")
        for package_name, pip_name in missing_packages:
            print(f"  - {package_name}")
        
        print("\nWould you like to install them now? (y/n)")
        response = input().strip().lower()
        
        if response == 'y':
            import subprocess
            
            for _, pip_name in missing_packages:
                print(f"Installing {pip_name}...")
                subprocess.call([sys.executable, "-m", "pip", "install", pip_name])
            
            print("All packages installed. Restarting application...")
            # Restart the application
            os.execv(sys.executable, ['python'] + sys.argv)
        else:
            print("Cannot continue without required packages. Exiting.")
            sys.exit(1)

def create_resources_dir():
    """Create resources directory if it doesn't exist"""
    script_dir = Path(__file__).parent
    resources_dir = script_dir / "resources"
    
    if not resources_dir.exists():
        resources_dir.mkdir()
        print(f"Created resources directory: {resources_dir}")
    
    # Check for splash image
    splash_image = resources_dir / "splash_image.png"
    if not splash_image.exists():
        # Create a simple placeholder splash image if possible
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a blank image
            img = Image.new('RGB', (460, 150), color=(245, 245, 245))
            d = ImageDraw.Draw(img)
            
            # Try to use a nice font
            try:
                # Different font options for different platforms
                font_options = [
                    ("Arial.ttf", 40),
                    ("DejaVuSans.ttf", 40),
                    ("FreeSans.ttf", 40)
                ]
                
                font = None
                for font_name, size in font_options:
                    try:
                        font = ImageFont.truetype(font_name, size)
                        break
                    except IOError:
                        continue
                
                if font is None:
                    font = ImageFont.load_default()
            except Exception:
                font = ImageFont.load_default()
            
            # Draw text
            d.text((20, 50), "Photo Organizer", fill=(74, 122, 188), font=font)
            
            # Save the image
            img.save(str(splash_image))
            print(f"Created placeholder splash image")
        except Exception as e:
            print(f"Could not create splash image: {e}")

def main():
    """Main application entry point"""
    # Check dependencies
    check_dependencies()
    
    # Create resources directory
    create_resources_dir()
    
    # Import the application modules (after dependencies are checked)
    from photo_organizer_app import PhotoOrganizerApp
    from splash_screen import SplashScreen
    
    # Create main window
    root = tk.Tk()
    
    # Show splash screen
    splash = SplashScreen(root)
    
    # Create app (this will be shown after splash screen closes)
    app = PhotoOrganizerApp(root)
    
    # Start main loop
    root.mainloop()

if __name__ == "__main__":
    main()