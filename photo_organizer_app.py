import sys
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
import queue
import time
from PIL import Image, ImageTk
from cloud_backup_ui import CloudBackupTab
from ai_features import add_ai_features_to_app

# Import functionality from existing scripts
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from photo_organizer import PhotoOrganizer
from remove_duplicates import DuplicateCleaner
from blur_detector import BlurryImageCleaner
from small_image_cleaner import SmallImageCleaner
from dng_jpg_cleaner import DNGJPGCleaner
from raw_to_jpg import convert_raw_to_jpg

class PhotoOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Photo Organizer")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Set theme and style
        self.style = ttk.Style()
        self.style.theme_use('clam')  # Use a modern theme
        
        # Configure colors
        self.style.configure('TFrame', background='#f5f5f5')
        self.style.configure('TButton', font=('Arial', 10), background='#4a7abc')
        self.style.configure('TLabel', font=('Arial', 10), background='#f5f5f5')
        self.style.configure('Header.TLabel', font=('Arial', 14, 'bold'), background='#f5f5f5')
        self.style.configure('Subheader.TLabel', font=('Arial', 12, 'bold'), background='#f5f5f5')
        
        # Create message queue for background threads
        self.message_queue = queue.Queue()
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.organize_tab = ttk.Frame(self.notebook)
        self.clean_tab = ttk.Frame(self.notebook)
        self.convert_tab = ttk.Frame(self.notebook)
        self.cloud_tab = ttk.Frame(self.notebook)  # New cloud backup tab
        self.settings_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.organize_tab, text="Organize Photos")
        self.notebook.add(self.clean_tab, text="Clean Photos")
        self.notebook.add(self.convert_tab, text="Convert Photos")
        self.notebook.add(self.cloud_tab, text="Cloud Backup")  # Add the new tab
        self.notebook.add(self.settings_tab, text="Settings")
        
        self.setup_organize_tab()
        self.setup_clean_tab()
        self.setup_convert_tab()
        self.setup_cloud_tab() 
        self.setup_settings_tab()
                
        # Create status bar
        self.status_frame = ttk.Frame(root)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=5)
        
        self.status_label = ttk.Label(self.status_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT)
        
        self.progress_bar = ttk.Progressbar(self.status_frame, mode='determinate', length=200)
        self.progress_bar.pack(side=tk.RIGHT, padx=10)
        
        self.process_messages()
        self.operation_running = False
        self.ai_features = add_ai_features_to_app(self)
        
        # Load app icon if available
        try:
            icon_path = Path(__file__).parent / "resources" / "photo_organizer_icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

    def setup_organize_tab(self):
        # Create organize frame
        frame = ttk.Frame(self.organize_tab)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header
        header = ttk.Label(frame, text="Organize Photos by Date", style='Header.TLabel')
        header.pack(pady=10)
        
        description = ttk.Label(frame, text="Organize your photos into Year/Month folders based on EXIF data or file creation date.")
        description.pack(pady=5)
        
        # Source directory selection
        source_frame = ttk.Frame(frame)
        source_frame.pack(fill=tk.X, pady=10)
        
        source_label = ttk.Label(source_frame, text="Source Directory:")
        source_label.pack(side=tk.LEFT, padx=5)
        
        self.source_var = tk.StringVar()
        source_entry = ttk.Entry(source_frame, textvariable=self.source_var, width=50)
        source_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        source_button = ttk.Button(source_frame, text="Browse...", command=self.browse_source)
        source_button.pack(side=tk.LEFT, padx=5)
        
        # Destination directory selection
        dest_frame = ttk.Frame(frame)
        dest_frame.pack(fill=tk.X, pady=10)
        
        dest_label = ttk.Label(dest_frame, text="Destination Directory:")
        dest_label.pack(side=tk.LEFT, padx=5)
        
        self.dest_var = tk.StringVar()
        dest_entry = ttk.Entry(dest_frame, textvariable=self.dest_var, width=50)
        dest_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        dest_button = ttk.Button(dest_frame, text="Browse...", command=self.browse_dest)
        dest_button.pack(side=tk.LEFT, padx=5)
        
        # Options
        options_frame = ttk.LabelFrame(frame, text="Options")
        options_frame.pack(fill=tk.X, pady=10, padx=5)
        
        self.move_var = tk.BooleanVar(value=False)
        move_check = ttk.Checkbutton(options_frame, text="Move files (instead of copy)", variable=self.move_var)
        move_check.pack(anchor=tk.W, padx=5, pady=5)
        
        self.dry_run_var = tk.BooleanVar(value=True)
        dry_run_check = ttk.Checkbutton(options_frame, text="Dry run (simulate without making changes)", variable=self.dry_run_var)
        dry_run_check.pack(anchor=tk.W, padx=5, pady=5)
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=20)
        
        self.organize_button = ttk.Button(button_frame, text="Organize Photos", command=self.run_organizer)
        self.organize_button.pack(side=tk.RIGHT, padx=5)
        
        log_frame = ttk.LabelFrame(frame, text="Log")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=5)
        
        self.organize_log = tk.Text(log_frame, height=10, width=80, wrap=tk.WORD)
        self.organize_log.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
        
        # Add scrollbar to log
        scrollbar = ttk.Scrollbar(self.organize_log, command=self.organize_log.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.organize_log.config(yscrollcommand=scrollbar.set)
        
        # Make log read-only
        self.organize_log.config(state=tk.DISABLED)

    def run_small_cleaner(self):
        """Run small image cleaner in background thread"""
        if self.operation_running:
            messagebox.showinfo("Operation in Progress", "Please wait for the current operation to complete.")
            return
        
        # Get input values
        directory = self.small_dir_var.get()
        max_dimension = self.small_dimension_var.get()
        dry_run = self.small_dry_run_var.get()
        
        # Validate inputs
        if not directory:
            messagebox.showerror("Error", "Please specify a directory to scan.")
            return
        
        if not Path(directory).exists():
            messagebox.showerror("Error", "Directory does not exist.")
            return
        
        # Confirm if not dry run
        if not dry_run:
            confirm = messagebox.askyesno(
                "Confirm Delete",
                "WARNING: This will permanently delete small images. Continue?",
                icon='warning'
            )
            if not confirm:
                return
        
        # Clear log
        self.clean_log.config(state=tk.NORMAL)
        self.clean_log.delete(1.0, tk.END)
        self.clean_log.config(state=tk.DISABLED)
        
        # Disable buttons during operation
        self.small_button.config(state=tk.DISABLED)
        self.operation_running = True
        
        # Create thread
        operation_thread = threading.Thread(
            target=self._small_cleaner_thread,
            args=(directory, max_dimension, dry_run)
        )
        operation_thread.daemon = True
        operation_thread.start()
    
    def _small_cleaner_thread(self, directory, max_dimension, dry_run):
        """Background thread for small image cleaning"""
        try:
            # Update status
            self.message_queue.put({
                "type": "status",
                "text": "Finding small photos..."
            })
            
            # Redirect stdout
            class PrintRedirector:
                def __init__(self, queue, widget):
                    self.queue = queue
                    self.widget = widget
                
                def write(self, text):
                    if text.strip():  # Only process non-empty text
                        self.queue.put({
                            "type": "log",
                            "widget": self.widget,
                            "text": text.rstrip()
                        })
                
                def flush(self):
                    pass
            
            original_stdout = sys.stdout
            sys.stdout = PrintRedirector(self.message_queue, self.clean_log)
            
            try:
                cleaner = SmallImageCleaner(Path(directory), max_dimension, dry_run)
                cleaner.clean_small_images()
            finally:
                # Restore stdout
                sys.stdout = original_stdout
            
            self.message_queue.put({
                "type": "status",
                "text": "Small image cleaning complete!"
            })
            
        except Exception as e:
            self.message_queue.put({
                "type": "log",
                "widget": self.clean_log,
                "text": f"Error: {str(e)}"
            })
            
            self.message_queue.put({
                "type": "status",
                "text": "Error during small image cleaning."
            })
        
        finally:
            self.message_queue.put({
                "type": "complete",
                "value": None
            })
    
    def run_dng_cleaner(self):
        """Run DNG/JPG cleaner in background thread"""
        if self.operation_running:
            messagebox.showinfo("Operation in Progress", "Please wait for the current operation to complete.")
            return
        
        # Get input values
        directory = self.dng_dir_var.get()
        dry_run = self.dng_dry_run_var.get()
        
        # Validate inputs
        if not directory:
            messagebox.showerror("Error", "Please specify a directory to scan.")
            return
        
        if not Path(directory).exists():
            messagebox.showerror("Error", "Directory does not exist.")
            return
        
        if not dry_run:
            confirm = messagebox.askyesno(
                "Confirm Delete",
                "WARNING: This will permanently delete JPG files paired with DNG files. Continue?",
                icon='warning'
            )
            if not confirm:
                return
        
        # Clear log
        self.clean_log.config(state=tk.NORMAL)
        self.clean_log.delete(1.0, tk.END)
        self.clean_log.config(state=tk.DISABLED)
        
        # Disable buttons during operation
        self.dng_button.config(state=tk.DISABLED)
        self.operation_running = True
        
        # Create thread
        operation_thread = threading.Thread(
            target=self._dng_cleaner_thread,
            args=(directory, dry_run)
        )
        operation_thread.daemon = True
        operation_thread.start()
    
    def _dng_cleaner_thread(self, directory, dry_run):
        """Background thread for DNG/JPG cleaning"""
        try:
            # Update status
            self.message_queue.put({
                "type": "status",
                "text": "Finding DNG/JPG pairs..."
            })
            
            # Redirect stdout
            class PrintRedirector:
                def __init__(self, queue, widget):
                    self.queue = queue
                    self.widget = widget
                
                def write(self, text):
                    if text.strip():  # Only process non-empty text
                        self.queue.put({
                            "type": "log",
                            "widget": self.widget,
                            "text": text.rstrip()
                        })
                
                def flush(self):
                    pass
            
            original_stdout = sys.stdout
            sys.stdout = PrintRedirector(self.message_queue, self.clean_log)
            
            try:
                cleaner = DNGJPGCleaner(Path(directory), dry_run)
                cleaner.clean_pairs()
            finally:
                sys.stdout = original_stdout
            
            self.message_queue.put({
                "type": "status",
                "text": "DNG/JPG cleaning complete!"
            })
            
        except Exception as e:
            self.message_queue.put({
                "type": "log",
                "widget": self.clean_log,
                "text": f"Error: {str(e)}"
            })
            
            self.message_queue.put({
                "type": "status",
                "text": "Error during DNG/JPG cleaning."
            })
        
        finally:
            self.message_queue.put({
                "type": "complete",
                "value": None
            })
    
    def run_raw_converter(self):
        """Run RAW to JPG converter in background thread"""
        if self.operation_running:
            messagebox.showinfo("Operation in Progress", "Please wait for the current operation to complete.")
            return
        
        # Get input values
        source_dir = self.raw_source_var.get()
        dest_dir = self.raw_dest_var.get()
        quality = self.jpg_quality_var.get()
        
        # Validate inputs
        if not source_dir or not dest_dir:
            messagebox.showerror("Error", "Please specify both source and destination directories.")
            return
        
        if not Path(source_dir).exists():
            messagebox.showerror("Error", "Source directory does not exist.")
            return
        
        # Clear log
        self.convert_log.config(state=tk.NORMAL)
        self.convert_log.delete(1.0, tk.END)
        self.convert_log.config(state=tk.DISABLED)
        
        # Disable buttons during operation
        self.convert_button.config(state=tk.DISABLED)
        self.operation_running = True
        
        # Create thread
        operation_thread = threading.Thread(
            target=self._raw_converter_thread,
            args=(source_dir, dest_dir, quality)
        )
        operation_thread.daemon = True
        operation_thread.start()
    
    def _raw_converter_thread(self, source_dir, dest_dir, quality):
        """Background thread for RAW to JPG conversion"""
        try:
            # Update status
            self.message_queue.put({
                "type": "status",
                "text": "Converting RAW photos to JPG..."
            })
            
            # Redirect stdout
            class PrintRedirector:
                def __init__(self, queue, widget):
                    self.queue = queue
                    self.widget = widget
                
                def write(self, text):
                    if text.strip():  # Only process non-empty text
                        self.queue.put({
                            "type": "log",
                            "widget": self.widget,
                            "text": text.rstrip()
                        })
                
                def flush(self):
                    pass
            
            original_stdout = sys.stdout
            sys.stdout = PrintRedirector(self.message_queue, self.convert_log)
            
            try:
                # Run converter
                converted, errors = convert_raw_to_jpg(source_dir, dest_dir, quality)
                
                print("\nConversion Summary")
                print("-" * 50)
                print(f"Successfully converted: {converted} files")
                print(f"Errors encountered: {errors} files")
                print(f"Total files processed: {converted + errors}")
                
            finally:
                # Restore stdout
                sys.stdout = original_stdout
            
            self.message_queue.put({
                "type": "status",
                "text": "RAW to JPG conversion complete!"
            })
            
        except Exception as e:
            self.message_queue.put({
                "type": "log",
                "widget": self.convert_log,
                "text": f"Error: {str(e)}"
            })
            
            self.message_queue.put({
                "type": "status",
                "text": "Error during RAW to JPG conversion."
            })
        
        finally:
            self.message_queue.put({
                "type": "complete",
                "value": None
            })
    
    def run_duplicate_cleaner(self):
        """Run duplicate cleaner in background thread"""
        if self.operation_running:
            messagebox.showinfo("Operation in Progress", "Please wait for the current operation to complete.")
            return
        
        # Get input values
        directory = self.dup_dir_var.get()
        dry_run = self.dup_dry_run_var.get()
        
        # Validate inputs
        if not directory:
            messagebox.showerror("Error", "Please specify a directory to scan.")
            return
        
        if not Path(directory).exists():
            messagebox.showerror("Error", "Directory does not exist.")
            return
        
        # Confirm if not dry run
        if not dry_run:
            confirm = messagebox.askyesno(
                "Confirm Delete",
                "WARNING: This will permanently delete duplicate files. Continue?",
                icon='warning'
            )
            if not confirm:
                return
        
        # Clear log
        self.clean_log.config(state=tk.NORMAL)
        self.clean_log.delete(1.0, tk.END)
        self.clean_log.config(state=tk.DISABLED)
        
        # Disable buttons during operation
        self.duplicate_button.config(state=tk.DISABLED)
        self.operation_running = True
        
        # Create thread
        operation_thread = threading.Thread(
            target=self._duplicate_cleaner_thread,
            args=(directory, dry_run)
        )
        operation_thread.daemon = True
        operation_thread.start()
    
    def _duplicate_cleaner_thread(self, directory, dry_run):
        """Background thread for duplicate cleaning"""
        try:
            # Update status
            self.message_queue.put({
                "type": "status",
                "text": "Finding duplicate photos..."
            })
            
            # Redirect stdout
            class PrintRedirector:
                def __init__(self, queue, widget):
                    self.queue = queue
                    self.widget = widget
                
                def write(self, text):
                    if text.strip():  # Only process non-empty text
                        self.queue.put({
                            "type": "log",
                            "widget": self.widget,
                            "text": text.rstrip()
                        })
                
                def flush(self):
                    pass
            
            original_stdout = sys.stdout
            sys.stdout = PrintRedirector(self.message_queue, self.clean_log)
            
            try:
                cleaner = DuplicateCleaner(Path(directory), dry_run)
                cleaner.clean_duplicates()
            finally:
                # Restore stdout
                sys.stdout = original_stdout
            
            self.message_queue.put({
                "type": "status",
                "text": "Duplicate cleaning complete!"
            })
            
        except Exception as e:
            self.message_queue.put({
                "type": "log",
                "widget": self.clean_log,
                "text": f"Error: {str(e)}"
            })
            
            self.message_queue.put({
                "type": "status",
                "text": "Error during duplicate cleaning."
            })
        
        finally:
            self.message_queue.put({
                "type": "complete",
                "value": None
            })
    
    def run_blur_cleaner(self):
        """Run blur cleaner in background thread"""
        if self.operation_running:
            messagebox.showinfo("Operation in Progress", "Please wait for the current operation to complete.")
            return
        
        # Get input values
        directory = self.blur_dir_var.get()
        threshold = self.blur_threshold_var.get()
        dry_run = self.blur_dry_run_var.get()
        
        # Validate inputs
        if not directory:
            messagebox.showerror("Error", "Please specify a directory to scan.")
            return
        
        if not Path(directory).exists():
            messagebox.showerror("Error", "Directory does not exist.")
            return
        
        # Confirm if not dry run
        if not dry_run:
            confirm = messagebox.askyesno(
                "Confirm Delete",
                "WARNING: This will permanently delete blurry images. Continue?",
                icon='warning'
            )
            if not confirm:
                return
        
        # Clear log
        self.clean_log.config(state=tk.NORMAL)
        self.clean_log.delete(1.0, tk.END)
        self.clean_log.config(state=tk.DISABLED)
        
        # Disable buttons during operation
        self.blur_button.config(state=tk.DISABLED)
        self.operation_running = True
        
        # Create thread
        operation_thread = threading.Thread(
            target=self._blur_cleaner_thread,
            args=(directory, threshold, dry_run)
        )
        operation_thread.daemon = True
        operation_thread.start()
    
    def _blur_cleaner_thread(self, directory, threshold, dry_run):
        """Background thread for blur cleaning"""
        try:
            # Update status
            self.message_queue.put({
                "type": "status",
                "text": "Finding blurry photos..."
            })
            
            # Redirect stdout
            class PrintRedirector:
                def __init__(self, queue, widget):
                    self.queue = queue
                    self.widget = widget
                
                def write(self, text):
                    if text.strip():  # Only process non-empty text
                        self.queue.put({
                            "type": "log",
                            "widget": self.widget,
                            "text": text.rstrip()
                        })
                
                def flush(self):
                    pass
            
            original_stdout = sys.stdout
            sys.stdout = PrintRedirector(self.message_queue, self.clean_log)
            
            try:
                cleaner = BlurryImageCleaner(Path(directory), threshold, dry_run)
                cleaner.clean_blurry_images()
            finally:
                sys.stdout = original_stdout
            
            self.message_queue.put({
                "type": "status",
                "text": "Blur cleaning complete!"
            })
            
        except Exception as e:
            self.message_queue.put({
                "type": "log",
                "widget": self.clean_log,
                "text": f"Error: {str(e)}"
            })
            
            self.message_queue.put({
                "type": "status",
                "text": "Error during blur cleaning."
            })
        
        finally:
            self.message_queue.put({
                "type": "complete",
                "value": None
            })

    def browse_source(self):
        """Open file dialog to select source directory"""
        directory = filedialog.askdirectory(title="Select Source Directory")
        if directory:
            self.source_var.set(directory)

    def browse_dest(self):
        """Open file dialog to select destination directory"""
        directory = filedialog.askdirectory(title="Select Destination Directory")
        if directory:
            self.dest_var.set(directory)

    def browse_directory(self, string_var):
        """Generic function to browse for a directory"""
        directory = filedialog.askdirectory(title="Select Directory")
        if directory:
            string_var.set(directory)

    def setup_cloud_tab(self):
        self.cloud_backup_ui = CloudBackupTab(self.cloud_tab, self.message_queue)


    def setup_clean_tab(self):
        # Create notebook for different cleaning options
        clean_notebook = ttk.Notebook(self.clean_tab)
        clean_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create frames for each cleaning option
        duplicate_frame = ttk.Frame(clean_notebook)
        blur_frame = ttk.Frame(clean_notebook)
        small_frame = ttk.Frame(clean_notebook)
        dng_jpg_frame = ttk.Frame(clean_notebook)
        
        clean_notebook.add(duplicate_frame, text="Remove Duplicates")
        clean_notebook.add(blur_frame, text="Remove Blurry Photos")
        clean_notebook.add(small_frame, text="Remove Small Photos")
        clean_notebook.add(dng_jpg_frame, text="Clean DNG+JPG Pairs")
        
        # Setup each cleaning option
        self.setup_duplicate_frame(duplicate_frame)
        self.setup_blur_frame(blur_frame)
        self.setup_small_frame(small_frame)
        self.setup_dng_jpg_frame(dng_jpg_frame)
        
        # Create common log area for cleaning operations
        log_frame = ttk.LabelFrame(self.clean_tab, text="Log")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=20)
        
        self.clean_log = tk.Text(log_frame, height=10, width=80, wrap=tk.WORD)
        self.clean_log.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
        
        # Add scrollbar to log
        scrollbar = ttk.Scrollbar(self.clean_log, command=self.clean_log.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.clean_log.config(yscrollcommand=scrollbar.set)
        
        # Make log read-only
        self.clean_log.config(state=tk.DISABLED)

    def setup_duplicate_frame(self, parent):
        # Directory selection
        dir_frame = ttk.Frame(parent)
        dir_frame.pack(fill=tk.X, pady=10, padx=10)
        
        dir_label = ttk.Label(dir_frame, text="Directory:")
        dir_label.pack(side=tk.LEFT, padx=5)
        
        self.dup_dir_var = tk.StringVar()
        dir_entry = ttk.Entry(dir_frame, textvariable=self.dup_dir_var, width=50)
        dir_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        dir_button = ttk.Button(dir_frame, text="Browse...", 
                               command=lambda: self.browse_directory(self.dup_dir_var))
        dir_button.pack(side=tk.LEFT, padx=5)
        
        # Options
        options_frame = ttk.LabelFrame(parent, text="Options")
        options_frame.pack(fill=tk.X, pady=10, padx=10)
        
        self.dup_dry_run_var = tk.BooleanVar(value=True)
        dry_run_check = ttk.Checkbutton(options_frame, 
                                       text="Dry run (simulate without making changes)", 
                                       variable=self.dup_dry_run_var)
        dry_run_check.pack(anchor=tk.W, padx=5, pady=5)
        
        # Description and warning
        desc_frame = ttk.Frame(parent)
        desc_frame.pack(fill=tk.X, pady=10, padx=10)
        
        desc_label = ttk.Label(desc_frame, 
                              text="This tool will find duplicate files based on name patterns, size, and content.\n"
                                  "It keeps the oldest file and removes duplicates.")
        desc_label.pack(pady=5)
        
        warning_label = ttk.Label(desc_frame, 
                                 text="Warning: Always run with 'Dry run' first to see what will be deleted!", 
                                 foreground='red')
        warning_label.pack(pady=5)
        
        # Run button
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=10, padx=10)
        
        self.duplicate_button = ttk.Button(button_frame, text="Find & Remove Duplicates", 
                                        command=self.run_duplicate_cleaner)
        self.duplicate_button.pack(side=tk.RIGHT, padx=5)

    def setup_blur_frame(self, parent):
        # Directory selection
        dir_frame = ttk.Frame(parent)
        dir_frame.pack(fill=tk.X, pady=10, padx=10)
        
        dir_label = ttk.Label(dir_frame, text="Directory:")
        dir_label.pack(side=tk.LEFT, padx=5)
        
        self.blur_dir_var = tk.StringVar()
        dir_entry = ttk.Entry(dir_frame, textvariable=self.blur_dir_var, width=50)
        dir_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        dir_button = ttk.Button(dir_frame, text="Browse...", 
                               command=lambda: self.browse_directory(self.blur_dir_var))
        dir_button.pack(side=tk.LEFT, padx=5)
        
        # Threshold slider
        threshold_frame = ttk.Frame(parent)
        threshold_frame.pack(fill=tk.X, pady=10, padx=10)
        
        threshold_label = ttk.Label(threshold_frame, text="Blur Threshold:")
        threshold_label.pack(side=tk.LEFT, padx=5)
        
        self.blur_threshold_var = tk.DoubleVar(value=100.0)
        threshold_scale = ttk.Scale(threshold_frame, from_=50.0, to=200.0, 
                                   variable=self.blur_threshold_var, orient=tk.HORIZONTAL, length=200)
        threshold_scale.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        threshold_value = ttk.Label(threshold_frame, textvariable=self.blur_threshold_var)
        threshold_value.pack(side=tk.LEFT, padx=5)
        
        # Options
        options_frame = ttk.LabelFrame(parent, text="Options")
        options_frame.pack(fill=tk.X, pady=10, padx=10)
        
        self.blur_dry_run_var = tk.BooleanVar(value=True)
        dry_run_check = ttk.Checkbutton(options_frame, 
                                       text="Dry run (simulate without making changes)", 
                                       variable=self.blur_dry_run_var)
        dry_run_check.pack(anchor=tk.W, padx=5, pady=5)
        
        # Description and warning
        desc_frame = ttk.Frame(parent)
        desc_frame.pack(fill=tk.X, pady=10, padx=10)
        
        desc_label = ttk.Label(desc_frame, 
                              text="This tool will detect and remove blurry images.\n"
                                  "Lower threshold = more aggressive (removes more images).")
        desc_label.pack(pady=5)
        
        warning_label = ttk.Label(desc_frame, 
                                 text="Warning: Always run with 'Dry run' first to see what will be deleted!", 
                                 foreground='red')
        warning_label.pack(pady=5)
        
        # Run button
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=10, padx=10)
        
        self.blur_button = ttk.Button(button_frame, text="Find & Remove Blurry Images", 
                                     command=self.run_blur_cleaner)
        self.blur_button.pack(side=tk.RIGHT, padx=5)

    def setup_small_frame(self, parent):
        # Directory selection
        dir_frame = ttk.Frame(parent)
        dir_frame.pack(fill=tk.X, pady=10, padx=10)
        
        dir_label = ttk.Label(dir_frame, text="Directory:")
        dir_label.pack(side=tk.LEFT, padx=5)
        
        self.small_dir_var = tk.StringVar()
        dir_entry = ttk.Entry(dir_frame, textvariable=self.small_dir_var, width=50)
        dir_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        dir_button = ttk.Button(dir_frame, text="Browse...", 
                              command=lambda: self.browse_directory(self.small_dir_var))
        dir_button.pack(side=tk.LEFT, padx=5)
        
        # Max dimension slider
        dim_frame = ttk.Frame(parent)
        dim_frame.pack(fill=tk.X, pady=10, padx=10)
        
        dim_label = ttk.Label(dim_frame, text="Max Dimension (px):")
        dim_label.pack(side=tk.LEFT, padx=5)
        
        self.small_dimension_var = tk.IntVar(value=400)
        dim_scale = ttk.Scale(dim_frame, from_=100, to=1000, 
                           variable=self.small_dimension_var, orient=tk.HORIZONTAL, length=200)
        dim_scale.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        dim_value = ttk.Label(dim_frame, textvariable=self.small_dimension_var)
        dim_value.pack(side=tk.LEFT, padx=5)
        
        # Options
        options_frame = ttk.LabelFrame(parent, text="Options")
        options_frame.pack(fill=tk.X, pady=10, padx=10)
        
        self.small_dry_run_var = tk.BooleanVar(value=True)
        dry_run_check = ttk.Checkbutton(options_frame, 
                                      text="Dry run (simulate without making changes)", 
                                      variable=self.small_dry_run_var)
        dry_run_check.pack(anchor=tk.W, padx=5, pady=5)
        
        # Description and warning
        desc_frame = ttk.Frame(parent)
        desc_frame.pack(fill=tk.X, pady=10, padx=10)
        
        desc_label = ttk.Label(desc_frame, 
                             text="This tool finds and removes images that are smaller than the specified dimension.\n"
                                 "Images with both width AND height smaller than this value will be removed.")
        desc_label.pack(pady=5)
        
        warning_label = ttk.Label(desc_frame, 
                                text="Warning: Always run with 'Dry run' first to see what will be deleted!", 
                                foreground='red')
        warning_label.pack(pady=5)
        
        # Run button
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=10, padx=10)
        
        self.small_button = ttk.Button(button_frame, text="Find & Remove Small Images", 
                                    command=self.run_small_cleaner)
        self.small_button.pack(side=tk.RIGHT, padx=5)

    def setup_dng_jpg_frame(self, parent):
        # Directory selection
        dir_frame = ttk.Frame(parent)
        dir_frame.pack(fill=tk.X, pady=10, padx=10)
        
        dir_label = ttk.Label(dir_frame, text="Directory:")
        dir_label.pack(side=tk.LEFT, padx=5)
        
        self.dng_dir_var = tk.StringVar()
        dir_entry = ttk.Entry(dir_frame, textvariable=self.dng_dir_var, width=50)
        dir_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        dir_button = ttk.Button(dir_frame, text="Browse...", 
                             command=lambda: self.browse_directory(self.dng_dir_var))
        dir_button.pack(side=tk.LEFT, padx=5)
        
        # Options
        options_frame = ttk.LabelFrame(parent, text="Options")
        options_frame.pack(fill=tk.X, pady=10, padx=10)
        
        self.dng_dry_run_var = tk.BooleanVar(value=True)
        dry_run_check = ttk.Checkbutton(options_frame, 
                                     text="Dry run (simulate without making changes)", 
                                     variable=self.dng_dry_run_var)
        dry_run_check.pack(anchor=tk.W, padx=5, pady=5)
        
        # Description and warning
        desc_frame = ttk.Frame(parent)
        desc_frame.pack(fill=tk.X, pady=10, padx=10)
        
        desc_label = ttk.Label(desc_frame, 
                            text="This tool finds pairs of DNG and JPG files (same image) and removes the JPG file.\n"
                                "Useful for freeing space when you have both RAW and JPG versions.")
        desc_label.pack(pady=5)
        
        warning_label = ttk.Label(desc_frame, 
                               text="Warning: Always run with 'Dry run' first to see what will be deleted!", 
                               foreground='red')
        warning_label.pack(pady=5)
        
        # Run button
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=10, padx=10)
        
        self.dng_button = ttk.Button(button_frame, text="Find & Remove JPG Duplicates", 
                                  command=self.run_dng_cleaner)
        self.dng_button.pack(side=tk.RIGHT, padx=5)

    def setup_convert_tab(self):
        # Create convert frame
        frame = ttk.Frame(self.convert_tab)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header
        header = ttk.Label(frame, text="Convert RAW Photos to JPG", style='Header.TLabel')
        header.pack(pady=10)
        
        description = ttk.Label(frame, text="Convert RAW format photos (CR2, NEF, ARW, etc.) to high-quality JPG format.")
        description.pack(pady=5)
        
        # Source directory selection
        source_frame = ttk.Frame(frame)
        source_frame.pack(fill=tk.X, pady=10)
        
        source_label = ttk.Label(source_frame, text="RAW Files Directory:")
        source_label.pack(side=tk.LEFT, padx=5)
        
        self.raw_source_var = tk.StringVar()
        source_entry = ttk.Entry(source_frame, textvariable=self.raw_source_var, width=50)
        source_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        source_button = ttk.Button(source_frame, text="Browse...", 
                                 command=lambda: self.browse_directory(self.raw_source_var))
        source_button.pack(side=tk.LEFT, padx=5)
        
        # Destination directory selection
        dest_frame = ttk.Frame(frame)
        dest_frame.pack(fill=tk.X, pady=10)
        
        dest_label = ttk.Label(dest_frame, text="Output JPG Directory:")
        dest_label.pack(side=tk.LEFT, padx=5)
        
        self.raw_dest_var = tk.StringVar()
        dest_entry = ttk.Entry(dest_frame, textvariable=self.raw_dest_var, width=50)
        dest_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        dest_button = ttk.Button(dest_frame, text="Browse...", 
                              command=lambda: self.browse_directory(self.raw_dest_var))
        dest_button.pack(side=tk.LEFT, padx=5)
        
        # Quality slider
        quality_frame = ttk.Frame(frame)
        quality_frame.pack(fill=tk.X, pady=10)
        
        quality_label = ttk.Label(quality_frame, text="JPG Quality (1-100):")
        quality_label.pack(side=tk.LEFT, padx=5)
        
        self.jpg_quality_var = tk.IntVar(value=95)
        quality_scale = ttk.Scale(quality_frame, from_=70, to=100, 
                                variable=self.jpg_quality_var, orient=tk.HORIZONTAL, length=200)
        quality_scale.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        quality_value = ttk.Label(quality_frame, textvariable=self.jpg_quality_var)
        quality_value.pack(side=tk.LEFT, padx=5)
        
        # Run button
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=20)
        
        self.convert_button = ttk.Button(button_frame, text="Convert RAW to JPG", 
                                      command=self.run_raw_converter)
        self.convert_button.pack(side=tk.RIGHT, padx=5)
        
        log_frame = ttk.LabelFrame(frame, text="Log")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=5)
        
        self.convert_log = tk.Text(log_frame, height=10, width=80, wrap=tk.WORD)
        self.convert_log.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
        
        # Add scrollbar to log
        scrollbar = ttk.Scrollbar(self.convert_log, command=self.convert_log.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.convert_log.config(yscrollcommand=scrollbar.set)
        
        # Make log read-only
        self.convert_log.config(state=tk.DISABLED)

    def setup_settings_tab(self):
        # Create settings frame
        frame = ttk.Frame(self.settings_tab)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header
        header = ttk.Label(frame, text="Application Settings", style='Header.TLabel')
        header.pack(pady=10)
        
        # Default directories section
        dir_frame = ttk.LabelFrame(frame, text="Default Directories")
        dir_frame.pack(fill=tk.X, pady=10, padx=5)
        
        # Default source directory
        default_source_frame = ttk.Frame(dir_frame)
        default_source_frame.pack(fill=tk.X, pady=10, padx=5)
        
        default_source_label = ttk.Label(default_source_frame, text="Default Source Directory:")
        default_source_label.pack(side=tk.LEFT, padx=5)
        
        self.default_source_var = tk.StringVar()
        default_source_entry = ttk.Entry(default_source_frame, textvariable=self.default_source_var, width=50)
        default_source_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        default_source_button = ttk.Button(default_source_frame, text="Browse...", 
                                       command=lambda: self.browse_directory(self.default_source_var))
        default_source_button.pack(side=tk.LEFT, padx=5)
        
        # Default destination directory
        default_dest_frame = ttk.Frame(dir_frame)
        default_dest_frame.pack(fill=tk.X, pady=10, padx=5)
        
        default_dest_label = ttk.Label(default_dest_frame, text="Default Output Directory:")
        default_dest_label.pack(side=tk.LEFT, padx=5)
        
        self.default_dest_var = tk.StringVar()
        default_dest_entry = ttk.Entry(default_dest_frame, textvariable=self.default_dest_var, width=50)
        default_dest_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        default_dest_button = ttk.Button(default_dest_frame, text="Browse...", 
                                     command=lambda: self.browse_directory(self.default_dest_var))
        default_dest_button.pack(side=tk.LEFT, padx=5)
        
        # Save settings button
        save_button = ttk.Button(dir_frame, text="Save Default Directories", 
                              command=self.save_settings)
        save_button.pack(anchor=tk.E, padx=10, pady=10)
        
        # App info section
        info_frame = ttk.LabelFrame(frame, text="About Photo Organizer")
        info_frame.pack(fill=tk.X, pady=20, padx=5)
        
        app_info = ttk.Label(info_frame, 
                          text="Photo Organizer v1.0\n\n"
                              "A tool to organize, clean, and convert your photo collection.\n"
                              "- Organize photos by date into Year/Month folders\n"
                              "- Remove duplicate, blurry, or small photos\n"
                              "- Convert RAW photos to high-quality JPG format")
        app_info.pack(pady=10, padx=10)
        
        # Try to load the settings if they exist
        self.load_settings()
        
    def save_settings(self):
        """Save default directories to a settings file"""
        try:
            settings_dir = Path.home() / ".photo_organizer"
            settings_dir.mkdir(exist_ok=True)
            settings_file = settings_dir / "settings.txt"
            
            with open(settings_file, "w") as f:
                f.write(f"default_source={self.default_source_var.get()}\n")
                f.write(f"default_dest={self.default_dest_var.get()}\n")
            
            messagebox.showinfo("Settings Saved", "Default directories have been saved.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
    
    def load_settings(self):
        """Load settings from settings file"""
        try:
            settings_file = Path.home() / ".photo_organizer" / "settings.txt"
            if settings_file.exists():
                with open(settings_file, "r") as f:
                    for line in f:
                        if "=" in line:
                            key, value = line.strip().split("=", 1)
                            if key == "default_source":
                                self.default_source_var.set(value)
                                # Also set current source if not already set
                                if not self.source_var.get():
                                    self.source_var.set(value)
                                if not self.dup_dir_var.get():
                                    self.dup_dir_var.set(value)
                                if not self.blur_dir_var.get():
                                    self.blur_dir_var.set(value)
                                if not self.small_dir_var.get():
                                    self.small_dir_var.set(value)
                                if not self.dng_dir_var.get():
                                    self.dng_dir_var.set(value)
                                if not self.raw_source_var.get():
                                    self.raw_source_var.set(value)
                            elif key == "default_dest":
                                self.default_dest_var.set(value)
                                # Also set current dest if not already set
                                if not self.dest_var.get():
                                    self.dest_var.set(value)
                                if not self.raw_dest_var.get():
                                    self.raw_dest_var.set(value)
        except Exception as e:
            # Silently fail on settings load, not critical
            print(f"Failed to load settings: {e}")
    
    def update_status(self, message):
        """Update status bar with message"""
        self.status_label.config(text=message)
        self.root.update_idletasks()
    
    def log_message(self, log_widget, message):
        """Add message to log widget"""
        log_widget.config(state=tk.NORMAL)
        log_widget.insert(tk.END, message + "\n")
        log_widget.see(tk.END)
        log_widget.config(state=tk.DISABLED)
        self.root.update_idletasks()
    
    def process_messages(self):
        try:
            while not self.message_queue.empty():
                message = self.message_queue.get_nowait()
                if message["type"] == "status":
                    self.update_status(message["text"])
                elif message["type"] == "log":
                    if "widget" in message and "text" in message:
                        self.log_message(message["widget"], message["text"])
                    elif "message" in message:
                        if hasattr(self, 'cloud_backup_ui'):
                            self.cloud_backup_ui.handle_message(message)
                elif message["type"] == "progress":
                    self.progress_bar["value"] = message["value"]
                elif message["type"] == "complete":
                    self.operation_complete()
                
                elif message["type"] in ["auth_success", "auth_failure", "update_backups", 
                                    "progress_update", "operation_complete"]:
                    if hasattr(self, 'cloud_backup_ui'):
                        self.cloud_backup_ui.handle_message(message)
                        
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_messages)

    def operation_complete(self):
        # Re-enable buttons
        self.organize_button.config(state=tk.NORMAL)
        self.duplicate_button.config(state=tk.NORMAL)
        self.blur_button.config(state=tk.NORMAL)
        self.small_button.config(state=tk.NORMAL)
        self.dng_button.config(state=tk.NORMAL)
        self.convert_button.config(state=tk.NORMAL)
        
        # Reset
        self.progress_bar["value"] = 0
        self.operation_running = False
    
    def run_organizer(self):
        """Run photo organizer in background thread"""
        if self.operation_running:
            messagebox.showinfo("Operation in Progress", "Please wait for the current operation to complete.")
            return
        
        source_dir = self.source_var.get()
        dest_dir = self.dest_var.get()
        move_files = self.move_var.get()
        dry_run = self.dry_run_var.get()
        
        if not source_dir or not dest_dir:
            messagebox.showerror("Error", "Please specify both source and destination directories.")
            return
        
        if not Path(source_dir).exists():
            messagebox.showerror("Error", "Source directory does not exist.")
            return
        
        self.organize_log.config(state=tk.NORMAL)
        self.organize_log.delete(1.0, tk.END)
        self.organize_log.config(state=tk.DISABLED)
        
        # Disable buttons during operation
        self.organize_button.config(state=tk.DISABLED)
        self.operation_running = True
        
        operation_thread = threading.Thread(
            target=self._organizer_thread,
            args=(source_dir, dest_dir, move_files, dry_run)
        )
        operation_thread.daemon = True
        operation_thread.start()
    
    def _organizer_thread(self, source_dir, dest_dir, move_files, dry_run):
        """Background thread for photo organization"""
        try:
            # Update status
            self.message_queue.put({
                "type": "status",
                "text": "Organizing photos..."
            })
            
            # Create redirect class to capture print output
            class PrintRedirector:
                def __init__(self, queue, widget):
                    self.queue = queue
                    self.widget = widget
                
                def write(self, text):
                    if text.strip():  # Only process non-empty text
                        self.queue.put({
                            "type": "log",
                            "widget": self.widget,
                            "text": text.rstrip()
                        })
                
                def flush(self):
                    pass
            
            # Redirect stdout
            original_stdout = sys.stdout
            sys.stdout = PrintRedirector(self.message_queue, self.organize_log)
            
            try:
                # Create and run organizer
                source_path = Path(source_dir)
                dest_path = Path(dest_dir)
                organizer = PhotoOrganizer(source_path, dest_path, move_files, dry_run)
                organizer.organize()
            finally:
                # Restore stdout
                sys.stdout = original_stdout
            
            self.message_queue.put({
                "type": "status",
                "text": "Organization complete!"
            })
            
        except Exception as e:
            self.message_queue.put({
                "type": "log",
                "widget": self.organize_log,
                "text": f"Error: {str(e)}"
            })
            
            self.message_queue.put({
                "type": "status",
                "text": "Error during organization."
            })
        
        finally:
            self.message_queue.put({
                "type": "complete",
                "value": None
            })

def main():
    # Create root window
    root = tk.Tk()
    
    # Create app
    app = PhotoOrganizerApp(root)
    
    # Start main loop
    root.mainloop()

if __name__ == "__main__":
    main()
    
