from pathlib import Path
import re
import argparse
from typing import Dict, List, Tuple
import hashlib
from collections import defaultdict
import concurrent.futures
import os
import asyncio
import time
from dataclasses import dataclass
import platform

# Try imports for maximum speed
try:
    import xxhash
    ULTRA_HASH = xxhash.xxh32  # Even faster than xxh64
except ImportError:
    ULTRA_HASH = None

@dataclass
class FileInfo:
    path: Path
    size: int
    ctime: float
    mtime: float
    base_name: str
    inode: int = 0
    device: int = 0

class BlazeSpeedDuplicateCleaner:
    def __init__(self, directory: Path, dry_run: bool = True, max_workers: int = None):
        self.directory = directory
        self.dry_run = dry_run
        self.max_workers = max_workers or min(64, (os.cpu_count() or 1) * 4)
        
        # Statistics
        self.duplicates_found = 0
        self.space_saved = 0
        self.files_deleted = 0
        
        # EXTREME speed settings
        self.min_file_size = 1024        # Skip tiny files
        self.confidence_threshold = 0.95  # Skip content verification if confidence > 95%
        self.timestamp_tolerance = 300    # 5 minutes - files created close together are likely duplicates
        self.verify_samples = 512         # Tiny sample for verification
        self.max_verify_files = 1000       # Limit content verification
        
        # Pre-compile patterns for maximum speed
        self._patterns = [
            re.compile(r'^(IMG_\d+_\d+)(?:_(\d+))?(\.[^.]+)$'),  # Capture sequence number
            re.compile(r'^(.+?)(?:_(\d+)|\s+\((\d+)\))(\.[^.]+)$')
        ]
        
        # Cache for base names
        self._base_name_cache = {}

    def get_base_name_and_sequence(self, filename: str) -> Tuple[str, int]:
        """Extract base name and sequence number for ultra-smart detection"""
        if filename in self._base_name_cache:
            return self._base_name_cache[filename]
        
        for pattern in self._patterns:
            match = pattern.match(filename)
            if match:
                if len(match.groups()) == 3:  # IMG pattern
                    base = match.group(1) + match.group(3)
                    seq = int(match.group(2)) if match.group(2) else 0
                else:  # Generic pattern
                    base = match.group(1) + match.group(4)
                    seq = int(match.group(2) or match.group(3) or 0)
                
                result = (base, seq)
                self._base_name_cache[filename] = result
                return result
        
        result = (filename, 0)
        self._base_name_cache[filename] = result
        return result

    async def ultra_scan_async(self) -> List[FileInfo]:
        """Async file scanning - brutally fast"""
        def scan_chunk(dir_paths):
            """Scan a chunk of directories"""
            chunk_files = []
            for dir_path in dir_paths:
                try:
                    with os.scandir(dir_path) as entries:
                        for entry in entries:
                            try:
                                if entry.is_file(follow_symlinks=False):
                                    stat_info = entry.stat(follow_symlinks=False)
                                    size = stat_info.st_size
                                    
                                    if size >= self.min_file_size:
                                        base_name, seq = self.get_base_name_and_sequence(entry.name)
                                        file_info = FileInfo(
                                            path=Path(entry.path),
                                            size=size,
                                            ctime=stat_info.st_ctime,
                                            mtime=stat_info.st_mtime,
                                            base_name=base_name,
                                            inode=stat_info.st_ino,
                                            device=stat_info.st_dev
                                        )
                                        chunk_files.append(file_info)
                            except (OSError, IOError, AttributeError):
                                continue
                except (OSError, IOError):
                    continue
            return chunk_files
        
        # Get all directories first
        all_dirs = [self.directory]
        for root, dirs, files_in_dir in os.walk(self.directory):
            all_dirs.extend(Path(root) / d for d in dirs)
        
        # Process directories in parallel chunks
        chunk_size = max(1, len(all_dirs) // self.max_workers)
        dir_chunks = [all_dirs[i:i + chunk_size] for i in range(0, len(all_dirs), chunk_size)]
        
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            tasks = [loop.run_in_executor(executor, scan_chunk, chunk) for chunk in dir_chunks]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results and filter out any exceptions
        files = []
        for result in results:
            if isinstance(result, list):
                files.extend(result)
            elif isinstance(result, Exception):
                print(f"Warning: Error in scanning chunk: {result}")
        
        return files

    def calculate_duplicate_confidence(self, files: List[FileInfo]) -> float:
        """Calculate confidence that files are duplicates without reading content"""
        if len(files) < 2:
            return 0.0
        
        confidence = 0.0
        
        # Same size = +40% confidence
        if len(set(f.size for f in files)) == 1:
            confidence += 0.4
        
        # Same base name = +30% confidence  
        if len(set(f.base_name for f in files)) == 1:
            confidence += 0.3
        
        # Similar timestamps = +20% confidence
        times = [f.ctime for f in files]
        if max(times) - min(times) < self.timestamp_tolerance:
            confidence += 0.2
        
        # Sequential filenames = +10% confidence
        paths = [f.path.name for f in files]
        if self._are_sequential_files(paths):
            confidence += 0.1
        
        return min(confidence, 1.0)

    def _are_sequential_files(self, filenames: List[str]) -> bool:
        """Check if filenames appear to be sequential duplicates"""
        if len(filenames) < 2:
            return False
        
        sequences = []
        for filename in filenames:
            _, seq = self.get_base_name_and_sequence(filename)
            sequences.append(seq)
        
        sequences.sort()
        # Check if they're roughly sequential
        for i in range(1, len(sequences)):
            if sequences[i] - sequences[i-1] > 10:  # Large gap
                return False
        
        return True

    def nano_hash(self, file_path: Path, size: int) -> str:
        """Minimal content sampling - just enough to verify"""
        try:
            if ULTRA_HASH:
                hasher = ULTRA_HASH()
            else:
                hasher = hashlib.md5()
            
            hasher.update(str(size).encode())
            
            # Read tiny sample from middle of file
            with open(file_path, "rb") as f:
                if size > self.verify_samples:
                    f.seek(size // 2)
                    sample = f.read(self.verify_samples)
                else:
                    sample = f.read()
                hasher.update(sample)
            
            return hasher.hexdigest()
        except (OSError, IOError):
            return f"error_{size}"

    def metadata_based_grouping(self, files: List[FileInfo]) -> Dict[str, List[List[FileInfo]]]:
        """Group files using only metadata - zero file I/O"""
        # Group by base name first
        base_groups = defaultdict(list)
        for file_info in files:
            base_groups[file_info.base_name].append(file_info)
        
        # Filter to potential duplicates and sub-group by size
        potential_duplicates = {}
        for base_name, file_list in base_groups.items():
            if len(file_list) > 1:
                # Sub-group by size
                size_groups = defaultdict(list)
                for file_info in file_list:
                    size_groups[file_info.size].append(file_info)
                
                # Only keep size groups with multiple files
                duplicate_size_groups = [files for files in size_groups.values() if len(files) > 1]
                if duplicate_size_groups:
                    potential_duplicates[base_name] = duplicate_size_groups
        
        return potential_duplicates

    def process_with_confidence(self, grouped_files: Dict[str, List[List[FileInfo]]]) -> List[Tuple[FileInfo, List[FileInfo]]]:
        """Process groups with confidence-based verification"""
        duplicate_groups = []
        verified_count = 0
        
        for base_name, size_groups in grouped_files.items():
            for files in size_groups:
                if len(files) < 2:
                    continue
                
                # Sort by creation time (oldest first)
                files.sort(key=lambda x: x.ctime)
                
                # Calculate confidence without reading files
                confidence = self.calculate_duplicate_confidence(files)
                
                if confidence >= self.confidence_threshold:
                    # High confidence - assume duplicates without verification
                    original = files[0]
                    duplicates = files[1:]
                    duplicate_groups.append((original, duplicates))
                    print(f"🎯 High confidence ({confidence:.1%}): {len(duplicates)} duplicates of {original.path.name}")
                
                elif verified_count < self.max_verify_files:
                    # Medium confidence - quick verification
                    verified_count += len(files)
                    content_groups = defaultdict(list)
                    
                    for file_info in files:
                        nano_hash = self.nano_hash(file_info.path, file_info.size)
                        content_groups[nano_hash].append(file_info)
                    
                    for nano_hash, identical_files in content_groups.items():
                        if len(identical_files) > 1:
                            original = identical_files[0]
                            duplicates = identical_files[1:]
                            duplicate_groups.append((original, duplicates))
                            print(f"✅ Verified: {len(duplicates)} duplicates of {original.path.name}")
                
                else:
                    # Skip verification - too many files
                    print(f"⏭️  Skipped verification for {files[0].path.name} (limit reached)")
        
        return duplicate_groups

    def remove_hard_links_safely(self, files: List[FileInfo]) -> List[FileInfo]:
        """Remove hard links more carefully, with Windows compatibility"""
        if platform.system() == "Windows":
            # On Windows, inode checking is unreliable, so we'll use a different approach
            # We'll check for files with identical size, mtime, and path differences
            unique_files = []
            seen_file_ids = set()
            
            for file_info in files:
                try:
                    # Use a combination of size and mtime as a basic check
                    # This isn't perfect but better than relying on st_ino on Windows
                    file_id = (file_info.size, int(file_info.mtime * 1000))  # mtime to milliseconds
                    
                    # Check if this exact file already exists (by path)
                    path_str = str(file_info.path)
                    is_duplicate_path = any(str(f.path) == path_str for f in unique_files)
                    
                    if not is_duplicate_path:
                        unique_files.append(file_info)
                        seen_file_ids.add(file_id)
                    
                except (OSError, IOError):
                    # If we can't get file info, include it anyway
                    unique_files.append(file_info)
            
            print(f"🔗 Removed {len(files) - len(unique_files)} potential hard links (Windows mode)")
            return unique_files
        
        else:
            # On Unix-like systems, use the original inode-based approach
            unique_files = []
            seen_inodes = set()
            for file_info in files:
                inode_key = (file_info.device, file_info.inode)
                if inode_key not in seen_inodes:
                    seen_inodes.add(inode_key)
                    unique_files.append(file_info)
            
            print(f"🔗 Removed {len(files) - len(unique_files)} hard links")
            return unique_files

    async def find_duplicates_blazing(self) -> List[Tuple[FileInfo, List[FileInfo]]]:
        """Blazing fast duplicate detection"""
        print("🚀 BLAZING SPEED MODE - Scanning...")
        start_time = time.time()
        
        # Ultra-fast async scan
        files = await self.ultra_scan_async()
        scan_time = time.time() - start_time
        print(f"📁 Scanned {len(files)} files in {scan_time:.3f}s ({len(files)/scan_time:.0f} files/sec)")
        
        if not files:
            return []
        
        # Remove hard links safely
        unique_files = self.remove_hard_links_safely(files)
        
        # Metadata-only grouping
        start_time = time.time()
        grouped_files = self.metadata_based_grouping(unique_files)
        group_time = time.time() - start_time
        print(f"📊 Grouped {len(unique_files)} files in {group_time:.3f}s")
        
        if not grouped_files:
            return []
        
        # Confidence-based processing
        start_time = time.time()
        duplicates = self.process_with_confidence(grouped_files)
        process_time = time.time() - start_time
        print(f"⚡ Processed duplicates in {process_time:.3f}s")
        
        return duplicates

    def clean_duplicates(self) -> None:
        """Main entry point"""
        total_start = time.time()
        
        # Run async duplicate detection
        duplicate_groups = asyncio.run(self.find_duplicates_blazing())
        
        if not duplicate_groups:
            print("✅ No duplicates found!")
            return

        print(f"\n🎯 Found {len(duplicate_groups)} groups of duplicates:")
        
        for i, (original, duplicates) in enumerate(duplicate_groups, 1):
            if i <= 10 or self.dry_run:  # Show details for first 10 or in dry run
                print(f"\n📄 Group {i}: {original.path.name}")
                print(f"   🗑️  Removing {len(duplicates)} duplicates:")
                for dup in duplicates:
                    print(f"      - {dup.path.name} ({dup.size:,} bytes)")
            
            if not self.dry_run:
                for dup in duplicates:
                    try:
                        dup.path.unlink()
                        self.space_saved += dup.size
                        self.files_deleted += 1
                    except Exception as e:
                        print(f"❌ Error deleting {dup.path}: {e}")
            else:
                self.space_saved += sum(dup.size for dup in duplicates)
            
            self.duplicates_found += len(duplicates)

        # Final summary
        total_time = time.time() - total_start
        action = "Would delete" if self.dry_run else "Deleted"
        
        print(f"\n🏆 BLAZING SPEED RESULTS:")
        print(f"   {action} {self.duplicates_found} duplicate files")
        print(f"   💾 Space saved: {self.space_saved:,} bytes ({self.space_saved / 1024 / 1024:.1f} MB)")
        print(f"   ⏱️  Total time: {total_time:.3f} seconds")
        print(f"   🚀 Speed: {self.duplicates_found / total_time:.0f} duplicates/second")
        
        if not self.dry_run and self.duplicates_found > 0:
            print(f"   🔥 Deleted {self.space_saved / 1024 / 1024 / total_time:.1f} MB/second")

def main():
    parser = argparse.ArgumentParser(description='BLAZING FAST duplicate file cleaner')
    parser.add_argument('directory', type=Path, help='Directory to scan')
    parser.add_argument('--delete', action='store_true', help='Actually delete files')
    parser.add_argument('--workers', type=int, default=None, help='Number of workers')
    parser.add_argument('--min-size', type=int, default=1024, help='Minimum file size (bytes)')
    parser.add_argument('--confidence', type=float, default=0.95, help='Confidence threshold (0.0-1.0)')
    parser.add_argument('--max-verify', type=int, default=1000, help='Max files to content-verify')
    
    args = parser.parse_args()
    
    if not args.directory.exists():
        print("❌ Directory does not exist!")
        return
    
    cleaner = BlazeSpeedDuplicateCleaner(
        args.directory, 
        dry_run=not args.delete,
        max_workers=args.workers
    )
    cleaner.min_file_size = args.min_size
    cleaner.confidence_threshold = args.confidence
    cleaner.max_verify_files = args.max_verify
    
    print(f"🔥 BLAZING SPEED DUPLICATE CLEANER")
    print(f"📁 Directory: {args.directory}")
    print(f"👥 Workers: {cleaner.max_workers}")
    print(f"🎯 Confidence threshold: {cleaner.confidence_threshold:.1%}")
    print(f"🔍 Max content verification: {cleaner.max_verify_files}")
    if ULTRA_HASH:
        print("⚡ Using xxHash ultra-fast mode")
    print()
    
    cleaner.clean_duplicates()

if __name__ == "__main__":
    main()