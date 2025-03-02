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

## Installation

### Requirements

- Python 3.6 or higher
- Required packages: pillow, rawpy, opencv-python, tqdm, imageio, humanize, psutil
- Optional: exiftool (for better metadata extraction)

### Easy Installation
0. (Recommended) `python -m venv venv && source venv/bin/activate`
1. Download the application files
2. Run the setup script: `python setup.py`

### Manual Installation

1. Install required Python packages:
   ```
   pip install pillow rawpy opencv-python tqdm imageio humanize psutil
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

## Safety Tips

- **Always run with "Dry run" first** to see what changes will be made
- Back up your photos before using the cleaning features
- Keep your original RAW files even after converting to JPG

## Troubleshooting

- **Missing dependencies**: Run the setup script to install required packages
- **EXIF data not detected**: Install exiftool for better metadata extraction
- **Performance issues**: Processing large photo collections can be resource-intensive. Try working with smaller batches.

## Advanced Use

The application is built from modular Python scripts that can also be used independently:

- `photo_organizer.py` - Core functionality for organizing photos
- `remove_duplicates.py` - Dedicated duplicate cleaner
- `blur_detector.py` - Blurry photo detector
- `small_image_cleaner.py` - Small image cleaner
- `dng_jpg_cleaner.py` - RAW+JPG pair cleaner
- `raw_to_jpg.py` - RAW converter

Each script can be run directly from the command line with its own options.

## Future Enhancements

Future versions will include:
- Facial recognition for organization
- AI-powered photo tagging
- Batch editing features
- Cloud backup integration
- Photo album creation

## License

This software is provided as-is under the MIT license.

## Contact

For support or feature requests, please open an issue on the project repository.