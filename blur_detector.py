from pathlib import Path
import cv2
import argparse
from typing import List, Tuple
import humanize

class BlurryImageCleaner:
    def __init__(self, directory: Path, threshold: float = 100.0, dry_run: bool = True):
        self.directory = directory
        self.threshold = threshold
        self.dry_run = dry_run
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp'}
        # Statistics
        self.files_processed = 0
        self.files_deleted = 0
        self.space_saved = 0
        self.errors = []

    def get_blur_score(self, image_path: Path) -> float:
        """Calculate blur score using Laplacian variance. Lower = blurrier."""
        try:
            # Read image in grayscale
            img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
            if img is None:
                raise ValueError("Failed to load image")
            
            # Calculate Laplacian variance
            laplacian = cv2.Laplacian(img, cv2.CV_64F)
            score = laplacian.var()
            
            return score
        except Exception as e:
            self.errors.append(f"Error processing {image_path}: {e}")
            return float('inf')  # Return infinity to skip this image

    def find_blurry_images(self) -> List[Tuple[Path, float, int]]:
        """Find all blurry images in directory."""
        blurry_images = []
        
        print("Scanning for blurry images...")
        for file_path in self.directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                self.files_processed += 1
                
                # Calculate blur score
                score = self.get_blur_score(file_path)
                if score == float('inf'):  # Skip error cases
                    continue
                
                if score < self.threshold:
                    try:
                        size = file_path.stat().st_size
                        blurry_images.append((file_path, score, size))
                    except Exception as e:
                        self.errors.append(f"Error getting size of {file_path}: {e}")
                        continue
        
        return blurry_images

    def clean_blurry_images(self) -> None:
        """Remove blurry images from directory."""
        blurry_images = self.find_blurry_images()
        
        if not blurry_images:
            print("No blurry images found!")
            return

        print(f"\nFound {len(blurry_images)} blurry images (threshold: {self.threshold}):")
        
        # Sort by blur score (blurriest first)
        blurry_images.sort(key=lambda x: x[1])
        
        for file_path, score, size in blurry_images:
            print(f"\n  {file_path}")
            print(f"    Blur score: {score:.2f}")
            print(f"    Size: {humanize.naturalsize(size)}")
            
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
        print(f"{action} {self.files_deleted} blurry images")
        print(f"Space saved: {humanize.naturalsize(self.space_saved)}")
        
        if self.errors:
            print("\nErrors encountered:")
            for error in self.errors:
                print(f"  {error}")

def main():
    parser = argparse.ArgumentParser(description='Find and remove blurry images')
    parser.add_argument('directory', type=Path, help='Directory to scan for blurry images')
    parser.add_argument('--threshold', type=float, default=100.0,
                        help='Blur threshold (lower = more aggressive, default: 100.0)')
    parser.add_argument('--delete', action='store_true',
                        help='Actually delete files (default is dry run)')
    
    args = parser.parse_args()
    
    if not args.directory.exists():
        print("Directory does not exist!")
        return
    
    cleaner = BlurryImageCleaner(args.directory, args.threshold, dry_run=not args.delete)
    cleaner.clean_blurry_images()

if __name__ == "__main__":
    main()