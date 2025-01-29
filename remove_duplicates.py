from pathlib import Path
import re
import argparse
from typing import Dict, List, Set, Tuple
import hashlib

class DuplicateCleaner:
    def __init__(self, directory: Path, dry_run: bool = True):
        self.directory = directory
        self.dry_run = dry_run
        # Track statistics
        self.duplicates_found = 0
        self.space_saved = 0
        self.files_deleted = 0

    def get_base_name(self, filename: str) -> str:
        """Extract base name without _1, _2, etc. suffix"""
        # Match pattern like "name_1.jpg" or "name (1).jpg"
        pattern = r'^(.+?)(?:_\d+|\s+\(\d+\))(\.[^.]+)$'
        match = re.match(pattern, filename)
        if match:
            return match.group(1) + match.group(2)
        return filename

    def calculate_file_hash(self, file_path: Path, block_size: int = 65536) -> str:
        """Calculate SHA-256 hash of a file for content comparison"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(block_size), b""):
                sha256_hash.update(block)
        return sha256_hash.hexdigest()

    def find_duplicates(self) -> List[Tuple[Path, List[Path]]]:
        """Find duplicate files based on name pattern and size"""
        # Dictionary to store files by their base name
        files_by_base: Dict[str, List[Path]] = {}
        
        # First pass: Group files by base name
        for file_path in self.directory.rglob('*'):
            if file_path.is_file():
                base_name = self.get_base_name(file_path.name)
                if base_name not in files_by_base:
                    files_by_base[base_name] = []
                files_by_base[base_name].append(file_path)

        # Second pass: Filter groups with potential duplicates
        duplicate_groups: List[Tuple[Path, List[Path]]] = []
        
        for base_name, file_paths in files_by_base.items():
            if len(file_paths) > 1:
                # Sort files by creation time (oldest first)
                file_paths.sort(key=lambda x: x.stat().st_ctime)
                
                # Group files by size
                size_groups: Dict[int, List[Path]] = {}
                for path in file_paths:
                    size = path.stat().st_size
                    if size not in size_groups:
                        size_groups[size] = []
                    size_groups[size].append(path)
                
                # Check each size group
                for size, paths in size_groups.items():
                    if len(paths) > 1:
                        # Keep the oldest file (first in the sorted list)
                        original = paths[0]
                        duplicates = paths[1:]
                        
                        # Verify content is identical using hash
                        original_hash = self.calculate_file_hash(original)
                        confirmed_duplicates = []
                        
                        for dup in duplicates:
                            if self.calculate_file_hash(dup) == original_hash:
                                confirmed_duplicates.append(dup)
                        
                        if confirmed_duplicates:
                            duplicate_groups.append((original, confirmed_duplicates))

        return duplicate_groups

    def clean_duplicates(self) -> None:
        """Remove duplicate files"""
        duplicate_groups = self.find_duplicates()
        
        if not duplicate_groups:
            print("No duplicates found!")
            return

        print(f"\nFound {len(duplicate_groups)} groups of duplicates:")
        
        for original, duplicates in duplicate_groups:
            print(f"\nOriginal: {original}")
            print("Duplicates to remove:")
            total_size = 0
            
            for dup in duplicates:
                size = dup.stat().st_size
                total_size += size
                print(f"  - {dup} ({size:,} bytes)")
            
            if not self.dry_run:
                for dup in duplicates:
                    try:
                        dup.unlink()
                        self.files_deleted += 1
                        self.space_saved += dup.stat().st_size
                    except Exception as e:
                        print(f"Error deleting {dup}: {e}")
            
            self.duplicates_found += len(duplicates)
            if self.dry_run:
                self.space_saved += total_size

        # Print summary
        action = "Would delete" if self.dry_run else "Deleted"
        print(f"\nSummary:")
        print(f"{action} {self.duplicates_found} duplicate files")
        print(f"Space saved: {self.space_saved:,} bytes ({self.space_saved / 1024 / 1024:.2f} MB)")

def main():
    parser = argparse.ArgumentParser(description='Find and remove duplicate files based on naming pattern and size')
    parser.add_argument('directory', type=Path, help='Directory to scan for duplicates')
    parser.add_argument('--delete', action='store_true', help='Actually delete files (default is dry run)')
    
    args = parser.parse_args()
    
    if not args.directory.exists():
        print("Directory does not exist!")
        return
    
    cleaner = DuplicateCleaner(args.directory, dry_run=not args.delete)
    cleaner.clean_duplicates()

if __name__ == "__main__":
    main()