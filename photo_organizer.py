from pathlib import Path
from datetime import datetime
import shutil
import argparse
import time
from typing import Dict, Set, Optional
import humanize
import psutil
from tqdm import tqdm
from statistics import mean
from PIL import Image
from PIL.ExifTags import TAGS
import subprocess
import json
import os

class PhotoOrganizer:
    def __init__(self, source_dir: Path, dest_dir: Path, move_files: bool = False, dry_run: bool = False):
        self.source_dir = source_dir
        self.dest_dir = dest_dir
        self.move_files = move_files
        self.dry_run = dry_run
        self.image_formats = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif'}
        self.raw_formats = {'.dng', '.raw', '.cr2', '.nef', '.arw'}
        self.video_formats = {'.mov', '.mp4', '.avi'}
        self.supported_formats = self.image_formats | self.raw_formats | self.video_formats
        self.failed_files: Set[Path] = set()
        self.retry_count = 3
        self.total_size = 0
        self.processed_size = 0
        self.start_time = time.time()
        self.file_stats = {
            'sizes': [],
            'dates': []
        }

    def get_exif_date_pillow(self, file_path: Path) -> Optional[datetime]:
        """Extract date from EXIF using Pillow for standard image formats."""
        try:
            with Image.open(file_path) as img:
                # GIF and some other formats don't support EXIF
                if file_path.suffix.lower() == '.gif':
                    return None
                    
                # Only try to get EXIF if the image format supports it
                if hasattr(img, '_getexif'):
                    exif = img._getexif()
                    if not exif:
                        return None
                
                # List of EXIF tags to check for date information
                date_tags = [36867,  # DateTimeOriginal
                           36868,  # DateTimeDigitized
                           306]    # DateTime
                
                for tag in date_tags:
                    if tag in exif:
                        try:
                            # Parse standard EXIF date format "YYYY:MM:DD HH:MM:SS"
                            date_str = exif[tag]
                            return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                        except (ValueError, TypeError):
                            continue
        except Exception as e:
            print(f"\nError reading EXIF from {file_path}: {e}")
        return None

    def get_exif_date_exiftool(self, file_path: Path) -> Optional[datetime]:
        try:
            test_result = subprocess.run(['exiftool', '-ver'], 
                                        capture_output=True, 
                                        text=True, 
                                        timeout=1)
            if test_result.returncode != 0:
                print(f"\nExiftool test failed: {test_result.stderr}")
                return None
        except (subprocess.SubprocessError, FileNotFoundError):
            print(f"""\nExiftool not found. Install it for better metadata extraction.
- On Ubuntu/Debian: sudo apt-get install libimage-exiftool-perl
- On macOS with Homebrew: brew install exiftool
- On Windows: Download and install from ExifTool's official website https://exiftool.org/
""")
            return None
        try:
            result = subprocess.run([
                'exiftool',
                '-json',
                '-DateTimeOriginal',
                '-CreateDate',
                '-MediaCreateDate',
                '-TrackCreateDate',
                str(file_path)
            ], capture_output=True, text=True)

            if result.returncode == 0:
                data = json.loads(result.stdout)[0]
                
                # Check various date fields in order of preference
                date_fields = [
                    'DateTimeOriginal',
                    'CreateDate',
                    'MediaCreateDate',
                    'TrackCreateDate'
                ]

                for field in date_fields:
                    if field in data and data[field]:
                        try:
                            # Handle various date formats
                            date_str = data[field].split('+')[0]  # Remove timezone if present
                            return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                        except (ValueError, TypeError):
                            continue
                            
        except (subprocess.SubprocessError, json.JSONDecodeError, IndexError) as e:
            print(f"\nError using exiftool for {file_path}: {e}")
        return None

    def get_file_date(self, file_path: Path) -> datetime:
        """Get the file date using the best available method."""
        date = None
        suffix = file_path.suffix.lower()

        # Try EXIF data first for supported formats
        if suffix in self.image_formats:
            date = self.get_exif_date_pillow(file_path)
        
        # If Pillow failed or for other formats, try exiftool
        if date is None and (suffix in self.raw_formats or suffix in self.video_formats or suffix in self.image_formats):
            date = self.get_exif_date_exiftool(file_path)

        # Fall back to file modification time if no EXIF data available
        if date is None:
            try:
                # Try creation time first (Windows)
                if os.name == 'nt':
                    date = datetime.fromtimestamp(file_path.stat().st_ctime)
                else:
                    # Use modification time as last resort
                    date = datetime.fromtimestamp(file_path.stat().st_mtime)
            except Exception as e:
                print(f"\nError getting file time for {file_path}: {e}")
                # Use current time as absolute last resort
                date = datetime.now()

        return date

    def process_file(self, file_path: Path, file_size: int, pbar: tqdm) -> bool:
        """Process a single file with retries. In dry-run mode, only simulates the operations."""
        for attempt in range(self.retry_count):
            try:
                # Get file date using EXIF or fallback methods
                file_date = self.get_file_date(file_path)
                
                # Create year/month path
                year = str(file_date.year)
                month = str(file_date.month).zfill(2)
                target_dir = self.dest_dir / year / month
                
                # Create directory with error handling
                try:
                    target_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    print(f"\nError creating directory {target_dir}: {e}")
                    return False
                
                destination = target_dir / file_path.name
                
                # Handle duplicate files
                if destination.exists():
                    base = destination.stem
                    suffix = destination.suffix
                    counter = 1
                    while destination.exists():
                        destination = target_dir / f"{base}_{counter}{suffix}"
                        counter += 1
                
                # Copy or move the file with exclusive access
                operation = "Moving" if self.move_files else "Copying"
                if self.dry_run:
                    operation = f"Would {operation.lower()}"
                pbar.set_description(f"{operation} {file_path.name}")
                
                if self.dry_run:
                    print(f"{operation} {file_path} -> {destination}")
                    self.processed_size += file_size
                    pbar.update(file_size)
                    return True
                
                try:
                    if self.move_files:
                        shutil.move(str(file_path), str(destination))
                    else:
                        shutil.copy2(str(file_path), str(destination))
                except PermissionError:
                    time.sleep(1)
                    continue
                
                # Verify file integrity
                if not self.verify_file_integrity(file_path, destination, file_size):
                    raise ValueError("File integrity check failed after transfer")
                
                self.processed_size += file_size
                pbar.update(file_size)
                return True
                
            except Exception as e:
                if attempt == self.retry_count - 1:
                    self.failed_files.add(file_path)
                    print(f"\nFailed to process {file_path.name} after {self.retry_count} attempts: {e}")
                    return False
                print(f"\nRetrying {file_path.name} (attempt {attempt + 2}/{self.retry_count})")
                time.sleep(1)
        
        return False

    def get_all_files(self) -> Dict[Path, int]:
        """Get all supported files and their sizes."""
        files_dict = {}
        print("Scanning for supported image and video files...")
        try:
            for file_path in self.source_dir.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                    try:
                        size = file_path.stat().st_size
                        mtime = file_path.stat().st_mtime
                        files_dict[file_path] = size
                        self.file_stats['sizes'].append(size)
                        self.file_stats['dates'].append(mtime)
                    except (PermissionError, FileNotFoundError, OSError) as e:
                        print(f"\nError accessing {file_path}: {e}")
                        continue
        except Exception as e:
            print(f"\nError while scanning directory: {e}")
        return files_dict

    def check_disk_space(self, total_size: int) -> bool:
        """Check if destination has enough space with safety margin."""
        try:
            dest_free_space = psutil.disk_usage(str(self.dest_dir)).free
            safety_margin = 1024 * 1024 * 100  # 100MB safety margin
            needed_space = total_size + safety_margin if not self.move_files else safety_margin
            if dest_free_space < needed_space:
                print(f"\nNot enough space in destination drive!")
                print(f"Required: {humanize.naturalsize(needed_space)}")
                print(f"Available: {humanize.naturalsize(dest_free_space)}")
                return False
            return True
        except Exception as e:
            print(f"\nError checking disk space: {e}")
            return False

    def verify_file_integrity(self, source: Path, destination: Path, original_size: int) -> bool:
        """Verify file integrity after transfer."""
        try:
            if not destination.exists():
                return False
            if destination.stat().st_size != original_size:
                return False
            # Optional: Add hash comparison if needed
            return True
        except Exception as e:
            print(f"\nError verifying file integrity: {e}")
            return False

    def print_statistics(self):
        """Print file statistics."""
        if not self.file_stats['sizes']:
            print("\nNo files processed, no statistics available.")
            return

        print("\nFile Statistics:")
        print(f"Max file size: {humanize.naturalsize(max(self.file_stats['sizes']))}")
        print(f"Min file size: {humanize.naturalsize(min(self.file_stats['sizes']))}")
        print(f"Average file size: {humanize.naturalsize(mean(self.file_stats['sizes']))}")
        
        oldest_date = datetime.fromtimestamp(min(self.file_stats['dates']))
        newest_date = datetime.fromtimestamp(max(self.file_stats['dates']))
        print(f"Oldest file date: {oldest_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Newest file date: {newest_date.strftime('%Y-%m-%d %H:%M:%S')}")

    def organize(self):
        """Main organization method with progress tracking."""
        try:
            files_dict = self.get_all_files()
            
            if not files_dict:
                print("No supported files found!")
                return
            
            total_files = len(files_dict)
            self.total_size = sum(files_dict.values())
            
            print(f"\nFound {total_files} files ({humanize.naturalsize(self.total_size)})")
            
            if not self.check_disk_space(self.total_size):
                return
            
            # Create progress bar
            with tqdm(total=self.total_size, unit='B', unit_scale=True) as pbar:
                # Process files sequentially
                for file_path, file_size in files_dict.items():
                    self.process_file(file_path, file_size, pbar)
            
            # Summary
            end_time = time.time()
            duration = end_time - self.start_time
            successful = total_files - len(self.failed_files)
            
            print("\nTransfer Complete!")
            print(f"Duration: {humanize.naturaltime(duration)}")
            print(f"Files processed: {successful}/{total_files}")
            print(f"Total size: {humanize.naturalsize(self.total_size)}")
            
            if duration > 0:  # Avoid division by zero
                print(f"Average speed: {humanize.naturalsize(self.total_size/duration)}/s")
            
            # Print statistics
            self.print_statistics()
            
            if self.failed_files:
                print(f"\nFailed files ({len(self.failed_files)}):")
                for file in self.failed_files:
                    print(f"- {file}")
                print("\nYou can retry failed files by running the script again.")

        except Exception as e:
            print(f"\nAn unexpected error occurred during organization: {e}")

def main():
    parser = argparse.ArgumentParser(description='Organize photos into year/month folders by last modified date')
    parser.add_argument('source', type=Path, help='Source directory containing photos')
    parser.add_argument('destination', type=Path, help='Destination directory for organized photos')
    parser.add_argument('--move', action='store_true', help='Move files instead of copying them')
    parser.add_argument('--dry-run', action='store_true', help='Simulate the organization without actually copying/moving files')
    
    args = parser.parse_args()
    
    # Validate directories
    if not args.source.exists():
        print("Source directory does not exist!")
        return
    
    # Create destination if it doesn't exist
    try:
        args.destination.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Error creating destination directory: {e}")
        return
    
    try:
        # Run organization
        organizer = PhotoOrganizer(args.source, args.destination, args.move, args.dry_run)
        organizer.organize()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user. Partially processed files remain in destination.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    main()