from pathlib import Path
import argparse
from PIL import Image
from typing import Tuple, List
import humanize

class SmallImageCleaner:
    def __init__(self, directory: Path, max_dimension: int = 400, dry_run: bool = True):
        self.directory = directory
        self.max_dimension = max_dimension
        self.dry_run = dry_run
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
        # Statistics
        self.files_processed = 0
        self.files_deleted = 0
        self.space_saved = 0
        self.errors = []

    def get_image_dimensions(self, file_path: Path) -> Tuple[int, int]:
        """Get image dimensions safely."""
        try:
            with Image.open(file_path) as img:
                return img.size
        except Exception as e:
            self.errors.append(f"Error reading {file_path}: {e}")
            return (0, 0)

    def is_image_small(self, dimensions: Tuple[int, int]) -> bool:
        """Check if image is smaller than max dimension."""
        width, height = dimensions
        return width <= self.max_dimension and height <= self.max_dimension

    def find_small_images(self) -> List[Tuple[Path, int, Tuple[int, int]]]:
        """Find all small images in directory."""
        small_images = []
        
        for file_path in self.directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                self.files_processed += 1
                dimensions = self.get_image_dimensions(file_path)
                
                if dimensions == (0, 0):  # Skip files with errors
                    continue
                    
                if self.is_image_small(dimensions):
                    try:
                        size = file_path.stat().st_size
                        small_images.append((file_path, size, dimensions))
                    except Exception as e:
                        self.errors.append(f"Error getting size of {file_path}: {e}")
                        continue
        
        return small_images

    def clean_small_images(self) -> None:
        """Remove small images from directory."""
        small_images = self.find_small_images()
        
        if not small_images:
            print("No small images found!")
            return

        print(f"\nFound {len(small_images)} images smaller than {self.max_dimension}x{self.max_dimension}:")
        
        # Sort by size (smallest first)
        small_images.sort(key=lambda x: x[1])
        
        for file_path, size, dimensions in small_images:
            print(f"  {file_path}")
            print(f"    Size: {humanize.naturalsize(size)}")
            print(f"    Dimensions: {dimensions[0]}x{dimensions[1]}")
            
            if not self.dry_run:
                try:
                    file_path.unlink()
                    self.files_deleted += 1
                    self.space_saved += size
                except Exception as e:
                    self.errors.append(f"Error deleting {file_path}: {e}")
            else:
                self.files_deleted += 1
                self.space_saved += size

        # Print summary
        print("\nSummary:")
        action = "Would delete" if self.dry_run else "Deleted"
        print(f"Files processed: {self.files_processed}")
        print(f"{action} {self.files_deleted} small images")
        print(f"Space saved: {humanize.naturalsize(self.space_saved)}")
        
        if self.errors:
            print("\nErrors encountered:")
            for error in self.errors:
                print(f"  {error}")

def main():
    parser = argparse.ArgumentParser(description='Find and remove images smaller than specified dimensions')
    parser.add_argument('directory', type=Path, help='Directory to scan for small images')
    parser.add_argument('--max-dimension', type=int, default=400, 
                        help='Maximum dimension (width or height) in pixels (default: 400)')
    parser.add_argument('--delete', action='store_true', 
                        help='Actually delete files (default is dry run)')
    
    args = parser.parse_args()
    
    if not args.directory.exists():
        print("Directory does not exist!")
        return
    
    cleaner = SmallImageCleaner(args.directory, args.max_dimension, dry_run=not args.delete)
    cleaner.clean_small_images()

if __name__ == "__main__":
    main()