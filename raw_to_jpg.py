import os
import rawpy
import imageio
import argparse
from pathlib import Path

def convert_raw_to_jpg(input_dir, output_dir, quality=95):
    """
    Convert RAW images to JPG format with high quality settings.
    
    Args:
        input_dir (str): Directory containing RAW images
        output_dir (str): Directory where JPG copies will be saved
        quality (int): JPG quality (1-100, default 95)
    """
    # List of common RAW file extensions
    raw_extensions = {'.cr2', '.nef', '.arw', '.orf', '.rw2', '.raf', '.dng'}
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all files in input directory
    input_path = Path(input_dir)
    files = list(input_path.rglob('*'))
    
    converted_count = 0
    error_count = 0
    
    # Process each file
    for file_path in files:
        if file_path.suffix.lower() in raw_extensions:
            try:
                # Create output filename
                relative_path = file_path.relative_to(input_path)
                output_path = Path(output_dir) / relative_path.with_suffix('.jpg')
                
                # Create necessary subdirectories
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                print(f"Converting: {file_path}")
                
                # Read and convert RAW file with high-quality settings
                with rawpy.imread(str(file_path)) as raw:
                    rgb = raw.postprocess(
                        use_camera_wb=True,
                        demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD,
                        output_bps=16,
                        no_auto_bright=True,
                        output_color=rawpy.ColorSpace.sRGB,
                        bright=1.0,
                        user_flip=0,
                    )
                
                # Convert to 8-bit color depth for JPG compatibility
                rgb_8bit = (rgb / 256).astype('uint8')
                
                # Save as high-quality JPG
                imageio.imsave(
                    str(output_path), 
                    rgb_8bit,
                    quality=quality,
                    optimize=True,
                    subsampling='4:4:4'
                )
                
                print(f"Saved: {output_path}")
                converted_count += 1
                
            except Exception as e:
                print(f"Error processing {file_path}: {str(e)}")
                error_count += 1
    
    return converted_count, error_count

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Convert RAW photo files to high-quality JPG format'
    )
    
    # Get current working directory for default paths
    cwd = os.getcwd()
    
    # Add arguments with defaults
    parser.add_argument(
        '-i', '--input',
        default=os.path.join(cwd, 'raw'),
        help='Input directory containing RAW files (default: ./raw)'
    )
    parser.add_argument(
        '-o', '--output',
        default=os.path.join(cwd, 'jpg'),
        help='Output directory for JPG files (default: ./jpg)'
    )
    parser.add_argument(
        '-q', '--quality',
        type=int,
        choices=range(1, 101),
        default=95,
        help='JPG quality (1-100, default: 95)'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Print configuration
    print(f"\nHigh-Quality RAW to JPG Converter")
    print(f"Input directory: {args.input}")
    print(f"Output directory: {args.output}")
    print(f"JPG quality: {args.quality}")
    print("-" * 50)
    
    # Run conversion
    converted, errors = convert_raw_to_jpg(args.input, args.output, args.quality)
    
    # Print summary
    print("\nConversion Summary")
    print("-" * 50)
    print(f"Successfully converted: {converted} files")
    print(f"Errors encountered: {errors} files")
    print(f"Total files processed: {converted + errors}")

if __name__ == "__main__":
    main()