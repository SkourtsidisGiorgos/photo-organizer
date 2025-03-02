import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import time
from pathlib import Path
import humanize
import sys
import os

# Import cloud backup functionality
from cloud_backup import get_backup_service, CloudBackupService

class CloudBackupTab:
    """Cloud Backup tab UI component for Photo Organizer"""
    
    def __init__(self, parent, message_queue):
        """
        Initialize cloud backup tab
        
        Args:
            parent: Parent frame/tab
            message_queue: Queue for thread-safe messaging
        """
        self.parent = parent
        self.message_queue = message_queue
        self.is_authenticated = False
        self.service = None
        self.current_service_type = None
        self.operation_running = False
        
        self.setup_ui()
        self.check_credentials()
    
    def setup_ui(self):
        """Set up the UI components"""
        # Main frame
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header
        header = ttk.Label(main_frame, text="Cloud Backup", style='Header.TLabel')
        header.pack(pady=10)
        
        description = ttk.Label(main_frame, 
                              text="Backup your photos to cloud storage or restore from a previous backup.")
        description.pack(pady=5)
        
        # Service selection frame
        service_frame = ttk.LabelFrame(main_frame, text="Cloud Service")
        service_frame.pack(fill=tk.X, pady=10, padx=5)
        
        # Service type selection
        service_type_frame = ttk.Frame(service_frame)
        service_type_frame.pack(fill=tk.X, pady=5, padx=5)
        
        service_label = ttk.Label(service_type_frame, text="Select Service:")
        service_label.pack(side=tk.LEFT, padx=5)
        
        self.service_var = tk.StringVar(value="dropbox")
        
        dropbox_radio = ttk.Radiobutton(service_type_frame, text="Dropbox", 
                                      variable=self.service_var, value="dropbox",
                                      command=self.on_service_changed)
        dropbox_radio.pack(side=tk.LEFT, padx=10)
        
        gdrive_radio = ttk.Radiobutton(service_type_frame, text="Google Drive", 
                                     variable=self.service_var, value="gdrive",
                                     command=self.on_service_changed)
        gdrive_radio.pack(side=tk.LEFT, padx=10)
        
        s3_radio = ttk.Radiobutton(service_type_frame, text="AWS S3", 
                                 variable=self.service_var, value="s3",
                                 command=self.on_service_changed)
        s3_radio.pack(side=tk.LEFT, padx=10)
        
        # Authentication status and button
        auth_frame = ttk.Frame(service_frame)
        auth_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.auth_status_var = tk.StringVar(value="Not authenticated")
        auth_status = ttk.Label(auth_frame, textvariable=self.auth_status_var)
        auth_status.pack(side=tk.LEFT, padx=5)
        
        self.auth_button = ttk.Button(auth_frame, text="Authenticate", 
                                    command=self.authenticate)
        self.auth_button.pack(side=tk.RIGHT, padx=5)
        
        # Backup operation frame
        backup_frame = ttk.LabelFrame(main_frame, text="Backup Operations")
        backup_frame.pack(fill=tk.X, pady=10, padx=5)
        
        # Source directory selection
        src_frame = ttk.Frame(backup_frame)
        src_frame.pack(fill=tk.X, pady=5, padx=5)
        
        src_label = ttk.Label(src_frame, text="Source Directory:")
        src_label.pack(side=tk.LEFT, padx=5)
        
        self.src_var = tk.StringVar()
        src_entry = ttk.Entry(src_frame, textvariable=self.src_var, width=50)
        src_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        src_button = ttk.Button(src_frame, text="Browse...", 
                               command=self.browse_source)
        src_button.pack(side=tk.LEFT, padx=5)
        
        self.backup_button = ttk.Button(backup_frame, text="Backup to Cloud", 
                                      command=self.start_backup,
                                      state=tk.DISABLED)
        self.backup_button.pack(side=tk.RIGHT, padx=5, pady=10)
        
        # Restore operation frame
        restore_frame = ttk.LabelFrame(main_frame, text="Restore Operations")
        restore_frame.pack(fill=tk.X, pady=10, padx=5)
        
        # Backups listbox with scrollbar
        backups_frame = ttk.Frame(restore_frame)
        backups_frame.pack(fill=tk.X, pady=5, padx=5)
        
        backups_label = ttk.Label(backups_frame, text="Available Backups:")
        backups_label.pack(anchor=tk.W, padx=5, pady=5)
        
        list_frame = ttk.Frame(backups_frame)
        list_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Scrollbar for backups list
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Backups listbox
        self.backups_listbox = tk.Listbox(list_frame, height=6, width=50, 
                                        yscrollcommand=scrollbar.set)
        self.backups_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        scrollbar.config(command=self.backups_listbox.yview)
        
        # Buttons frame for backups
        backups_buttons_frame = ttk.Frame(backups_frame)
        backups_buttons_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.refresh_button = ttk.Button(backups_buttons_frame, text="Refresh Backups", 
                                       command=self.refresh_backups,
                                       state=tk.DISABLED)
        self.refresh_button.pack(side=tk.LEFT, padx=5)
        
        # Destination directory selection
        dest_frame = ttk.Frame(restore_frame)
        dest_frame.pack(fill=tk.X, pady=5, padx=5)
        
        dest_label = ttk.Label(dest_frame, text="Destination Directory:")
        dest_label.pack(side=tk.LEFT, padx=5)
        
        self.dest_var = tk.StringVar()
        dest_entry = ttk.Entry(dest_frame, textvariable=self.dest_var, width=50)
        dest_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        dest_button = ttk.Button(dest_frame, text="Browse...", 
                               command=self.browse_destination)
        dest_button.pack(side=tk.LEFT, padx=5)
        
        # Restore button
        self.restore_button = ttk.Button(restore_frame, text="Restore from Cloud", 
                                       command=self.start_restore,
                                       state=tk.DISABLED)
        self.restore_button.pack(side=tk.RIGHT, padx=5, pady=10)
        
        log_frame = ttk.LabelFrame(main_frame, text="Log")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=5)
        
        self.log = tk.Text(log_frame, height=10, width=80, wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
        
        # Add scrollbar to log
        log_scrollbar = ttk.Scrollbar(self.log, command=self.log.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log.config(yscrollcommand=log_scrollbar.set)
        
        # Make log read-only
        self.log.config(state=tk.DISABLED)
        
        # Progress frame
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.progress_var = tk.StringVar(value="")
        progress_label = ttk.Label(progress_frame, textvariable=self.progress_var)
        progress_label.pack(side=tk.LEFT, padx=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.progress_bar.pack(side=tk.RIGHT, padx=5)
        
    def check_credentials(self):
        service_type = self.service_var.get()
        
        try:
            # Create service instance without triggering authentication
            service = get_backup_service(service_type)
            
            # Update status based on authentication
            if service.is_authenticated:
                self.is_authenticated = True
                self.service = service
                self.current_service_type = service_type
                self.auth_status_var.set(f"Authenticated with {service_type}")
                self.auth_button.config(text="Re-authenticate")
                self.backup_button.config(state=tk.NORMAL)
                self.refresh_button.config(state=tk.NORMAL)
                self.restore_button.config(state=tk.NORMAL)
                
                # Populate backups list
                self.refresh_backups()
            else:
                self.is_authenticated = False
                self.auth_status_var.set(f"Not authenticated with {service_type}")
                self.auth_button.config(text="Authenticate")
                self.backup_button.config(state=tk.DISABLED)
                self.refresh_button.config(state=tk.DISABLED)
                self.restore_button.config(state=tk.DISABLED)
                self.backups_listbox.delete(0, tk.END)
        
        except Exception as e:
            self.log_message(f"Error checking credentials: {e}")
            self.is_authenticated = False
    
    def on_service_changed(self):
        """Handle service type change"""
        self.check_credentials()
    
    def log_message(self, message):
        """Add message to log"""
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)
    
    def browse_source(self):
        """Browse for source directory"""
        directory = filedialog.askdirectory(title="Select Source Directory")
        if directory:
            self.src_var.set(directory)
    
    def browse_destination(self):
        """Browse for destination directory"""
        directory = filedialog.askdirectory(title="Select Destination Directory")
        if directory:
            self.dest_var.set(directory)
    
    def refresh_backups(self):
        """Refresh the list of available backups"""
        if not self.is_authenticated or self.operation_running:
            return
        
        self.operation_running = True
        self.log_message("Fetching backup list...")
        self.backups_listbox.delete(0, tk.END)
        
        # Start in a separate thread
        thread = threading.Thread(target=self._refresh_backups_thread)
        thread.daemon = True
        thread.start()
    
    def _refresh_backups_thread(self):
        """Background thread for refreshing backups"""
        try:
            backups = self.service.list_backups()
            
            self.message_queue.put({
                "type": "update_backups",
                "backups": backups
            })
            
            self.message_queue.put({
                "type": "log",
                "message": f"Found {len(backups)} backups."
            })
            
        except Exception as e:
            self.message_queue.put({
                "type": "log",
                "message": f"Error refreshing backups: {e}"
            })
        
        finally:
            self.message_queue.put({
                "type": "operation_complete"
            })
    
    def update_backups_list(self, backups):
        self.backups_listbox.delete(0, tk.END)
        
        if not backups:
            self.backups_listbox.insert(tk.END, "No backups found")
            return
        
        self.backups = backups
        
        for backup in backups:
            name = backup.get('name', 'Unknown')
            created = backup.get('created', 'Unknown date')
            
            if isinstance(created, str) and 'T' in created:
                # Format ISO datetime
                try:
                    created_parts = created.split('T')
                    created = f"{created_parts[0]} {created_parts[1][:8]}"
                except:
                    pass
            
            if 'total_size' in backup and backup['total_size'] != 'Unknown':
                try:
                    size = humanize.naturalsize(backup['total_size'])
                except:
                    size = str(backup['total_size']) + " bytes"
            else:
                size = "Unknown size"
            
            self.backups_listbox.insert(tk.END, f"{name} - {created} ({size})")
    
    def authenticate(self):
        if self.operation_running:
            messagebox.showinfo("Operation in Progress", 
                              "Please wait for the current operation to complete.")
            return
        
        self.operation_running = True
        service_type = self.service_var.get()
        
        self.log_message(f"Authenticating with {service_type}...")
        
        thread = threading.Thread(target=self._authenticate_thread, args=(service_type,))
        thread.daemon = True
        thread.start()
    
    def _authenticate_thread(self, service_type):
        """Background thread for authentication"""
        try:
            # Log detailed information
            self.message_queue.put({
                "type": "log",
                "message": f"Starting authentication with {service_type}..."
            })
            
            # For Dropbox, we need an app key
            if service_type == 'dropbox':
                # Show dialog to get app key
                from tkinter import simpledialog
                app_key = simpledialog.askstring(
                    "Dropbox App Key Required", 
                    "Please enter your Dropbox App Key:\n\n"
                    "To get one:\n"
                    "1. Go to https://www.dropbox.com/developers/apps\n"
                    "2. Click 'Create app'\n"
                    "3. Choose 'Scoped access' API\n"
                    "4. Select 'Full Dropbox' access\n"
                    "5. Give your app a name\n"
                    "6. In Settings, find and copy the App Key",
                    parent=self.parent
                )
                
                if not app_key:
                    self.message_queue.put({
                        "type": "log",
                        "message": "Authentication cancelled - no app key provided."
                    })
                    self.message_queue.put({"type": "operation_complete"})
                    return
                
                # Create service instance with app key
                service = get_backup_service(service_type, app_key=app_key)
            
            # For Google Drive, we need credentials file
            elif service_type in ['gdrive', 'google', 'googledrive']:
                # Ask user to select credentials file
                from tkinter import filedialog
                credentials_file = filedialog.askopenfilename(
                    title="Select Google OAuth Credentials JSON file",
                    filetypes=[("JSON files", "*.json")]
                )
                
                if not credentials_file:
                    self.message_queue.put({
                        "type": "log",
                        "message": "Authentication cancelled - no credentials file selected."
                    })
                    self.message_queue.put({"type": "operation_complete"})
                    return
                
                # Create service instance with credentials file
                service = get_backup_service(service_type, credentials_file=credentials_file)
            
            # For S3, we'll use regular auth (handled in service)
            else:
                # Create service instance
                service = get_backup_service(service_type)
            
            # Show info about what's happening next
            if service_type == 'dropbox':
                self.message_queue.put({
                    "type": "log",
                    "message": "A browser window or URL will be provided for Dropbox authentication.\n"
                            "You'll need to authorize and get a code to paste back into the application."
                })
            elif service_type in ['gdrive', 'google', 'googledrive']:
                self.message_queue.put({
                    "type": "log",
                    "message": "A browser window will open for Google authentication.\n"
                            "Follow the prompts to authorize the application."
                })
            
            # Authenticate
            success = service.authenticate()
            
            if success:
                # Update service
                self.service = service
                self.current_service_type = service_type
                
                # Update UI with success
                self.message_queue.put({
                    "type": "auth_success",
                    "service_type": service_type
                })
                
                # Refresh backup list
                backups = service.list_backups()
                self.message_queue.put({
                    "type": "update_backups",
                    "backups": backups
                })
            else:
                # Update UI with failure
                self.message_queue.put({
                    "type": "auth_failure",
                    "service_type": service_type
                })
            
        except Exception as e:
            # Log detailed error
            import traceback
            error_details = traceback.format_exc()
            
            self.message_queue.put({
                "type": "log",
                "message": f"Error during authentication: {e}\n\nDetails:\n{error_details}"
            })
            
            # Update UI with failure
            self.message_queue.put({
                "type": "auth_failure",
                "service_type": service_type
            })
        
        finally:
            # Signal completion
            self.message_queue.put({
                "type": "operation_complete"
            })

    def auth_success(self, service_type):
        self.is_authenticated = True
        self.auth_status_var.set(f"Authenticated with {service_type}")
        self.auth_button.config(text="Re-authenticate")
        self.backup_button.config(state=tk.NORMAL)
        self.refresh_button.config(state=tk.NORMAL)
        self.restore_button.config(state=tk.NORMAL)
        self.log_message(f"Successfully authenticated with {service_type}")
    
    def auth_failure(self, service_type):
        self.is_authenticated = False
        self.auth_status_var.set(f"Authentication failed")
        self.log_message(f"Failed to authenticate with {service_type}")
    
    def start_backup(self):
        if not self.is_authenticated:
            messagebox.showinfo("Authentication Required", 
                              "Please authenticate with the cloud service first.")
            return
        
        if self.operation_running:
            messagebox.showinfo("Operation in Progress", 
                              "Please wait for the current operation to complete.")
            return
        
        source_dir = self.src_var.get()
        if not source_dir:
            messagebox.showerror("Error", "Please specify a source directory.")
            return
        
        source_path = Path(source_dir)
        if not source_path.exists():
            messagebox.showerror("Error", "Source directory does not exist.")
            return
        
        confirm = messagebox.askyesno(
            "Confirm Backup",
            f"Are you sure you want to backup {source_dir} to {self.current_service_type}?",
            icon='question'
        )
        
        if not confirm:
            return
        
        self.operation_running = True
        
        # Reset
        self.progress_bar["value"] = 0
        self.progress_var.set("0%")
        self.log_message(f"Starting backup of {source_dir} to {self.current_service_type}...")
        
        thread = threading.Thread(target=self._backup_thread, args=(source_path,))
        thread.daemon = True
        thread.start()
    
    def _backup_thread(self, source_path):
        try:
            def progress_callback(current, total):
                if total > 0:
                    percent = int(current / total * 100)
                    self.message_queue.put({
                        "type": "progress_update",
                        "percent": percent
                    })
            
            class LogRedirector:
                def __init__(self, queue):
                    self.queue = queue
                
                def write(self, text):
                    if text.strip():  # Only process non-empty text
                        self.queue.put({
                            "type": "log",
                            "message": text.rstrip()
                        })
                
                def flush(self):
                    pass
            
            original_stdout = sys.stdout
            sys.stdout = LogRedirector(self.message_queue)
            
            try:
                success = self.service.upload_directory(
                    source_path, 
                    progress_callback=progress_callback
                )
                
                if success:
                    self.message_queue.put({
                        "type": "log",
                        "message": "Backup completed successfully!"
                    })
                else:
                    self.message_queue.put({
                        "type": "log",
                        "message": "Backup completed with errors. Check the log for details."
                    })
                
                backups = self.service.list_backups()
                self.message_queue.put({
                    "type": "update_backups",
                    "backups": backups
                })
                
            finally:
                # Restore stdout
                sys.stdout = original_stdout
            
        except Exception as e:
            self.message_queue.put({
                "type": "log",
                "message": f"Error during backup: {e}"
            })
        
        finally:
            self.message_queue.put({
                "type": "operation_complete"
            })
            
            self.message_queue.put({
                "type": "progress_update",
                "percent": 100
            })
    
    def start_restore(self):
        """Start restore operation"""
        if not self.is_authenticated:
            messagebox.showinfo("Authentication Required", 
                              "Please authenticate with the cloud service first.")
            return
        
        if self.operation_running:
            messagebox.showinfo("Operation in Progress", 
                              "Please wait for the current operation to complete.")
            return
        
        # Get destination directory
        dest_dir = self.dest_var.get()
        if not dest_dir:
            messagebox.showerror("Error", "Please specify a destination directory.")
            return
        
        # Create destination if it doesn't exist
        dest_path = Path(dest_dir)
        dest_path.mkdir(parents=True, exist_ok=True)
        
        # Get selected backup
        selection = self.backups_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a backup to restore.")
            return
        
        backup_index = selection[0]
        if not hasattr(self, 'backups') or backup_index >= len(self.backups):
            messagebox.showerror("Error", "Invalid backup selection.")
            return
        
        selected_backup = self.backups[backup_index]
        backup_id = selected_backup['id']
        backup_name = selected_backup['name']
        
        # Confirm operation
        confirm = messagebox.askyesno(
            "Confirm Restore",
            f"Are you sure you want to restore backup '{backup_name}' to {dest_dir}?",
            icon='question'
        )
        
        if not confirm:
            return
        
        self.operation_running = True
        
        self.progress_bar["value"] = 0
        self.progress_var.set("0%")
        self.log_message(f"Starting restore of backup '{backup_name}' to {dest_dir}...")
        
        thread = threading.Thread(target=self._restore_thread, 
                                args=(backup_id, dest_path))
        thread.daemon = True
        thread.start()
    
    def _restore_thread(self, backup_id, dest_path):
        """Background thread for restore operation"""
        try:
            def progress_callback(current, total):
                if total > 0:
                    percent = int(current / total * 100)
                    self.message_queue.put({
                        "type": "progress_update",
                        "percent": percent
                    })
            
            # Redirect stdout to log
            class LogRedirector:
                def __init__(self, queue):
                    self.queue = queue
                
                def write(self, text):
                    if text.strip():  # Only process non-empty text
                        self.queue.put({
                            "type": "log",
                            "message": text.rstrip()
                        })
                
                def flush(self):
                    pass
            
            original_stdout = sys.stdout
            sys.stdout = LogRedirector(self.message_queue)
            
            try:
                # Perform restore
                success = self.service.download_backup(
                    backup_id, 
                    dest_path,
                    progress_callback=progress_callback
                )
                
                if success:
                    self.message_queue.put({
                        "type": "log",
                        "message": "Restore completed successfully!"
                    })
                else:
                    self.message_queue.put({
                        "type": "log",
                        "message": "Restore completed with errors. Check the log for details."
                    })
                
            finally:
                # Restore stdout
                sys.stdout = original_stdout
            
        except Exception as e:
            self.message_queue.put({
                "type": "log",
                "message": f"Error during restore: {e}"
            })
        
        finally:
            self.message_queue.put({
                "type": "operation_complete"
            })
            
            self.message_queue.put({
                "type": "progress_update",
                "percent": 100
            })
    
    def update_progress(self, percent):
        """Update progress bar and text"""
        self.progress_bar["value"] = percent
        self.progress_var.set(f"{percent}%")
    
    def operation_complete(self):
        """Handle operation completion"""
        self.operation_running = False
    
    def handle_message(self, message):
        """Process messages from the queue"""
        message_type = message.get("type")
        
        if message_type == "log":
            self.log_message(message.get("message", ""))
        
        elif message_type == "auth_success":
            self.auth_success(message.get("service_type"))
        
        elif message_type == "auth_failure":
            self.auth_failure(message.get("service_type"))
        
        elif message_type == "update_backups":
            self.update_backups_list(message.get("backups", []))
        
        elif message_type == "progress_update":
            self.update_progress(message.get("percent", 0))
        
        elif message_type == "operation_complete":
            self.operation_complete()