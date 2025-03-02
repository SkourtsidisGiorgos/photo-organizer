# Photo Organizer

A user-friendly application for organizing, cleaning, and converting your photo collection.

![Photo Organizer Screenshot](resources/screenshot.png)

## Features

- **Organize Photos**: Automatically sort your photos into Year/Month folders based on EXIF data or file creation date
- **Clean Photos**:
  - Remove duplicate photos
  - Delete blurry images
  - Clean up small thumbnail images
  - Remove redundant JPG files when paired with RAW/DNG
- **Convert Photos**: Transform RAW format photos to high-quality JPG
- **Cloud Backup**: Back up your photo collection to cloud storage services
  - Dropbox integration
  - Google Drive integration
  - Amazon S3 support
- **Smart Content Tagging**: Automatically identify objects, scenes, and activities in your photos
- **Face Recognition**: Group photos by the people appearing in them
- **Image Enhancement**: Use AI to improve lighting, color, and sharpness

## Installation

### Requirements

- Python 3.6 or higher
- Required packages: 
  - Core: pillow, rawpy, opencv-python, tqdm, imageio, humanize, psutil
  - Cloud: dropbox, google-auth-oauthlib, google-api-python-client, pydrive2, boto3, requests
- Optional: exiftool (for better metadata extraction)

### Easy Installation
0. (Recommended) `python -m venv venv && source venv/bin/activate`
1. Download the application files
2. Run the setup script: `python setup.py`

### Manual Installation

1. Install required Python packages:
   ```
   pip install pillow rawpy opencv-python tqdm imageio humanize psutil dropbox google-auth-oauthlib google-api-python-client pydrive2 boto3 requests
   ```
2. Download and extract the application files
3. Run the application:
   ```
   python photo_organizer_launcher.py
   ```

## Usage Guide

### Organizing Photos

1. Go to the "Organize Photos" tab
2. Select your source directory containing photos
3. Choose a destination directory for the organized photos
4. Select options:
   - "Move files" - moves instead of copying (saves disk space but modifies source)
   - "Dry run" - simulates organization without making changes
5. Click "Organize Photos" to start

The application will read EXIF data from your photos to determine the date they were taken, then sort them into Year/Month folders. If EXIF data is not available, the file creation date will be used.

### Cleaning Photos

#### Remove Duplicates

Finds and removes duplicate photos by comparing names, sizes, and content. Keeps the oldest file and removes newer duplicates.

#### Remove Blurry Photos

Detects and removes blurry images based on a sharpness threshold. Lower threshold = more aggressive (removes more images).

#### Remove Small Photos

Finds and removes images smaller than a specified dimension.

#### Clean DNG+JPG Pairs

Removes JPG files when a matching DNG/RAW file exists with the same base name.

### Converting RAW to JPG

1. Select your RAW files directory
2. Choose a destination directory for JPG files
3. Adjust the quality slider (higher = better quality but larger files)
4. Click "Convert RAW to JPG"

### Cloud Backup (In progress)

The Cloud Backup tab allows you to securely back up your photo collection to popular cloud storage services.

#### Supported Services

- **Dropbox**: Secure cloud storage with reliable sync
- **Google Drive**: Integrates with Google ecosystem
- **Amazon S3**: Enterprise-grade storage with excellent durability

#### Backing up Photos

1. Go to the "Cloud Backup" tab
2. Select your preferred cloud service (Dropbox, Google Drive, or AWS S3)
3. Click "Authenticate" to connect to your account
   - For Dropbox: You'll need to authorize the app via a web browser
   - For Google Drive: You'll need to provide OAuth credentials
   - For Amazon S3: You'll need to provide your AWS access key, secret key, and bucket name
4. Select the source directory containing photos you want to back up
5. Click "Backup to Cloud" to start the upload process

The backup will be organized in a folder named "Photo_Organizer_Backup" within your cloud storage, with each backup including a timestamp.

#### Restoring from Backup

1. Go to the "Cloud Backup" tab
2. Authenticate with your cloud service if needed
3. Click "Refresh Backups" to see available backups
4. Select a backup from the list
5. Choose a destination directory for the restored files
6. Click "Restore from Cloud" to download the backed up files

## AI features (TODO)
### Smart Content Tagging

Navigate to the "AI Features" tab and select "Smart Tagging"
1. Choose the directory containing your photos
1. Select detection categories (objects, scenes, activities)
1. Adjust the confidence threshold as needed (higher = more accurate but fewer detections)
1. Choose whether to save tags to image EXIF data or a CSV file
1. Click "Download Model" to download the required AI model (first time only)
1. Click "Run Smart Tagging" to begin the analysis

### Face Recognition

1. Navigate to the "AI Features" tab and select "Face Recognition"
1. Choose the directory containing your photos
1. Select recognition mode:
    - "Cluster similar faces" to group faces without identifying people
    - "Recognize known people" to match faces against a database


1. For clustering, specify the minimum number of photos needed to form a cluster
1. Click "Download Model" to download the required AI model (first time only)
1. Click "Run Face Recognition" to begin the analysis

### Image Enhancement

1. Navigate to the "AI Features" tab and select "Image Enhancement"
1. Choose between enhancing a single image or batch processing a directory
1. For single images:
    - Select an image file to enhance
    - Choose which enhancements to apply
    - Click "Enhance Image" to preview the results
    - If satisfied, click "Save Enhanced Image" to save the result
1. For batch processing:
    - Select source and output directories
    - Choose which enhancements to apply
    - Click "Enhance All Images" to process all images in the directory

### Troubleshooting

- **Model Download Issues**: If model download fails, check your internet connection and try again. Models are typically 100-200MB in size.
- **Memory Errors**: AI processing can be memory-intensive. For large collections, try processing in smaller batches.
- **Face Recognition Accuracy**: For best results, use clear, well-lit photos with faces at least 100x100 pixels in size.
- **Performance**: AI processing is computationally intensive and may take longer on older hardware. A dedicated GPU will significantly improve performance.

## Safety Tips

- **Always run with "Dry run" first** to see what changes will be made
- Back up your photos before using the cleaning features
- Keep your original RAW files even after converting to JPG
- Regularly backup your photo collection to cloud storage for extra protection
- Use different cloud services for critical backups to avoid single-point-of-failure

## Troubleshooting

- **Missing dependencies**: Run the setup script to install required packages
- **EXIF data not detected**: Install exiftool for better metadata extraction
- **Performance issues**: Processing large photo collections can be resource-intensive. Try working with smaller batches.
- **Cloud authentication failures**: 
  - For Dropbox: Make sure you allow the application in your browser
  - For Google Drive: Check that your OAuth credentials are correct and have the necessary permissions
  - For Amazon S3: Verify your access keys and bucket permissions

## Step-by-step for creating credentials:

For Dropbox:

Go to https://www.dropbox.com/developers/apps
Click "Create app"
Choose "Scoped access" API
Select "Full Dropbox" access type
Give your app a name (e.g., "MyPhotoOrganizer")
Click "Create app"
On the settings tab, find your App Key to use in the authentication

For Google Drive:

Go to https://console.cloud.google.com/
Create a new project
Enable the Google Drive API
Go to "Credentials" and create OAuth client ID credentials
Set the application type to Desktop application
Download the JSON file
Use this file when prompted during authentication

## Advanced Use

The application is built from modular Python scripts that can also be used independently:

- `photo_organizer.py` - Core functionality for organizing photos
- `remove_duplicates.py` - Dedicated duplicate cleaner
- `blur_detector.py` - Blurry photo detector
- `small_image_cleaner.py` - Small image cleaner
- `dng_jpg_cleaner.py` - RAW+JPG pair cleaner
- `raw_to_jpg.py` - RAW converter
- `cloud_backup.py` - Cloud storage integration

Each script can be run directly from the command line with its own options.

### Command-line Cloud Backup

The cloud backup functionality can be used from the command line:

```
python cloud_backup.py --service dropbox --action auth
python cloud_backup.py --service gdrive --action backup --source /path/to/photos
python cloud_backup.py --service s3 --action list
python cloud_backup.py --service dropbox --action restore --backup-id <backup_id> --dest /path/to/restore
```

## Future Enhancements

Future versions will include:
- Facial recognition for organization
- AI-powered photo tagging
- Batch editing features
- Enhanced cloud backup features with scheduled backups
- Photo album creation

## License

This software is provided as-is under the MIT license.

## Contact

For support or feature requests, please open an issue on the project repository.