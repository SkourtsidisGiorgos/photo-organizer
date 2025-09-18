from pathlib import Path
import re
import argparse
from typing import Dict, List, Tuple
import hashlib
from collections import defaultdict
import concurrent.futures
import os
import mmap
import time
from dataclasses import dataclass

# Try to import faster alternatives
try:
    import xxhash
    FAST_HASH = xxhash.xxh64
except ImportError:
    FAST_HASH = None

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

@dataclass
class FileInfo:
    path: Path
    size: int
    ctime: float
    base_name: str
    inode: int = 0
    device: int = 0

class UltraFastDuplicateCleaner:
    def __init__(self, directory: Path, dry_run: bool = True, max_workers: int = None):
        self.directory = directory
        self.dry_run = dry_run
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        
        # Statistics
        self.duplicates_found = 0
        self.space_saved = 0
        self.files_deleted = 0
        
        # Ultra-fast settings
        self.quick_hash_size = 4096      # Smaller samples for speed
        self.min_file_size = 512         # Even smaller threshold
        self.use_mmap = True             # Memory-mapped files for large files
        self.mmap_threshold = 1024 * 1024  # 1MB threshold for mmap
        self.max_quick_sample_files = 1000  # Limit quick sampling for huge dirs
        
        # Pre-compile regex patterns
        self._base_name_patterns = [
            re.compile(r'^(IMG_\d+_\d+)(?:_\d+)?(\.[^.]+)$'),
            re.compile(r'^(.+?)(?:_\d+|\s+\(\d+\))(\.[^.]+)$')
        ]
        
        # Hash function selection
        self.quick_hasher = FAST_HASH if FAST_HASH else hashlib.md5
        
        # Reusable buffer for reading
        self._buffer = bytearray(self.quick_hash_size)

    def get_base_name(self, filename: str) -> str:
        """Optimized base name extraction with cached patterns"""
        for pattern in self._base_name_patterns:
            match = pattern.match(filename)
            if match:
                return match.group(1) + match.group(2)
        return filename

    def ultra_quick_hash(self, file_path: Path, size: int) -> str:
        """Ultra-fast hash using minimal I/O and fastest algorithms"""
        try:
            if FAST_HASH:
                hasher = FAST_HASH()
            else:
                hasher = hashlib.md5()
            
            # Include size in hash to avoid collisions
            hasher.update(str(size).encode())
            
            if size <= self.quick_hash_size:
                # Small file: read entirely
                with open(file_path, "rb") as f:
                    data = f.read()
                    hasher.update(data)
            elif size <= self.mmap_threshold or not self.use_mmap:
                # Medium file: strategic sampling
                with open(file_path, "rb") as f:
                    # Read into reusable buffer
                    bytes_read = f.readinto(self._buffer)
                    if bytes_read:
                        hasher.update(self._buffer[:bytes_read])
                    
                    if size > self.quick_hash_size * 2:
                        # Jump to end
                        f.seek(-self.quick_hash_size, 2)
                        bytes_read = f.readinto(self._buffer)
                        if bytes_read:
                            hasher.update(self._buffer[:bytes_read])
            else:
                # Large file: use memory mapping
                with open(file_path, "rb") as f:
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                        # Sample beginning
                        hasher.update(mm[:self.quick_hash_size])
                        # Sample end
                        if size > self.quick_hash_size:
                            hasher.update(mm[-self.quick_hash_size:])
                        # Sample middle for very large files
                        if size > self.quick_hash_size * 100:
                            mid = size // 2
                            hasher.update(mm[mid:mid + self.quick_hash_size])
            
            return hasher.hexdigest()
        except (OSError, IOError, ValueError):
            return f"error_{size}_{hash(str(file_path))}"

    def full_hash_mmap(self, file_path: Path) -> str:
        """Memory-mapped full file hashing for large files"""
        try:
            if FAST_HASH:
                hasher = FAST_HASH()
            else:
                hasher = hashlib.md5()
            
            size = file_path.stat().st_size
            
            if size <= self.mmap_threshold:
                # Use regular file reading for smaller files
                with open(file_path, "rb") as f:
                    while True:
                        chunk = f.read(1048576)  # 1MB chunks
                        if not chunk:
                            break
                        hasher.update(chunk)
            else:
                # Use memory mapping for large files
                with open(file_path, "rb") as f:
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                        # Process in chunks to avoid memory issues
                        chunk_size = 16 * 1024 * 1024  # 16MB chunks
                        for i in range(0, len(mm), chunk_size):
                            hasher.update(mm[i:i + chunk_size])
            
            return hasher.hexdigest()
        except (OSError, IOError, ValueError):
            return f"error_{file_path}"

    def ultra_fast_scan(self) -> List[FileInfo]:
        """Ultra-optimized file scanning using os.scandir"""
        files = []
        
        def scan_directory(dir_path: Path):
            try:
                with os.scandir(dir_path) as entries:
                    for entry in entries:
                        if entry.is_file(follow_symlinks=False):
                            try:
                                stat_result = entry.stat(follow_symlinks=False)
                                size = stat_result.st_size
                                
                                if size >= self.min_file_size:
                                    base_name = self.get_base_name(entry.name)
                                    files.append(FileInfo(
                                        path=Path(entry.path),
                                        size=size,
                                        ctime=stat_result.st_ctime,
                                        base_name=base_name,
                                        inode=stat_result.st_ino,
                                        device=stat_result.st_dev
                                    ))
                            except (OSError, IOError):
                                continue
                        elif entry.is_dir(follow_symlinks=False):
                            scan_directory(Path(entry.path))
            except (OSError, IOError):
                pass
        
        scan_directory(self.directory)
        return files

    def detect_hardlinks(self, files: List[FileInfo]) -> List[FileInfo]:
        """Remove hard links from consideration (same inode = same file)"""
        seen_inodes = set()
        unique_files = []
        
        for file_info in files:
            inode_key = (file_info.device, file_info.inode)
            if inode_key not in seen_inodes:
                seen_inodes.add(inode_key)
                unique_files.append(file_info)
        
        return unique_files

    def smart_grouping(self, files: List[FileInfo]) -> Dict[str, Dict[int, List[FileInfo]]]:
        """Ultra-fast grouping with early size-based filtering"""
        # First pass: group by size only
        size_groups = defaultdict(list)
        for file_info in files:
            size_groups[file_info.size].append(file_info)
        
        # Filter out unique sizes immediately
        potential_duplicates = {size: files for size, files in size_groups.items() if len(files) > 1}
        
        if not potential_duplicates:
            return {}
        
        # Second pass: group by base name within size groups
        result = defaultdict(lambda: defaultdict(list))
        for size, file_list in potential_duplicates.items():
            for file_info in file_list:
                result[file_info.base_name][size].append(file_info)
        
        # Final filter: only keep groups with multiple files
        filtered_result = {}
        for base_name, size_groups in result.items():
            filtered_size_groups = {size: files for size, files in size_groups.items() if len(files) > 1}
            if filtered_size_groups:
                filtered_result[base_name] = filtered_size_groups
        
        return filtered_result

    def batch_process_groups(self, grouped_files: Dict[str, Dict[int, List[FileInfo]]]) -> List[Tuple[FileInfo, List[FileInfo]]]:
        """Process multiple groups in parallel batches"""
        all_size_groups = []
        for base_name, size_groups in grouped_files.items():
            for size, file_list in size_groups.items():
                all_size_groups.append(file_list)
        
        if not all_size_groups:
            return []
        
        print(f"Processing {len(all_size_groups)} potential duplicate groups...")
        
        all_duplicates = []
        
        # Process in parallel batches
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_group = {
                executor.submit(self.process_size_group_ultra_fast, group): group 
                for group in all_size_groups
            }
            
            completed = 0
            for future in concurrent.futures.as_completed(future_to_group):
                try:
                    duplicates = future.result()
                    all_duplicates.extend(duplicates)
                except Exception as e:
                    print(f"Error processing group: {e}")
                
                completed += 1
                if completed % 50 == 0 or completed == len(all_size_groups):
                    print(f"Processed {completed}/{len(all_size_groups)} groups...")
        
        return all_duplicates

    def process_size_group_ultra_fast(self, files: List[FileInfo]) -> List[Tuple[FileInfo, List[FileInfo]]]:
        """Ultra-fast processing of files with same size"""
        if len(files) < 2:
            return []
        
        # Sort by creation time (oldest first)
        files.sort(key=lambda x: x.ctime)
        
        # Quick hash phase - ultra fast
        quick_groups = defaultdict(list)
        for file_info in files:
            qhash = self.ultra_quick_hash(file_info.path, file_info.size)
            quick_groups[qhash].append(file_info)
        
        # Full verification phase - only for matches
        duplicate_groups = []
        for qhash, matching_files in quick_groups.items():
            if len(matching_files) > 1:
                # Full hash verification
                full_groups = defaultdict(list)
                for file_info in matching_files:
                    full_hash = self.full_hash_mmap(file_info.path)
                    full_groups[full_hash].append(file_info)
                
                for full_hash, identical_files in full_groups.items():
                    if len(identical_files) > 1:
                        original = identical_files[0]
                        duplicates = identical_files[1:]
                        duplicate_groups.append((original, duplicates))
        
        return duplicate_groups

    def find_duplicates(self) -> List[Tuple[FileInfo, List[FileInfo]]]:
        """Ultra-fast duplicate detection pipeline"""
        print("🚀 Ultra-fast scanning...")
        start_time = time.time()
        
        files = self.ultra_fast_scan()
        scan_time = time.time() - start_time
        print(f"📁 Scanned {len(files)} files in {scan_time:.2f}s")
        
        if not files:
            return []
        
        # Remove hard links
        start_time = time.time()
        files = self.detect_hardlinks(files)
        hardlink_time = time.time() - start_time
        print(f"🔗 Filtered hard links in {hardlink_time:.2f}s, {len(files)} unique files remain")
        
        # Smart grouping
        start_time = time.time()
        grouped_files = self.smart_grouping(files)
        group_time = time.time() - start_time
        print(f"📊 Grouped files in {group_time:.2f}s")
        
        if not grouped_files:
            return []
        
        # Batch processing
        start_time = time.time()
        duplicates = self.batch_process_groups(grouped_files)
        process_time = time.time() - start_time
        print(f"⚡ Processed duplicates in {process_time:.2f}s")
        
        return duplicates

    def clean_duplicates(self) -> None:
        """Main entry point with timing"""
        total_start = time.time()
        
        duplicate_groups = self.find_duplicates()
        
        if not duplicate_groups:
            print("✅ No duplicates found!")
            return

        print(f"\n🎯 Found {len(duplicate_groups)} groups of duplicates:")
        
        for original, duplicates in duplicate_groups:
            print(f"\n📄 Original: {original.path}")
            print("🗑️  Duplicates to remove:")
            total_size = 0
            
            for dup in duplicates:
                print(f"   - {dup.path} ({dup.size:,} bytes)")
                total_size += dup.size
            
            if not self.dry_run:
                for dup in duplicates:
                    try:
                        dup.path.unlink()
                        self.space_saved += dup.size
                        self.files_deleted += 1
                    except Exception as e:
                        print(f"❌ Error deleting {dup.path}: {e}")
            else:
                self.space_saved += total_size
            
            self.duplicates_found += len(duplicates)

        # Summary
        total_time = time.time() - total_start
        action = "Would delete" if self.dry_run else "Deleted"
        print(f"\n📈 Summary:")
        print(f"   {action} {self.duplicates_found} duplicate files")
        print(f"   💾 Space saved: {self.space_saved:,} bytes ({self.space_saved / 1024 / 1024:.2f} MB)")
        print(f"   ⏱️  Total time: {total_time:.2f} seconds")
        
        if self.duplicates_found > 0:
            print(f"   🚀 Speed: {self.duplicates_found / total_time:.1f} duplicates/second")

def main():
    parser = argparse.ArgumentParser(description='Ultra-fast duplicate file cleaner')
    parser.add_argument('directory', type=Path, help='Directory to scan for duplicates')
    parser.add_argument('--delete', action='store_true', help='Actually delete files (default is dry run)')
    parser.add_argument('--workers', type=int, default=None, help='Number of parallel workers')
    parser.add_argument('--min-size', type=int, default=512, help='Minimum file size to consider (bytes)')
    parser.add_argument('--no-mmap', action='store_true', help='Disable memory mapping')
    
    args = parser.parse_args()
    
    if not args.directory.exists():
        print("❌ Directory does not exist!")
        return
    
    cleaner = UltraFastDuplicateCleaner(
        args.directory, 
        dry_run=not args.delete,
        max_workers=args.workers
    )
    cleaner.min_file_size = args.min_size
    cleaner.use_mmap = not args.no_mmap
    
    print(f"🎯 Ultra-fast duplicate cleaner starting...")
    print(f"📁 Directory: {args.directory}")
    print(f"👥 Workers: {cleaner.max_workers}")
    print(f"💾 Min file size: {cleaner.min_file_size} bytes")
    print(f"🗺️  Memory mapping: {'enabled' if cleaner.use_mmap else 'disabled'}")
    if FAST_HASH:
        print("⚡ Using xxHash for ultra-fast hashing")
    print()
    
    cleaner.clean_duplicates()

if __name__ == "__main__":
    main()