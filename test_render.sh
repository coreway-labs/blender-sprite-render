#!/bin/bash
# Quick test render script
# Tests the renderer with a small subset of models before full batch
#
# Usage: ./test_render.sh <input_dir> [output_dir]
# Example: ./test_render.sh ./my-models ./test-output

set -e

echo "==================================="
echo "Blender Sprite Render - Test Script"
echo "==================================="
echo ""

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check arguments
if [ $# -eq 0 ]; then
    echo "Usage: $0 <input_dir> [output_dir]"
    echo ""
    echo "Example:"
    echo "  $0 ./kenney-dungeon/Models/GLTF ./test-sprites"
    echo ""
    echo "This will render a small test batch to verify your setup."
    exit 1
fi

INPUT_DIR="$1"
OUTPUT_DIR="${2:-./test_output}"

# Blender binary path
BLENDER_BIN="blender"
if ! command -v blender &> /dev/null; then
    # macOS default location
    if [ -f "/Applications/Blender.app/Contents/MacOS/Blender" ]; then
        BLENDER_BIN="/Applications/Blender.app/Contents/MacOS/Blender"
    else
        echo "ERROR: Blender not found in PATH or default location"
        echo ""
        echo "macOS: Add to PATH or use full path:"
        echo "  /Applications/Blender.app/Contents/MacOS/Blender"
        echo ""
        echo "Or add to ~/.zshrc:"
        echo '  export PATH="/Applications/Blender.app/Contents/MacOS:$PATH"'
        exit 1
    fi
fi

echo "Blender: $($BLENDER_BIN --version | head -1)"
echo ""

# Check input directory
if [ ! -d "$INPUT_DIR" ]; then
    echo "ERROR: Input directory not found: $INPUT_DIR"
    exit 1
fi

# Count models
MODEL_COUNT=$(find "$INPUT_DIR" -maxdepth 1 \( -name "*.gltf" -o -name "*.glb" -o -name "*.obj" -o -name "*.fbx" \) | wc -l | tr -d ' ')

if [ "$MODEL_COUNT" -eq 0 ]; then
    echo "ERROR: No 3D models found in $INPUT_DIR"
    echo "Supported formats: .gltf, .glb, .obj, .fbx"
    exit 1
fi

echo "Found $MODEL_COUNT models in: $INPUT_DIR"
echo "Output: $OUTPUT_DIR"
echo ""

# Limit to first 5 models for test
TEST_LIMIT=5
if [ "$MODEL_COUNT" -gt "$TEST_LIMIT" ]; then
    echo "Note: Testing with first $TEST_LIMIT models only"
    echo "      Full batch will process all $MODEL_COUNT models"
    echo ""
fi

# Create temp directory with subset
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Copy first N models to temp dir
count=0
for ext in gltf glb obj fbx; do
    for model in "$INPUT_DIR"/*."$ext"; do
        [ -f "$model" ] || continue
        cp "$model" "$TEMP_DIR/"
        # Also copy associated .bin files for .gltf
        if [ "$ext" = "gltf" ]; then
            bin_file="${model%.gltf}.bin"
            [ -f "$bin_file" ] && cp "$bin_file" "$TEMP_DIR/"
        fi
        count=$((count + 1))
        [ $count -ge $TEST_LIMIT ] && break 2
    done
done

echo "Test settings:"
echo "  Camera angle: 60 degrees (angled view)"
echo "  Ortho scale: 4.0 Blender units"
echo "  Scale factor: 1.0 (adjust based on your models)"
echo "  Samples: 32 (lower for quick test)"
echo "  Rotations: 4 (N/S/E/W)"
echo ""
echo "Starting test render..."
echo ""

"$BLENDER_BIN" --background --python "$SCRIPT_DIR/blender_batch_render.py" -- \
    --input "$TEMP_DIR" \
    --output "$OUTPUT_DIR" \
    --angle 60 \
    --ortho-scale 4.0 \
    --samples 32 \
    --pixels-per-unit 256 \
    --scale-factor 1.0 \
    --rotations 4 \
    --verbose

echo ""
echo "==================================="
echo "Test render complete!"
echo "==================================="
echo ""
echo "Output: $OUTPUT_DIR"
echo ""
echo "Check the output sprites:"
echo "  - Verify transparent backgrounds"
echo "  - Check sprite framing and scale"
echo "  - Adjust --scale-factor if models are too large/small"
echo ""
echo "If everything looks good, run full batch:"
echo "  ./batch_render.sh configs/your-config.conf"
echo ""
echo "Or directly:"
echo "  blender --background --python blender_batch_render.py -- \\"
echo "      --input $INPUT_DIR \\"
echo "      --output ./sprites \\"
echo "      --rotations 4"
echo ""
