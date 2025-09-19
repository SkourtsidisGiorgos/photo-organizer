import tkinter as tk
from PIL import Image, ImageTk
from pathlib import Path

class SplashScreen:
    def __init__(self, parent, app_name="Photo Organizer", timeout=2000):
        self.parent = parent
        self.timeout = timeout
        
        # Hide the main window
        parent.withdraw()
        
        # Create splash screen window
        self.splash = tk.Toplevel(parent)
        self.splash.title("")
        
        # Remove title bar and make borderless
        self.splash.overrideredirect(True)
        
        # Set splash window size
        width = 500
        height = 300
        
        # Center on screen
        screen_width = self.splash.winfo_screenwidth()
        screen_height = self.splash.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.splash.geometry(f"{width}x{height}+{x}+{y}")
        
        # Create frame
        frame = tk.Frame(self.splash, bg="#f5f5f5", width=width, height=height)
        frame.pack(fill="both", expand=True)
        
        # Try to load splash image
        try:
            # Look for splash image in resources folder
            script_dir = Path(__file__).parent
            splash_image_path = script_dir / "resources" / "splash_image.png"
            
            if splash_image_path.exists():
                img = Image.open(splash_image_path)
                # Resize to fit
                img = img.resize((width-40, 150), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                # Display image
                image_label = tk.Label(frame, image=photo, bg="#f5f5f5")
                image_label.image = photo  # Keep a reference
                image_label.pack(pady=20)
            else:
                # If no image, create a text banner
                banner = tk.Label(frame, text=app_name, 
                                font=("Arial", 28, "bold"), bg="#f5f5f5", fg="#4a7abc")
                banner.pack(pady=40)
        except Exception:
            # Fallback if image loading fails
            banner = tk.Label(frame, text=app_name, 
                            font=("Arial", 28, "bold"), bg="#f5f5f5", fg="#4a7abc")
            banner.pack(pady=40)
        
        # Add app version
        version_label = tk.Label(frame, text="Version 1.0", 
                               font=("Arial", 12), bg="#f5f5f5")
        version_label.pack()
        
        # Add loading message
        loading_label = tk.Label(frame, text="Loading...", 
                               font=("Arial", 10), bg="#f5f5f5")
        loading_label.pack(pady=10)
        
        # Add progress bar
        progress = tk.Canvas(frame, width=width-100, height=20, bg="white",
                          highlightthickness=1, highlightbackground="#cccccc")
        progress.pack(pady=10)
        
        # Animate progress bar
        self.progress_bar(progress, width-100, 0)
        
        # Schedule closing the splash screen
        self.splash.after(self.timeout, self.close_splash)
    
    def progress_bar(self, canvas, width, value):
        """Animate progress bar"""
        if value < width:
            # Increment progress
            canvas.delete("progress")
            canvas.create_rectangle(0, 0, value, 20, fill="#4a7abc", tags="progress")
            
            # Schedule next update
            value += width / 100  # Create 100 animation steps
            self.splash.after(self.timeout // 100, lambda: self.progress_bar(canvas, width, value))
    
    def close_splash(self):
        """Close splash screen and show main application"""
        self.parent.deiconify()  # Show main window
        self.splash.destroy()  # Destroy splash window