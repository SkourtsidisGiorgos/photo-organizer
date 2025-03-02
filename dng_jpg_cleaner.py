from pathlib import Path
import argparse
import re
from typing import Dict, List, Tuple

class DNGJPGCleaner:
    def __init__(self, directory: Path, dry_run: bool = True):
        self.directory = directory
        self.dry_run = dry_run
        self.pairs_found = 0
        self.space_saved = 0
        self.files_deleted = 0

    def get_base_name(self, filename: str) -> str:
        """Extract base name without extension and any duplicate indicators"""
        # Remove extension
        base = filename.rsplit('.', 1)[0]
        # Remove _1, _2, etc. suffixes if present
        pattern = r'^(IMG_\d+_\d+)(?:_\d+)?$'
        match = re.match(pattern, base)
        if match:
            return match.group(1)
        return base

    def find_pairs(self) -> List[Tuple[Path, Path]]:
        """Find pairs of DNG and JPG files representing the same image"""
        files_by_base: Dict[str, List[Path]] = {}
        
        # Group files by base name
        for file_path in self.directory.rglob('*'):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in ['.dng', '.jpg', '.jpeg']:
                    base_name = self.get_base_name(file_path.name)
                    if base_name not in files_by_base:
                        files_by_base[base_name] = []
                    files_by_base[base_name].append(file_path)

        # Find DNG/JPG pairs
        pairs: List[Tuple[Path, Path]] = []
        
        for base_name, files in files_by_base.items():
            dng_files = [f for f in files if f.suffix.lower() == '.dng']
            jpg_files = [f for f in files if f.suffix.lower() in ['.jpg', '.jpeg']]
            
            # If we have both DNG and JPG for the same base name
            if dng_files and jpg_files:
                # Use creation time to match pairs
                for dng in dng_files:
                    dng_time = dng.stat().st_ctime
                    # Find JPG with closest creation time
                    matching_jpg = min(jpg_files, 
                                    key=lambda jpg: abs(jpg.stat().st_ctime - dng_time))
                    # Only include if creation times are within 2 seconds of each other
                    if abs(matching_jpg.stat().st_ctime - dng_time) < 2:
                        pairs.append((dng, matching_jpg))

        return pairs

    def clean_pairs(self) -> None:
        """Remove JPG files when matching DNG exists"""
        pairs = self.find_pairs()
        
        if not pairs:
            print("No DNG/JPG pairs found!")
            return

        print(f"\nFound {len(pairs)} DNG/JPG pairs:")
        
        for dng, jpg in pairs:
            print(f"\nDNG: {dng}")
            jpg_size = jpg.stat().st_size
            print(f"JPG to remove: {jpg} ({jpg_size:,} bytes)")
            
            if not self.dry_run:
                try:
                    self.space_saved += jpg_size
                    jpg.unlink()
                    self.files_deleted += 1
                except Exception as e:
                    print(f"Error deleting {jpg}: {e}")
            else:
                self.space_saved += jpg_size
            
            self.pairs_found += 1

        # Print summary
        action = "Would delete" if self.dry_run else "Deleted"
        print(f"\nSummary:")
        print(f"{action} {self.pairs_found} JPG files")
        print(f"Space saved: {self.space_saved:,} bytes ({self.space_saved / 1024 / 1024:.2f} MB)")

def main():
    parser = argparse.ArgumentParser(description='Remove JPG files when matching DNG exists')
    parser.add_argument('directory', type=Path, help='Directory to scan')
    parser.add_argument('--delete', action='store_true', help='Actually delete files (default is dry run)')
    
    args = parser.parse_args()
    
    if not args.directory.exists():
        print("Directory does not exist!")
        return
    
    cleaner = DNGJPGCleaner(args.directory, dry_run=not args.delete)
    cleaner.clean_pairs()

if __name__ == "__main__":
    main()