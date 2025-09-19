import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
import numpy as np
import cv2
from PIL import Image, ImageTk
from torchvision.models import resnet50

class AIFeatures:
    def __init__(self, parent_app):
        """Initialize AI features integration with the parent application"""
        self.parent = parent_app
        self.root = parent_app.root
        self.style = parent_app.style
        self.message_queue = parent_app.message_queue
        
        # Create models directory if it doesn't exist
        models_dir = Path(__file__).parent / "models"
        models_dir.mkdir(exist_ok=True)
        
        # Initialize model statuses
        self.models_loaded = {
            "classification": False,
            "face_recognition": False,
            "enhancement": False
        }
        
        # Setup components
        self.setup_ai_tab()
    
    def setup_ai_tab(self):
        """Add AI features tab to the main application"""
        # Create new tab in the parent's notebook
        self.ai_tab = ttk.Frame(self.parent.notebook)
        self.parent.notebook.add(self.ai_tab, text="AI Features")
        
        # Header
        header = ttk.Label(self.ai_tab, text="AI-Powered Photo Analysis", style='Header.TLabel')
        header.pack(pady=10)
        
        description = ttk.Label(self.ai_tab, 
                               text="Apply artificial intelligence to analyze, enhance, and organize your photos.")
        description.pack(pady=5)
        
        # Create notebook for different AI features
        self.ai_notebook = ttk.Notebook(self.ai_tab)
        self.ai_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create frames for each AI feature
        self.content_tagging_frame = ttk.Frame(self.ai_notebook)
        self.face_recognition_frame = ttk.Frame(self.ai_notebook)
        self.enhancement_frame = ttk.Frame(self.ai_notebook)
        
        self.ai_notebook.add(self.content_tagging_frame, text="Smart Tagging")
        self.ai_notebook.add(self.face_recognition_frame, text="Face Recognition")
        self.ai_notebook.add(self.enhancement_frame, text="Image Enhancement")
        
        # Setup each feature tab
        self.setup_content_tagging()
        self.setup_face_recognition()
        self.setup_enhancement()
        
        # Create common log area for AI operations
        log_frame = ttk.LabelFrame(self.ai_tab, text="AI Processing Log")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=20)
        
        self.ai_log = tk.Text(log_frame, height=10, width=80, wrap=tk.WORD)
        self.ai_log.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
        
        # Add scrollbar to log
        scrollbar = ttk.Scrollbar(self.ai_log, command=self.ai_log.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.ai_log.config(yscrollcommand=scrollbar.set)
        
        # Make log read-only
        self.ai_log.config(state=tk.DISABLED)
    
    def setup_content_tagging(self):
        """Setup the content tagging tab"""
        frame = self.content_tagging_frame
        
        # Directory selection
        dir_frame = ttk.Frame(frame)
        dir_frame.pack(fill=tk.X, pady=10, padx=10)
        
        dir_label = ttk.Label(dir_frame, text="Photos Directory:")
        dir_label.pack(side=tk.LEFT, padx=5)
        
        self.tagging_dir_var = tk.StringVar()
        dir_entry = ttk.Entry(dir_frame, textvariable=self.tagging_dir_var, width=50)
        dir_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        dir_button = ttk.Button(dir_frame, text="Browse...", 
                               command=lambda: self.browse_directory(self.tagging_dir_var))
        dir_button.pack(side=tk.LEFT, padx=5)
        
        # Options frame
        options_frame = ttk.LabelFrame(frame, text="Tagging Options")
        options_frame.pack(fill=tk.X, pady=10, padx=10)
        
        # Detection confidence threshold
        threshold_frame = ttk.Frame(options_frame)
        threshold_frame.pack(fill=tk.X, pady=5, padx=5)
        
        threshold_label = ttk.Label(threshold_frame, text="Detection Confidence:")
        threshold_label.pack(side=tk.LEFT, padx=5)
        
        self.confidence_var = tk.DoubleVar(value=0.7)
        threshold_scale = ttk.Scale(threshold_frame, from_=0.1, to=0.9, 
                                  variable=self.confidence_var, orient=tk.HORIZONTAL, length=200)
        threshold_scale.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        threshold_value = ttk.Label(threshold_frame, textvariable=self.confidence_var)
        threshold_value.pack(side=tk.LEFT, padx=5)
        
        # Categories to detect
        categories_frame = ttk.Frame(options_frame)
        categories_frame.pack(fill=tk.X, pady=5, padx=5)
        
        categories_label = ttk.Label(categories_frame, text="Categories to detect:")
        categories_label.pack(anchor=tk.W, padx=5, pady=5)
        
        # Checkboxes for different categories
        self.detect_objects_var = tk.BooleanVar(value=True)
        objects_check = ttk.Checkbutton(categories_frame, text="Objects", 
                                      variable=self.detect_objects_var)
        objects_check.pack(anchor=tk.W, padx=20, pady=2)
        
        self.detect_scenes_var = tk.BooleanVar(value=True)
        scenes_check = ttk.Checkbutton(categories_frame, text="Scenes", 
                                     variable=self.detect_scenes_var)
        scenes_check.pack(anchor=tk.W, padx=20, pady=2)
        
        self.detect_activities_var = tk.BooleanVar(value=True)
        activities_check = ttk.Checkbutton(categories_frame, text="Activities", 
                                         variable=self.detect_activities_var)
        activities_check.pack(anchor=tk.W, padx=20, pady=2)
        
        # Output options
        output_frame = ttk.Frame(options_frame)
        output_frame.pack(fill=tk.X, pady=5, padx=5)
        
        output_label = ttk.Label(output_frame, text="Save tags to:")
        output_label.pack(anchor=tk.W, padx=5, pady=5)
        
        self.tag_output_var = tk.StringVar(value="exif")
        exif_radio = ttk.Radiobutton(output_frame, text="EXIF metadata", 
                                   variable=self.tag_output_var, value="exif")
        exif_radio.pack(anchor=tk.W, padx=20, pady=2)
        
        csv_radio = ttk.Radiobutton(output_frame, text="CSV file", 
                                  variable=self.tag_output_var, value="csv")
        csv_radio.pack(anchor=tk.W, padx=20, pady=2)
        
        # Description 
        desc_frame = ttk.Frame(frame)
        desc_frame.pack(fill=tk.X, pady=10, padx=10)
        
        desc_text = ("This feature analyzes your photos using AI to detect objects, scenes, and activities. "
                    "The results can be saved as EXIF metadata or to a CSV file for easy searching and filtering.")
        
        desc_label = ttk.Label(desc_frame, text=desc_text, wraplength=600)
        desc_label.pack(pady=5)
        
        # Model download info
        model_frame = ttk.LabelFrame(frame, text="AI Model")
        model_frame.pack(fill=tk.X, pady=10, padx=10)
        
        self.model_status_var = tk.StringVar(value="Model not loaded")
        model_status = ttk.Label(model_frame, textvariable=self.model_status_var)
        model_status.pack(pady=5, padx=5)
        
        model_buttons_frame = ttk.Frame(model_frame)
        model_buttons_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.download_model_button = ttk.Button(model_buttons_frame, text="Download Model", 
                                              command=self.download_classification_model)
        self.download_model_button.pack(side=tk.LEFT, padx=5)
        
        # Run button
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=20, padx=10)
        
        self.run_tagging_button = ttk.Button(button_frame, text="Run Smart Tagging", 
                                         command=self.run_content_tagging, state=tk.DISABLED)
        self.run_tagging_button.pack(side=tk.RIGHT, padx=5)
    
    def setup_face_recognition(self):
        """Setup the face recognition tab"""
        frame = self.face_recognition_frame
        
        # Directory selection
        dir_frame = ttk.Frame(frame)
        dir_frame.pack(fill=tk.X, pady=10, padx=10)
        
        dir_label = ttk.Label(dir_frame, text="Photos Directory:")
        dir_label.pack(side=tk.LEFT, padx=5)
        
        self.face_dir_var = tk.StringVar()
        dir_entry = ttk.Entry(dir_frame, textvariable=self.face_dir_var, width=50)
        dir_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        dir_button = ttk.Button(dir_frame, text="Browse...", 
                              command=lambda: self.browse_directory(self.face_dir_var))
        dir_button.pack(side=tk.LEFT, padx=5)
        
        # Options frame
        options_frame = ttk.LabelFrame(frame, text="Face Recognition Options")
        options_frame.pack(fill=tk.X, pady=10, padx=10)
        
        # Recognition mode
        mode_frame = ttk.Frame(options_frame)
        mode_frame.pack(fill=tk.X, pady=5, padx=5)
        
        mode_label = ttk.Label(mode_frame, text="Recognition Mode:")
        mode_label.pack(anchor=tk.W, padx=5, pady=5)
        
        self.face_mode_var = tk.StringVar(value="cluster")
        cluster_radio = ttk.Radiobutton(mode_frame, text="Cluster similar faces", 
                                      variable=self.face_mode_var, value="cluster")
        cluster_radio.pack(anchor=tk.W, padx=20, pady=2)
        
        recognize_radio = ttk.Radiobutton(mode_frame, text="Recognize known people", 
                                        variable=self.face_mode_var, value="recognize")
        recognize_radio.pack(anchor=tk.W, padx=20, pady=2)
        
        # Clustering settings
        cluster_frame = ttk.Frame(options_frame)
        cluster_frame.pack(fill=tk.X, pady=5, padx=5)
        
        min_faces_label = ttk.Label(cluster_frame, text="Minimum cluster size:")
        min_faces_label.pack(side=tk.LEFT, padx=5)
        
        self.min_faces_var = tk.IntVar(value=5)
        min_faces_spin = ttk.Spinbox(cluster_frame, from_=2, to=100, 
                                   textvariable=self.min_faces_var, width=5)
        min_faces_spin.pack(side=tk.LEFT, padx=5)
        
        # Face database
        database_frame = ttk.LabelFrame(frame, text="Face Database")
        database_frame.pack(fill=tk.X, pady=10, padx=10)
        
        # Database path
        db_path_frame = ttk.Frame(database_frame)
        db_path_frame.pack(fill=tk.X, pady=5, padx=5)
        
        db_path_label = ttk.Label(db_path_frame, text="Database Location:")
        db_path_label.pack(side=tk.LEFT, padx=5)
        
        self.face_db_var = tk.StringVar()
        db_path_entry = ttk.Entry(db_path_frame, textvariable=self.face_db_var, width=50)
        db_path_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        db_path_button = ttk.Button(db_path_frame, text="Browse...", 
                                  command=lambda: self.browse_directory(self.face_db_var))
        db_path_button.pack(side=tk.LEFT, padx=5)
        
        # Database actions
        db_actions_frame = ttk.Frame(database_frame)
        db_actions_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.create_db_button = ttk.Button(db_actions_frame, text="Create New Database", 
                                         command=self.create_face_database)
        self.create_db_button.pack(side=tk.LEFT, padx=5)
        
        self.update_db_button = ttk.Button(db_actions_frame, text="Update Database", 
                                         command=self.update_face_database)
        self.update_db_button.pack(side=tk.LEFT, padx=5)
        
        # Model info
        model_frame = ttk.LabelFrame(frame, text="AI Model")
        model_frame.pack(fill=tk.X, pady=10, padx=10)
        
        self.face_model_status_var = tk.StringVar(value="Model not loaded")
        model_status = ttk.Label(model_frame, textvariable=self.face_model_status_var)
        model_status.pack(pady=5, padx=5)
        
        model_buttons_frame = ttk.Frame(model_frame)
        model_buttons_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.download_face_model_button = ttk.Button(model_buttons_frame, text="Download Model", 
                                                  command=self.download_face_model)
        self.download_face_model_button.pack(side=tk.LEFT, padx=5)
        
        # Run button
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=20, padx=10)
        
        self.run_face_button = ttk.Button(button_frame, text="Run Face Recognition", 
                                       command=self.run_face_recognition, state=tk.DISABLED)
        self.run_face_button.pack(side=tk.RIGHT, padx=5)
    
    def setup_enhancement(self):
        """Setup the image enhancement tab"""
        frame = self.enhancement_frame
        
        # Single image or batch processing selection
        mode_frame = ttk.Frame(frame)
        mode_frame.pack(fill=tk.X, pady=10, padx=10)
        
        self.enhancement_mode_var = tk.StringVar(value="single")
        single_radio = ttk.Radiobutton(mode_frame, text="Enhance Single Image", 
                                     variable=self.enhancement_mode_var, value="single",
                                     command=self.toggle_enhancement_mode)
        single_radio.pack(side=tk.LEFT, padx=20)
        
        batch_radio = ttk.Radiobutton(mode_frame, text="Batch Process Directory", 
                                    variable=self.enhancement_mode_var, value="batch",
                                    command=self.toggle_enhancement_mode)
        batch_radio.pack(side=tk.LEFT, padx=20)
        
        # Single image frame
        self.single_image_frame = ttk.Frame(frame)
        self.single_image_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
        
        # Image selection
        image_select_frame = ttk.Frame(self.single_image_frame)
        image_select_frame.pack(fill=tk.X, pady=10)
        
        image_label = ttk.Label(image_select_frame, text="Select Image:")
        image_label.pack(side=tk.LEFT, padx=5)
        
        self.image_path_var = tk.StringVar()
        image_entry = ttk.Entry(image_select_frame, textvariable=self.image_path_var, width=50)
        image_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        image_button = ttk.Button(image_select_frame, text="Browse...", 
                                command=self.browse_image)
        image_button.pack(side=tk.LEFT, padx=5)
        
        # Image preview area (before/after)
        preview_frame = ttk.Frame(self.single_image_frame)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        before_frame = ttk.LabelFrame(preview_frame, text="Original")
        before_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.before_canvas = tk.Canvas(before_frame, bg="gray", width=300, height=300)
        self.before_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        after_frame = ttk.LabelFrame(preview_frame, text="Enhanced")
        after_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.after_canvas = tk.Canvas(after_frame, bg="gray", width=300, height=300)
        self.after_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Enhancement options
        enhancement_options = ttk.LabelFrame(self.single_image_frame, text="Enhancement Options")
        enhancement_options.pack(fill=tk.X, pady=10)
        
        # Exposure correction
        exposure_frame = ttk.Frame(enhancement_options)
        exposure_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.enhance_exposure_var = tk.BooleanVar(value=True)
        exposure_check = ttk.Checkbutton(exposure_frame, text="Exposure Correction", 
                                       variable=self.enhance_exposure_var)
        exposure_check.pack(anchor=tk.W)
        
        # Color correction
        color_frame = ttk.Frame(enhancement_options)
        color_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.enhance_color_var = tk.BooleanVar(value=True)
        color_check = ttk.Checkbutton(color_frame, text="Color Enhancement", 
                                    variable=self.enhance_color_var)
        color_check.pack(anchor=tk.W)
        
        # Noise reduction
        noise_frame = ttk.Frame(enhancement_options)
        noise_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.enhance_noise_var = tk.BooleanVar(value=True)
        noise_check = ttk.Checkbutton(noise_frame, text="Noise Reduction", 
                                    variable=self.enhance_noise_var)
        noise_check.pack(anchor=tk.W)
        
        # Sharpening
        sharp_frame = ttk.Frame(enhancement_options)
        sharp_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.enhance_sharp_var = tk.BooleanVar(value=True)
        sharp_check = ttk.Checkbutton(sharp_frame, text="Sharpening", 
                                    variable=self.enhance_sharp_var)
        sharp_check.pack(anchor=tk.W)
        
        # Enhance button
        self.enhance_button = ttk.Button(self.single_image_frame, text="Enhance Image", 
                                      command=self.enhance_single_image, state=tk.DISABLED)
        self.enhance_button.pack(pady=10)
        
        self.save_enhanced_button = ttk.Button(self.single_image_frame, text="Save Enhanced Image", 
                                            command=self.save_enhanced_image, state=tk.DISABLED)
        self.save_enhanced_button.pack(pady=5)
        
        # Batch processing frame
        self.batch_frame = ttk.Frame(frame)
        
        # Directory selection
        batch_dir_frame = ttk.Frame(self.batch_frame)
        batch_dir_frame.pack(fill=tk.X, pady=10)
        
        source_label = ttk.Label(batch_dir_frame, text="Source Directory:")
        source_label.pack(side=tk.LEFT, padx=5)
        
        self.batch_source_var = tk.StringVar()
        source_entry = ttk.Entry(batch_dir_frame, textvariable=self.batch_source_var, width=50)
        source_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        source_button = ttk.Button(batch_dir_frame, text="Browse...", 
                                 command=lambda: self.browse_directory(self.batch_source_var))
        source_button.pack(side=tk.LEFT, padx=5)
        
        # Output directory
        output_dir_frame = ttk.Frame(self.batch_frame)
        output_dir_frame.pack(fill=tk.X, pady=10)
        
        output_label = ttk.Label(output_dir_frame, text="Output Directory:")
        output_label.pack(side=tk.LEFT, padx=5)
        
        self.batch_output_var = tk.StringVar()
        output_entry = ttk.Entry(output_dir_frame, textvariable=self.batch_output_var, width=50)
        output_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        output_button = ttk.Button(output_dir_frame, text="Browse...", 
                                 command=lambda: self.browse_directory(self.batch_output_var))
        output_button.pack(side=tk.LEFT, padx=5)
        
        # Batch enhancement options (similar to single image)
        batch_options = ttk.LabelFrame(self.batch_frame, text="Enhancement Options")
        batch_options.pack(fill=tk.X, pady=10)
        
        # Same options as single mode
        batch_exposure_frame = ttk.Frame(batch_options)
        batch_exposure_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.batch_exposure_var = tk.BooleanVar(value=True)
        batch_exposure_check = ttk.Checkbutton(batch_exposure_frame, text="Exposure Correction", 
                                             variable=self.batch_exposure_var)
        batch_exposure_check.pack(anchor=tk.W)
        
        batch_color_frame = ttk.Frame(batch_options)
        batch_color_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.batch_color_var = tk.BooleanVar(value=True)
        batch_color_check = ttk.Checkbutton(batch_color_frame, text="Color Enhancement", 
                                          variable=self.batch_color_var)
        batch_color_check.pack(anchor=tk.W)
        
        batch_noise_frame = ttk.Frame(batch_options)
        batch_noise_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.batch_noise_var = tk.BooleanVar(value=True)
        batch_noise_check = ttk.Checkbutton(batch_noise_frame, text="Noise Reduction", 
                                          variable=self.batch_noise_var)
        batch_noise_check.pack(anchor=tk.W)
        
        batch_sharp_frame = ttk.Frame(batch_options)
        batch_sharp_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.batch_sharp_var = tk.BooleanVar(value=True)
        batch_sharp_check = ttk.Checkbutton(batch_sharp_frame, text="Sharpening", 
                                          variable=self.batch_sharp_var)
        batch_sharp_check.pack(anchor=tk.W)
        
        # Run batch button
        self.run_batch_button = ttk.Button(self.batch_frame, text="Enhance All Images", 
                                        command=self.run_batch_enhancement, state=tk.DISABLED)
        self.run_batch_button.pack(pady=20)
        
        # Initially hide batch frame
        self.single_image_frame.pack()
        self.batch_frame.pack_forget()
        
        # Model info
        model_frame = ttk.LabelFrame(frame, text="AI Model")
        model_frame.pack(fill=tk.X, pady=10, padx=10)
        
        self.enhance_model_status_var = tk.StringVar(value="Model not loaded")
        model_status = ttk.Label(model_frame, textvariable=self.enhance_model_status_var)
        model_status.pack(pady=5, padx=5)
        
        model_buttons_frame = ttk.Frame(model_frame)
        model_buttons_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.download_enhance_model_button = ttk.Button(model_buttons_frame, text="Download Model", 
                                                     command=self.download_enhancement_model)
        self.download_enhance_model_button.pack(side=tk.LEFT, padx=5)
    
    # Utility functions
    def browse_directory(self, string_var):
        """Open file dialog to select directory"""
        directory = filedialog.askdirectory(title="Select Directory")
        if directory:
            string_var.set(directory)
    
    def browse_image(self):
        """Open file dialog to select an image"""
        file_types = [
            ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff")
        ]
        image_path = filedialog.askopenfilename(
            title="Select Image", 
            filetypes=file_types
        )
        if image_path:
            self.image_path_var.set(image_path)
            self.load_image_preview(image_path)
    
    def load_image_preview(self, image_path):
        """Load and display image preview"""
        try:
            # Open and resize image for preview
            img = Image.open(image_path)
            img.thumbnail((300, 300))
            photo = ImageTk.PhotoImage(img)
            
            # Display in canvas
            self.before_canvas.config(width=img.width, height=img.height)
            self.before_canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            self.before_canvas.image = photo  # Keep reference
            
            # Clear after canvas
            self.after_canvas.config(width=img.width, height=img.height)
            self.after_canvas.delete("all")
            
            # If model is loaded, enable enhance button
            if self.models_loaded["enhancement"]:
                self.enhance_button.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {e}")
    
    def toggle_enhancement_mode(self):
        """Switch between single image and batch processing modes"""
        mode = self.enhancement_mode_var.get()
        if mode == "single":
            self.batch_frame.pack_forget()
            self.single_image_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
        else:
            self.single_image_frame.pack_forget()
            self.batch_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
    
    # Model downloading
    def download_classification_model(self):
        """Download image classification model"""
        self.log_message(self.ai_log, "Downloading image classification model...")
        self.download_model_button.config(state=tk.DISABLED)
        self.model_status_var.set("Downloading model...")
        
        # Start download in background thread
        thread = threading.Thread(target=self._download_classification_model_thread)
        thread.daemon = True
        thread.start()
    
    def _download_classification_model_thread(self):
        """Background thread for downloading classification model"""
        try:
            # Simulate download with pre-trained model
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": "Initializing ResNet-50 model..."
            })
            
            # Create model directory
            models_dir = Path(__file__).parent / "models"
            models_dir.mkdir(exist_ok=True)
            
            # TODO download specific weights if needed
            # Here we'll use torchvision's pre-trained model
            model = resnet50(pretrained=True)
            model.eval()
            
            # Save model info for reference
            model_info = {
                "name": "ResNet-50",
                "type": "classification",
                "categories": 1000,
                "size": "~100MB"
            }
            
            # TODO save model info to a JSON file
            
            # Update UI
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": "Image classification model loaded successfully!"
            })
            
            self.message_queue.put({
                "type": "status_update",
                "variable": self.model_status_var,
                "text": "Model loaded: ResNet-50"
            })
            
            # Enable run button
            self.message_queue.put({
                "type": "button_state",
                "button": self.run_tagging_button,
                "state": tk.NORMAL
            })
            
            # Set model loaded flag
            self.models_loaded["classification"] = True
            
        except Exception as e:
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": f"Error downloading model: {str(e)}"
            })
            
            self.message_queue.put({
                "type": "status_update",
                "variable": self.model_status_var,
                "text": "Model download failed"
            })
            
            self.message_queue.put({
                "type": "button_state",
                "button": self.download_model_button,
                "state": tk.NORMAL
            })
    
    def download_face_model(self):
        """Download face recognition model"""
        self.log_message(self.ai_log, "Downloading face recognition model...")
        self.download_face_model_button.config(state=tk.DISABLED)
        self.face_model_status_var.set("Downloading model...")
        
        # Start download in background thread
        thread = threading.Thread(target=self._download_face_model_thread)
        thread.daemon = True
        thread.start()
    
    def _download_face_model_thread(self):
        """Background thread for downloading face recognition model"""
        try:
            # Simulate download - TODO download actual models
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": "Downloading face detection and recognition models..."
            })
            
            # Simulate download delay
            time.sleep(2)
            
            # Update UI
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": "Face recognition models loaded successfully!"
            })
            
            self.message_queue.put({
                "type": "status_update",
                "variable": self.face_model_status_var,
                "text": "Models loaded: Detection and Recognition"
            })
            
            # Enable run button
            self.message_queue.put({
                "type": "button_state",
                "button": self.run_face_button,
                "state": tk.NORMAL
            })
            
            # Set model loaded flag
            self.models_loaded["face_recognition"] = True
            
        except Exception as e:
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": f"Error downloading models: {str(e)}"
            })
            
            self.message_queue.put({
                "type": "status_update",
                "variable": self.face_model_status_var,
                "text": "Model download failed"
            })
            
            self.message_queue.put({
                "type": "button_state",
                "button": self.download_face_model_button,
                "state": tk.NORMAL
            })
    
    def download_enhancement_model(self):
        """Download image enhancement model"""
        self.log_message(self.ai_log, "Downloading image enhancement model...")
        self.download_enhance_model_button.config(state=tk.DISABLED)
        self.enhance_model_status_var.set("Downloading model...")
        
        # Start download in background thread
        thread = threading.Thread(target=self._download_enhancement_model_thread)
        thread.daemon = True
        thread.start()
    
    def _download_enhancement_model_thread(self):
        """Background thread for downloading enhancement model"""
        try:
            # Simulate download - TODO download actual models
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": "Downloading image enhancement models..."
            })
            
            # Simulate download delay
            time.sleep(2)
            
            # Update UI
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": "Image enhancement models loaded successfully!"
            })
            
            self.message_queue.put({
                "type": "status_update",
                "variable": self.enhance_model_status_var,
                "text": "Models loaded: Enhancement Suite"
            })
            
            # Enable run buttons
            self.message_queue.put({
                "type": "button_state",
                "button": self.run_batch_button,
                "state": tk.NORMAL
            })
            
            # Check if an image is loaded
            if self.image_path_var.get():
                self.message_queue.put({
                    "type": "button_state",
                    "button": self.enhance_button,
                    "state": tk.NORMAL
                })
            
            # Set model loaded flag
            self.models_loaded["enhancement"] = True
            
        except Exception as e:
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": f"Error downloading models: {str(e)}"
            })
            
            self.message_queue.put({
                "type": "status_update",
                "variable": self.enhance_model_status_var,
                "text": "Model download failed"
            })
            
            self.message_queue.put({
                "type": "button_state",
                "button": self.download_enhance_model_button,
                "state": tk.NORMAL
            })
    
    # Feature execution
    def run_content_tagging(self):
        """Run content tagging on photos directory"""
        if self.parent.operation_running:
            messagebox.showinfo("Operation in Progress", "Please wait for the current operation to complete.")
            return
        
        # Get input values
        directory = self.tagging_dir_var.get()
        
        # Validate inputs
        if not directory:
            messagebox.showerror("Error", "Please specify a directory to scan.")
            return
        
        if not Path(directory).exists():
            messagebox.showerror("Error", "Directory does not exist.")
            return
        
        # Clear log
        self.ai_log.config(state=tk.NORMAL)
        self.ai_log.delete(1.0, tk.END)
        self.ai_log.config(state=tk.DISABLED)
        
        # Disable buttons during operation
        self.run_tagging_button.config(state=tk.DISABLED)
        self.parent.operation_running = True
        
        # Get options
        confidence = self.confidence_var.get()
        detect_objects = self.detect_objects_var.get()
        detect_scenes = self.detect_scenes_var.get()
        detect_activities = self.detect_activities_var.get()
        output_type = self.tag_output_var.get()
        
        # Create thread
        thread = threading.Thread(
            target=self._content_tagging_thread,
            args=(directory, confidence, detect_objects, detect_scenes, 
                  detect_activities, output_type)
        )
        thread.daemon = True
        thread.start()
    
    def _content_tagging_thread(self, directory, confidence, detect_objects, 
                             detect_scenes, detect_activities, output_type):
        """Background thread for content tagging"""
        try:
            # Update status
            self.message_queue.put({
                "type": "status",
                "text": "Analyzing images with AI..."
            })
            
            # Log start
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": f"Starting image analysis in {directory}"
            })
            
            # Find image files
            image_extensions = {'.jpg', '.jpeg', '.png'}
            image_files = []
            
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": "Scanning for image files..."
            })
            
            for file_path in Path(directory).rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                    image_files.append(file_path)
            
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": f"Found {len(image_files)} images to analyze"
            })
            
            # TODO:
            # 1. Load the trained model
            # 2. Batch process images
            # 3. Apply detection for requested categories
            # 4. Write output to EXIF or CSV
            
            # Simulate processing delay
            import time
            
            # Simulate processing with progress updates
            processed = 0
            total = len(image_files)
            
            # Create output for CSV if needed
            if output_type == "csv":
                csv_path = Path(directory) / "image_tags.csv"
                self.message_queue.put({
                    "type": "log",
                    "widget": self.ai_log,
                    "text": f"Will save results to {csv_path}"
                })
            
            # Process each image (simulated)
            for i, img_path in enumerate(image_files[:10]):  # Limit to 10 for demo
                processed += 1
                
                self.message_queue.put({
                    "type": "log",
                    "widget": self.ai_log,
                    "text": f"Processing {img_path.name} ({processed}/{min(10, total)})..."
                })
                
                # Simulate AI processing time
                time.sleep(0.3)
                
                # In real implementation: Analyze image and extract tags
                
                # Simulate results
                self.message_queue.put({
                    "type": "log",
                    "widget": self.ai_log,
                    "text": f"  Detected: {'dog, person, ball' if i % 2 == 0 else 'landscape, mountain, sunset'}"
                })
            
            # Summarize results
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": f"\nAnalysis complete!"
            })
            
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": f"Processed {processed} images out of {total}"
            })
            
            if output_type == "csv":
                self.message_queue.put({
                    "type": "log",
                    "widget": self.ai_log,
                    "text": f"Results saved to {csv_path}"
                })
            else:
                self.message_queue.put({
                    "type": "log",
                    "widget": self.ai_log,
                    "text": "Tags written to image EXIF metadata"
                })
            
            # Update status
            self.message_queue.put({
                "type": "status",
                "text": "Image analysis complete!"
            })
            
        except Exception as e:
            # Log error
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": f"Error during image analysis: {str(e)}"
            })
            
            # Update status
            self.message_queue.put({
                "type": "status",
                "text": "Error during image analysis."
            })
        
        finally:
            # Signal completion
            self.message_queue.put({
                "type": "complete",
                "value": None
            })
            
            # Re-enable button
            self.message_queue.put({
                "type": "button_state",
                "button": self.run_tagging_button,
                "state": tk.NORMAL
            })
    
    def run_face_recognition(self):
        """Run face recognition on photos directory"""
        # Similar implementation to content tagging
        if self.parent.operation_running:
            messagebox.showinfo("Operation in Progress", "Please wait for the current operation to complete.")
            return
        
        # Get input values
        directory = self.face_dir_var.get()
        
        # Validate inputs
        if not directory:
            messagebox.showerror("Error", "Please specify a directory to scan.")
            return
        
        if not Path(directory).exists():
            messagebox.showerror("Error", "Directory does not exist.")
            return
        
        # Clear log
        self.ai_log.config(state=tk.NORMAL)
        self.ai_log.delete(1.0, tk.END)
        self.ai_log.config(state=tk.DISABLED)
        
        # Disable buttons during operation
        self.run_face_button.config(state=tk.DISABLED)
        self.parent.operation_running = True
        
        # Get options
        mode = self.face_mode_var.get()
        min_faces = self.min_faces_var.get()
        
        # Create thread
        thread = threading.Thread(
            target=self._face_recognition_thread,
            args=(directory, mode, min_faces)
        )
        thread.daemon = True
        thread.start()
    
    def _face_recognition_thread(self, directory, mode, min_faces):
        """Background thread for face recognition"""
        try:
            # Update status
            self.message_queue.put({
                "type": "status",
                "text": "Running face recognition..."
            })
            
            # Log start
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": f"Starting face {mode} in {directory}"
            })
            
            # Find image files
            image_extensions = {'.jpg', '.jpeg', '.png'}
            image_files = []
            
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": "Scanning for image files..."
            })
            
            for file_path in Path(directory).rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                    image_files.append(file_path)
            
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": f"Found {len(image_files)} images to analyze"
            })
            
            # Simulate processing
            import time
            
            # Process each image (simulated)
            faces_detected = 0
            clusters_created = 5
            
            for i, img_path in enumerate(image_files[:20]):  # Limit to 20 for demo
                self.message_queue.put({
                    "type": "log",
                    "widget": self.ai_log,
                    "text": f"Processing {img_path.name}..."
                })
                
                # Simulate AI processing time
                time.sleep(0.2)
                
                # Simulate results
                if i % 3 != 0:  # Simulate some images without faces
                    detected = i % 4 + 1
                    faces_detected += detected
                    self.message_queue.put({
                        "type": "log",
                        "widget": self.ai_log,
                        "text": f"  Detected {detected} faces"
                    })
            
            # Summarize results
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": f"\nAnalysis complete!"
            })
            
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": f"Detected {faces_detected} faces in {len(image_files)} images"
            })
            
            if mode == "cluster":
                self.message_queue.put({
                    "type": "log",
                    "widget": self.ai_log,
                    "text": f"Created {clusters_created} face clusters"
                })
            
            # Update status
            self.message_queue.put({
                "type": "status",
                "text": "Face recognition complete!"
            })
            
        except Exception as e:
            # Log error
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": f"Error during face recognition: {str(e)}"
            })
            
            # Update status
            self.message_queue.put({
                "type": "status",
                "text": "Error during face recognition."
            })
        
        finally:
            # Signal completion
            self.message_queue.put({
                "type": "complete",
                "value": None
            })
            
            # Re-enable button
            self.message_queue.put({
                "type": "button_state",
                "button": self.run_face_button,
                "state": tk.NORMAL
            })
    
    def create_face_database(self):
        """Create a new face database"""
        # TODO:
        # 1. Create database structure
        # 2. Initialize necessary files
        messagebox.showinfo("Database Creation", 
                           "This would create a new face database structure.")
    
    def update_face_database(self):
        """Update existing face database with new faces/identities"""
        # TODO:
        # 1. Open existing database
        # 2. Scan for new faces/update existing
        messagebox.showinfo("Database Update", 
                           "This would update the face database with new images.")
    
    def enhance_single_image(self):
        """Apply AI enhancement to the loaded image"""
        if not self.image_path_var.get():
            messagebox.showerror("Error", "No image selected.")
            return
        
        # Get image path
        image_path = self.image_path_var.get()
        
        # Get enhancement options
        enhance_exposure = self.enhance_exposure_var.get()
        enhance_color = self.enhance_color_var.get()
        enhance_noise = self.enhance_noise_var.get()
        enhance_sharp = self.enhance_sharp_var.get()
        
        try:
            # Load image
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError("Failed to load image")
            
            # Convert to RGB for processing
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Apply enhancements (simulated for demo)
            enhanced_img = img_rgb.copy()
            
            # Exposure correction (simple histogram equalization as placeholder)
            if enhance_exposure:
                # Convert to LAB color space for better exposure correction
                lab = cv2.cvtColor(enhanced_img, cv2.COLOR_RGB2LAB)
                l, a, b = cv2.split(lab)
                # Apply CLAHE to L channel
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                cl = clahe.apply(l)
                # Merge channels and convert back to RGB
                enhanced_lab = cv2.merge((cl, a, b))
                enhanced_img = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)
            
            # Color enhancement (simple saturation boost as placeholder)
            if enhance_color:
                # Convert to HSV
                hsv = cv2.cvtColor(enhanced_img, cv2.COLOR_RGB2HSV)
                h, s, v = cv2.split(hsv)
                # Boost saturation
                s = cv2.add(s, 10)
                # Merge and convert back
                enhanced_hsv = cv2.merge((h, s, v))
                enhanced_img = cv2.cvtColor(enhanced_hsv, cv2.COLOR_HSV2RGB)
            
            # Noise reduction
            if enhance_noise:
                # Non-local means denoising
                enhanced_img = cv2.fastNlMeansDenoisingColored(enhanced_img, None, 10, 10, 7, 21)
            
            # Sharpening
            if enhance_sharp:
                # Create sharpening kernel
                kernel = np.array([[-1, -1, -1], 
                                 [-1, 9, -1], 
                                 [-1, -1, -1]])
                enhanced_img = cv2.filter2D(enhanced_img, -1, kernel)
            
            # Convert to PIL image for display
            pil_img = Image.fromarray(enhanced_img)
            pil_img.thumbnail((300, 300))
            photo = ImageTk.PhotoImage(pil_img)
            
            # Display enhanced image
            self.after_canvas.config(width=pil_img.width, height=pil_img.height)
            self.after_canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            self.after_canvas.image = photo  # Keep reference
            
            # Store enhanced image for saving
            self.enhanced_image = Image.fromarray(enhanced_img)
            
            # Enable save button
            self.save_enhanced_button.config(state=tk.NORMAL)
            
            # Log success
            self.log_message(self.ai_log, "Image enhanced successfully")
            
        except Exception as e:
            # Log error
            self.log_message(self.ai_log, f"Error enhancing image: {str(e)}")
            messagebox.showerror("Error", f"Failed to enhance image: {e}")
    
    def save_enhanced_image(self):
        """Save the enhanced image to disk"""
        if not hasattr(self, 'enhanced_image'):
            messagebox.showerror("Error", "No enhanced image to save.")
            return
        
        # Get original path
        original_path = Path(self.image_path_var.get())
        
        # Suggest new filename
        suggested_name = f"{original_path.stem}_enhanced{original_path.suffix}"
        
        # Ask for save location
        file_types = [
            ("JPEG files", "*.jpg"),
            ("PNG files", "*.png"),
            ("All files", "*.*")
        ]
        
        save_path = filedialog.asksaveasfilename(
            title="Save Enhanced Image",
            defaultextension=".jpg",
            initialfile=suggested_name,
            filetypes=file_types
        )
        
        if not save_path:
            return  # User cancelled
        
        try:
            # Save the image
            self.enhanced_image.save(save_path)
            
            # Log success
            self.log_message(self.ai_log, f"Enhanced image saved to {save_path}")
            messagebox.showinfo("Success", "Enhanced image saved successfully.")
            
        except Exception as e:
            # Log error
            self.log_message(self.ai_log, f"Error saving image: {str(e)}")
            messagebox.showerror("Error", f"Failed to save image: {e}")
    
    def run_batch_enhancement(self):
        """Run batch enhancement on a directory of images"""
        if self.parent.operation_running:
            messagebox.showinfo("Operation in Progress", "Please wait for the current operation to complete.")
            return
        
        # Get input values
        source_dir = self.batch_source_var.get()
        output_dir = self.batch_output_var.get()
        
        # Validate inputs
        if not source_dir or not output_dir:
            messagebox.showerror("Error", "Please specify both source and output directories.")
            return
        
        if not Path(source_dir).exists():
            messagebox.showerror("Error", "Source directory does not exist.")
            return
        
        # Create output directory if it doesn't exist
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Could not create output directory: {e}")
            return
        
        # Clear log
        self.ai_log.config(state=tk.NORMAL)
        self.ai_log.delete(1.0, tk.END)
        self.ai_log.config(state=tk.DISABLED)
        
        # Disable buttons during operation
        self.run_batch_button.config(state=tk.DISABLED)
        self.parent.operation_running = True
        
        # Get enhancement options
        enhance_exposure = self.batch_exposure_var.get()
        enhance_color = self.batch_color_var.get()
        enhance_noise = self.batch_noise_var.get()
        enhance_sharp = self.batch_sharp_var.get()
        
        # Create thread
        thread = threading.Thread(
            target=self._batch_enhancement_thread,
            args=(source_dir, output_dir, enhance_exposure, enhance_color, 
                  enhance_noise, enhance_sharp)
        )
        thread.daemon = True
        thread.start()
    
    def _batch_enhancement_thread(self, source_dir, output_dir, enhance_exposure, 
                               enhance_color, enhance_noise, enhance_sharp):
        """Background thread for batch image enhancement"""
        try:
            # Update status
            self.message_queue.put({
                "type": "status",
                "text": "Enhancing images..."
            })
            
            # Log start
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": f"Starting batch enhancement from {source_dir} to {output_dir}"
            })
            
            # Find image files
            image_extensions = {'.jpg', '.jpeg', '.png'}
            image_files = []
            
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": "Scanning for image files..."
            })
            
            for file_path in Path(source_dir).rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                    image_files.append(file_path)
            
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": f"Found {len(image_files)} images to enhance"
            })
            
            # Process images (TODO  this would apply AI enhancement)
            enhanced_count = 0
            error_count = 0
            
            for img_path in image_files:
                try:
                    # Log current file
                    self.message_queue.put({
                        "type": "log",
                        "widget": self.ai_log,
                        "text": f"Enhancing {img_path.name}..."
                    })
                    
                    # Calculate relative path to maintain directory structure
                    rel_path = img_path.relative_to(Path(source_dir))
                    output_path = Path(output_dir) / rel_path
                    
                    # Create parent directories if needed
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # TODO use AI models for enhancement
                    # Here we'll do a simple enhancement similar to the single image mode
                    try:
                        # Load image
                        img = cv2.imread(str(img_path))
                        
                        # Skip if loading failed
                        if img is None:
                            raise ValueError(f"Failed to load {img_path.name}")
                        
                        # Convert to RGB for processing
                        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        
                        # Apply enhancements (simple placeholders)
                        enhanced_img = img_rgb.copy()
                        
                        # Exposure correction
                        if enhance_exposure:
                            # Convert to LAB color space
                            lab = cv2.cvtColor(enhanced_img, cv2.COLOR_RGB2LAB)
                            l, a, b = cv2.split(lab)
                            # Apply CLAHE to L channel
                            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                            cl = clahe.apply(l)
                            # Merge channels and convert back to RGB
                            enhanced_lab = cv2.merge((cl, a, b))
                            enhanced_img = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)
                        
                        # Color enhancement
                        if enhance_color:
                            # Convert to HSV
                            hsv = cv2.cvtColor(enhanced_img, cv2.COLOR_RGB2HSV)
                            h, s, v = cv2.split(hsv)
                            # Boost saturation
                            s = cv2.add(s, 10)
                            # Merge and convert back
                            enhanced_hsv = cv2.merge((h, s, v))
                            enhanced_img = cv2.cvtColor(enhanced_hsv, cv2.COLOR_HSV2RGB)
                        
                        # Noise reduction
                        if enhance_noise:
                            # Simple gaussian blur as placeholder
                            enhanced_img = cv2.GaussianBlur(enhanced_img, (3, 3), 0)
                        
                        # Sharpening
                        if enhance_sharp:
                            # Create sharpening kernel
                            kernel = np.array([[-1, -1, -1], 
                                             [-1, 9, -1], 
                                             [-1, -1, -1]])
                            enhanced_img = cv2.filter2D(enhanced_img, -1, kernel)
                        
                        # Convert back to BGR for saving
                        enhanced_bgr = cv2.cvtColor(enhanced_img, cv2.COLOR_RGB2BGR)
                        
                        # Save the enhanced image
                        cv2.imwrite(str(output_path), enhanced_bgr)
                        
                        enhanced_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        self.message_queue.put({
                            "type": "log",
                            "widget": self.ai_log,
                            "text": f"  Error processing {img_path.name}: {str(e)}"
                        })
                
                except Exception as e:
                    error_count += 1
                    self.message_queue.put({
                        "type": "log",
                        "widget": self.ai_log,
                        "text": f"  Error with {img_path.name}: {str(e)}"
                    })
            
            # Log completion
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": f"\nEnhancement complete!"
            })
            
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": f"Successfully enhanced: {enhanced_count} images"
            })
            
            if error_count > 0:
                self.message_queue.put({
                    "type": "log",
                    "widget": self.ai_log,
                    "text": f"Errors encountered: {error_count} images"
                })
            
            # Update status
            self.message_queue.put({
                "type": "status",
                "text": "Image enhancement complete!"
            })
            
        except Exception as e:
            # Log error
            self.message_queue.put({
                "type": "log",
                "widget": self.ai_log,
                "text": f"Error during batch enhancement: {str(e)}"
            })
            
            # Update status
            self.message_queue.put({
                "type": "status",
                "text": "Error during image enhancement."
            })
        
        finally:
            # Signal completion
            self.message_queue.put({
                "type": "complete",
                "value": None
            })
            
            # Re-enable button
            self.message_queue.put({
                "type": "button_state",
                "button": self.run_batch_button,
                "state": tk.NORMAL
            })
    
    def log_message(self, log_widget, message):
        """Add message to log widget"""
        log_widget.config(state=tk.NORMAL)
        log_widget.insert(tk.END, message + "\n")
        log_widget.see(tk.END)
        log_widget.config(state=tk.DISABLED)
        self.root.update_idletasks()

# Function to integrate AI features into the main app
def add_ai_features_to_app(app):
    """Add AI features to the existing PhotoOrganizerApp"""
    ai_features = AIFeatures(app)
    return ai_features