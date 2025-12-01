#!/bin/bash
# Crop sprites to power-of-2 with transparent padding
# Usage: ./crop_sprites.sh <input_dir>

set -e

INPUT_DIR="${1:-.}"
PADDING=4

# Check for ImageMagick
if ! command -v magick &> /dev/null; then
    echo "ERROR: ImageMagick not found in PATH"
    echo ""
    echo "Install ImageMagick:"
    echo "  macOS (Homebrew): brew install imagemagick"
    echo "  Ubuntu/Debian: sudo apt-get install imagemagick"
    echo "  Windows: Download from https://imagemagick.org/script/download.php"
    echo ""
    exit 1
fi

if ! command -v identify &> /dev/null; then
    echo "ERROR: ImageMagick 'identify' command not found"
    echo "Please ensure ImageMagick is properly installed"
    exit 1
fi

echo "✓ ImageMagick found: $(magick --version | head -1)"
echo ""

# Function to get next power of 2
next_power_of_2() {
    local n=$1
    local p=1
    while [ $p -lt $n ]; do
        p=$((p * 2))
    done
    echo $p
}

echo "Cropping sprites in: $INPUT_DIR (recursive)"
echo "Padding: ${PADDING}px"
echo ""

# Count total PNG files
TOTAL_FILES=$(find "$INPUT_DIR" -type f -name "*.png" ! -name "*_cropped.png" | wc -l | tr -d ' ')
echo "Found $TOTAL_FILES PNG files to process"
echo ""

PROCESSED=0

# Process all PNG files recursively
find "$INPUT_DIR" -type f -name "*.png" | while read -r file; do
    filename=$(basename "$file")

    # Skip already cropped files
    if [[ "$filename" == *"_cropped.png" ]]; then
        continue
    fi

    PROCESSED=$((PROCESSED + 1))
    echo "[$PROCESSED/$TOTAL_FILES] Processing: $filename"

    # Get original dimensions
    original_dims=$(identify -format "%wx%h" "$file")
    echo "  Original: $original_dims"

    # Create temp file for trimmed version
    temp_trimmed="${file%.png}_temp_trim.png"

    # Step 1: Trim to content
    magick "$file" -trim "$temp_trimmed"

    # Get trimmed dimensions
    trimmed_dims=$(identify -format "%w %h" "$temp_trimmed")
    trim_w=$(echo $trimmed_dims | cut -d' ' -f1)
    trim_h=$(echo $trimmed_dims | cut -d' ' -f2)
    echo "  Trimmed: ${trim_w}×${trim_h}"

    # Calculate dimensions with padding
    padded_w=$((trim_w + PADDING * 2))
    padded_h=$((trim_h + PADDING * 2))

    # Calculate next power of 2
    pow2_w=$(next_power_of_2 $padded_w)
    pow2_h=$(next_power_of_2 $padded_h)
    echo "  Power-of-2: ${pow2_w}×${pow2_h}"

    # Step 2: Add padding and expand to power-of-2
    magick "$temp_trimmed" \
        -bordercolor transparent -border $PADDING \
        -gravity center \
        -background transparent \
        -extent "${pow2_w}x${pow2_h}" \
        "$file"

    # Clean up temp file
    rm "$temp_trimmed"

    # Get final size
    final_size=$(ls -lh "$file" | awk '{print $5}')
    echo "  Final size: $final_size"
    echo ""
done

echo ""
echo "==========================================="
echo "Crop processing complete!"
echo "==========================================="
echo "Processed $TOTAL_FILES PNG files"
echo "Output: $INPUT_DIR (in-place cropping)"
echo ""
