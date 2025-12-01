#!/bin/bash
# Universal batch render script - works with config files for different asset packs
# Usage: ./batch_render.sh <config_file>
# Example: ./batch_render.sh configs/quaternius_fantasy.conf

set -e

# Check if config file provided
if [ $# -eq 0 ]; then
    echo "ERROR: No config file provided"
    echo ""
    echo "Usage: $0 <config_file>"
    echo ""
    echo "Available configs:"
    echo "  configs/kaykit.conf               - KayKit Dungeon Remastered (~420 models)"
    echo "  configs/quaternius_fantasy.conf   - Quaternius Fantasy Props (~200 models)"
    echo "  configs/quaternius_village.conf   - Quaternius Medieval Village (~200 models)"
    echo ""
    exit 1
fi

CONFIG_FILE="$1"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Config file not found: $CONFIG_FILE"
    exit 1
fi

# Set up paths BEFORE loading config (so config can use $PROJECT_DIR)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
export PROJECT_DIR

# Load configuration
source "$CONFIG_FILE"

# Validate required variables
REQUIRED_VARS=(
    "ASSET_PACK_NAME"
    "INPUT_DIR"
    "OUTPUT_DIR"
    "SCALE_FACTOR"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "ERROR: Required variable '$var' not set in config file"
        exit 1
    fi
done

# Set defaults for optional variables
CAMERA_ANGLE="${CAMERA_ANGLE:-60}"
ORTHO_SCALE="${ORTHO_SCALE:-4.0}"
PIXELS_PER_UNIT="${PIXELS_PER_UNIT:-256}"
SAMPLES="${SAMPLES:-64}"
ROTATIONS="${ROTATIONS:-4}"
LIGHT_STRENGTH="${LIGHT_STRENGTH:-3.0}"

# Expand variables in paths (support $PROJECT_DIR in config)
INPUT_DIR=$(eval echo "$INPUT_DIR")
OUTPUT_DIR=$(eval echo "$OUTPUT_DIR")
LOG_FILE="$OUTPUT_DIR/batch_render.log"

echo "==========================================="
echo "$ASSET_PACK_NAME - Full Batch Render"
echo "==========================================="
echo ""

# Check Blender
if ! command -v blender &> /dev/null; then
    echo "ERROR: Blender not found in PATH"
    echo "macOS: Use /Applications/Blender.app/Contents/MacOS/Blender"
    exit 1
fi

# Check input directory
if [ ! -d "$INPUT_DIR" ]; then
    echo "ERROR: Asset directory not found at:"
    echo "  $INPUT_DIR"
    exit 1
fi

# Count models
MODEL_COUNT=$(find "$INPUT_DIR" -name "*.gltf" | wc -l | tr -d ' ')

echo "Configuration:"
echo "  Config: $CONFIG_FILE"
echo "  Input: $INPUT_DIR"
echo "  Output: $OUTPUT_DIR"
echo "  Models: ~$MODEL_COUNT"
echo "  Camera angle: ${CAMERA_ANGLE}° (angled top-down)"
echo "  Ortho scale: ${ORTHO_SCALE} BU (fixed scale)"
echo "  Pixels per unit: ${PIXELS_PER_UNIT}"
echo "  Scale factor: ${SCALE_FACTOR}×"
echo "  Samples: $SAMPLES"
echo "  Rotations: $ROTATIONS (N/S/E/W)"
echo "  Light strength: ${LIGHT_STRENGTH}"
echo "  Canvas size: $((${ORTHO_SCALE%.*} * ${PIXELS_PER_UNIT%.*}))px (before crop)"
echo "  Log: $LOG_FILE"
echo ""
echo "Estimated time: 1-3 hours (~$MODEL_COUNT models × $ROTATIONS rotations)"
echo ""

# Confirmation
read -p "Start batch render? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Record start time
START_TIME=$(date +%s)
echo "Started at: $(date)" | tee "$LOG_FILE"
echo ""

# Run batch render
blender --background --python "$SCRIPT_DIR/blender_batch_render.py" -- \
    --input "$INPUT_DIR" \
    --output "$OUTPUT_DIR" \
    --angle "$CAMERA_ANGLE" \
    --ortho-scale "$ORTHO_SCALE" \
    --pixels-per-unit "$PIXELS_PER_UNIT" \
    --scale-factor "$SCALE_FACTOR" \
    --samples "$SAMPLES" \
    --rotations "$ROTATIONS" \
    --light-strength "$LIGHT_STRENGTH" \
    --log-file "$LOG_FILE"

# Calculate duration
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo ""
echo "==========================================="
echo "Running auto-crop on rendered sprites..."
echo "==========================================="
echo ""

# Run crop script to optimize sprite sizes
"$SCRIPT_DIR/crop_sprites.sh" "$OUTPUT_DIR"

CROP_END_TIME=$(date +%s)
CROP_DURATION=$((CROP_END_TIME - END_TIME))
CROP_MINUTES=$((CROP_DURATION / 60))
CROP_SECONDS=$((CROP_DURATION % 60))

echo ""
echo "==========================================="
echo "Batch render complete!"
echo "==========================================="
echo "Finished at: $(date)"
echo "Render duration: ${MINUTES}m ${SECONDS}s"
echo "Crop duration: ${CROP_MINUTES}m ${CROP_SECONDS}s"
echo "Total duration: $(((CROP_END_TIME - START_TIME) / 60))m $(((CROP_END_TIME - START_TIME) % 60))s"
echo "Output: $OUTPUT_DIR"
echo "Log: $LOG_FILE"
echo ""
echo "Sprites have been automatically cropped to power-of-2 dimensions."
echo ""
