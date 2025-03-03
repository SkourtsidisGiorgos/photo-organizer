#!/usr/bin/env python3
"""
Photo Organizer Setup Script
This script sets up the Photo Organizer application by:
1. Installing required dependencies
2. Creating necessary directories
3. Creating shortcuts (if requested)
"""
import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

REQUIRED_PACKAGES = [
    'ttkthemes',
    'pillow',           # Image processing
    'rawpy',            # RAW image processing
    'opencv-python',    # Computer vision for blur detection
    'tqdm',             # Progress bars
    'imageio',          # Image I/O
    'humanize',         # Human-readable file sizes
    'psutil',           # System utilities for disk space
    # cloud backup dependencies
    'dropbox',          # Dropbox SDK
    'google-auth-oauthlib', # Google authentication
    'google-api-python-client', # Google Drive API
    'pydrive2',         # Alternative Google Drive library
    'boto3',            # AWS SDK for S3
    'requests',         # HTTP requests
    # ai features
    'torch',            # Deep learning framework
    'torchvision',      # Computer vision models and utilities
    #'face-recognition'  # Optional: Face recognition capabilities
]

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def install_dependencies():
    """Install required Python packages"""
    print_header("Installing Required Dependencies")
    
    for package in REQUIRED_PACKAGES:
        print(f"Installing {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✓ {package} installed successfully")
        except subprocess.CalledProcessError:
            print(f"✗ Failed to install {package}")
            return False
    
    return True

def setup_application_files():
    """Make sure all application files are in the right place"""
    print_header("Setting Up Application Files")
    
    # Get directory of this script
    setup_dir = Path(__file__).resolve().parent
    
    # Check for required Python files
    required_files = [
        "photo_organizer.py",
        "remove_duplicates.py",
        "blur_detector.py",
        "small_image_cleaner.py",
        "dng_jpg_cleaner.py",
        "raw_to_jpg.py",
        "photo_organizer_app.py",
        "splash_screen.py",
        "photo_organizer_launcher.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not (setup_dir / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("The following required files are missing:")
        for file in missing_files:
            print(f"  - {file}")
        print("\nPlease make sure all application files are in the same directory as this setup script.")
        return False
    
    resources_dir = setup_dir / "resources"
    resources_dir.mkdir(exist_ok=True)
    print(f"✓ Resources directory created/verified at {resources_dir}")

    models_dir = setup_dir / "models"
    models_dir.mkdir(exist_ok=True)
    print(f"✓ Models directory created/verified at {models_dir}")
    
    return True

def create_desktop_shortcut():
    """Create desktop shortcut based on the operating system"""
    print_header("Creating Desktop Shortcut")
    
    # Get paths
    setup_dir = Path(__file__).resolve().parent
    launcher_path = setup_dir / "photo_organizer_launcher.py"
    
    system = platform.system()
    
    if system == "Windows":
        try:
            # Use PowerShell to create a shortcut
            desktop_path = Path.home() / "Desktop"
            shortcut_path = desktop_path / "Photo Organizer.lnk"
            
            # PowerShell script to create shortcut
            ps_script = f"""
            $WshShell = New-Object -comObject WScript.Shell
            $Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
            $Shortcut.TargetPath = '{sys.executable}'
            $Shortcut.Arguments = '"{launcher_path}"'
            $Shortcut.WorkingDirectory = '{setup_dir}'
            $Shortcut.Description = 'Photo Organizer Application'
            $Shortcut.Save()
            """
            
            # Execute PowerShell script
            subprocess.run(['powershell', '-Command', ps_script], check=True)
            print(f"✓ Desktop shortcut created at {shortcut_path}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to create Windows shortcut: {e}")
            return False
            
    elif system == "Linux":
        try:
            # Create a .desktop file
            desktop_path = Path.home() / "Desktop"
            shortcut_path = desktop_path / "photo-organizer.desktop"
            
            with open(shortcut_path, 'w') as f:
                f.write(f"""[Desktop Entry]
Type=Application
Name=Photo Organizer
Comment=Organize and manage your photo collection
Exec={sys.executable} "{launcher_path}"
Path={setup_dir}
Terminal=false
Categories=Graphics;
""")
            
            # Make executable
            os.chmod(shortcut_path, 0o755)
            print(f"✓ Desktop shortcut created at {shortcut_path}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to create Linux shortcut: {e}")
            return False
            
    elif system == "Darwin":  # macOS
        try:
            # Create a simple shell script as launcher
            desktop_path = Path.home() / "Desktop"
            app_script_path = desktop_path / "Photo Organizer.command"
            
            with open(app_script_path, 'w') as f:
                f.write(f"""#!/bin/bash
cd "{setup_dir}"
"{sys.executable}" "{launcher_path}"
""")
            
            # Make executable
            os.chmod(app_script_path, 0o755)
            print(f"✓ Desktop launcher created at {app_script_path}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to create macOS launcher: {e}")
            return False
    
    else:
        print(f"✗ Unsupported operating system: {system}")
        return False

def main():
    """Main setup function"""
    print_header("Photo Organizer Setup")
    print("This script will set up the Photo Organizer application on your computer.")
    print("Press Ctrl+C at any time to cancel the setup.\n")
    
    try:
        # Install dependencies
        if not install_dependencies():
            print("\nSetup failed: Could not install required dependencies.")
            return
        
        # Setup application files
        if not setup_application_files():
            print("\nSetup failed: Missing application files.")
            return
        
        # Ask about desktop shortcut
        print("\nWould you like to create a desktop shortcut? (y/n)")
        create_shortcut = input().strip().lower() == 'y'
        
        if create_shortcut:
            create_desktop_shortcut()
        
        # Setup complete
        print_header("Setup Complete!")
        print("You can now run the Photo Organizer application by executing:")
        print(f"  python {Path(__file__).parent / 'photo_organizer_launcher.py'}")
        
        if create_shortcut:
            print("\nOr by using the desktop shortcut that was created.")
        
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        print("Setup failed.")

if __name__ == "__main__":
    main()