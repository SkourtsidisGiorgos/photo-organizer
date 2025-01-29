from pathlib import Path
from datetime import datetime
import shutil
import argparse
import time
from typing import Dict, Set
import humanize
import psutil
from tqdm import tqdm
from statistics import mean

class PhotoOrganizer:
    def __init__(self, source_dir: Path, dest_dir: Path, move_files: bool = False, dry_run: bool = False):
        self.source_dir = source_dir
        self.dest_dir = dest_dir
        self.move_files = move_files
        self.dry_run = dry_run
        self.supported_formats = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.dng', '.raw', '.cr2', '.nef', '.arw', '.mov', '.mp4', '.avi'}  # Added more video formats
        self.failed_files: Set[Path] = set()
        self.retry_count = 3
        self.total_size = 0
        self.processed_size = 0
        self.start_time = time.time()
        self.file_stats = {
            'sizes': [],
            'dates': []
        }

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

    def process_file(self, file_path: Path, file_size: int, pbar: tqdm) -> bool:
        """Process a single file with retries. In dry-run mode, only simulates the operations."""
        for attempt in range(self.retry_count):
            try:
                # Get last modified time
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                # Create year/month path
                year = str(mtime.year)
                month = str(mtime.month).zfill(2)
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
                    # Wait and retry if file is locked
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
                time.sleep(1)  # Wait before retry
        
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