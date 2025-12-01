# Blender Sprite Render

Automated tool to convert 3D models into 2D sprites with consistent lighting, framing, and optional multi-directional rendering. Perfect for creating sprite assets for 2D games from 3D models.

## Features

- **Batch Processing**: Process entire directories of 3D models automatically
- **Multi-Format Support**: Handles `.gltf`, `.glb`, `.obj`, `.fbx`
- **Fixed Scale Rendering**: Consistent world-to-pixel ratio across all assets
- **Asset Scaling**: Import-time scaling to normalize asset sizes
- **4-Directional Sprites**: Optional N/S/E/W rendering via camera rotation
- **Configurable Camera**: Angle, yaw, orthographic scale
- **Transparent Output**: PNG with alpha channel (32-bit RGBA)
- **Automatic Cropping**: Power-of-2 dimensions with padding (GPU-friendly)
- **Metadata Export**: JSON sidecar files with sprite dimensions
- **Headless Operation**: Runs without Blender GUI

## Prerequisites

1. **Blender 3.0+**
   - Download: https://www.blender.org/download/
   - Verify: `blender --version`

2. **ImageMagick** (for auto-crop)
   - macOS: `brew install imagemagick`
   - Ubuntu/Debian: `sudo apt-get install imagemagick`
   - Windows: https://imagemagick.org/script/download.php
   - Verify: `magick --version`

3. **Python 3.7+** (bundled with Blender)

## Quick Start

### Method 1: Direct Python Usage

```bash
# Render all models in a directory
blender --background --python blender_batch_render.py -- \
    --input ./my-3d-models \
    --output ./sprites \
    --rotations 4

# With custom settings
blender --background --python blender_batch_render.py -- \
    --input ./my-3d-models \
    --output ./sprites \
    --angle 60 \
    --scale-factor 0.5 \
    --samples 64 \
    --rotations 4
```

### Method 2: Using Config Files

```bash
# Create a config for your asset pack
cp configs/example.conf configs/my-assets.conf

# Edit the config
nano configs/my-assets.conf

# Run batch render
./batch_render.sh configs/my-assets.conf
```

### Method 3: JSON Config

```bash
# Copy and edit example config
cp render_config.example.json render_config.json
nano render_config.json

# Run with config
blender --background --python blender_batch_render.py -- \
    --config render_config.json
```

## Configuration Options

### Command-Line Arguments

| Argument | Short | Default | Description |
|----------|-------|---------|-------------|
| `--input` | `-i` | *required* | Input directory with 3D models |
| `--output` | `-o` | `./rendered_sprites` | Output directory for PNG sprites |
| `--angle` | `-a` | `60.0` | Camera pitch angle (55-90 degrees) |
| `--camera-yaw` | | `0.0` | Camera compass direction (0=north) |
| `--ortho-scale` | | `4.0` | Orthographic scale in Blender units |
| `--pixels-per-unit` | | `256.0` | Pixels per Blender unit |
| `--samples` | `-s` | `64` | Anti-aliasing samples |
| `--rotations` | | `1` | Rotations: 1 (single) or 4 (N/S/E/W) |
| `--scale-factor` | | `1.0` | Import scaling factor |
| `--light-strength` | | `3.0` | Directional light intensity |
| `--skip-existing` | | `false` | Skip already rendered files |
| `--verbose` | `-v` | `false` | Enable debug logging |
| `--log-file` | | `none` | Write log to file |
| `--config` | `-c` | `none` | Load settings from JSON file |

### Config File Formats

**Shell config (.conf):**
```bash
# configs/my-assets.conf
ASSET_PACK_NAME="My Asset Pack"
INPUT_DIR="./models"
OUTPUT_DIR="./sprites"
CAMERA_ANGLE=60
ORTHO_SCALE=4.0
PIXELS_PER_UNIT=256
SCALE_FACTOR=1.0
SAMPLES=64
ROTATIONS=4
```

**JSON config:**
```json
{
  "input_dir": "./models",
  "output_dir": "./sprites",
  "camera_angle": 60.0,
  "ortho_scale": 4.0,
  "pixels_per_unit": 256.0,
  "samples": 64,
  "rotations": 4,
  "scale_factor": 1.0,
  "auto_crop": true
}
```

## Understanding the Settings

### Camera Angle (55-90 degrees)

- **55-60**: Classic angled view, good depth perception (recommended)
- **65-75**: More overhead, better spatial awareness
- **80-85**: Nearly top-down
- **90**: Pure top-down, flat view

### Scale Factor

Different asset packs use different scales. Use `inspect_model_sizes.py` to analyze your models:

```bash
blender --background --python inspect_model_sizes.py -- ./models/*.gltf
```

Common scale factors:
- `1.0` - Standard metric scaling (1 BU = 1 meter)
- `0.5` - For oversized models (e.g., some KayKit assets)
- `2.0` - For undersized models

### 4-Directional Rendering

When `--rotations 4` is enabled, the camera orbits around each model to capture:
- **South (_s)**: Front view (default)
- **East (_e)**: Right side
- **North (_n)**: Back view
- **West (_w)**: Left side

This shows genuine different sides of asymmetric objects.

### Resolution & Canvas Size

Canvas size = `ortho_scale × pixels_per_unit`

Default: 4.0 × 256 = 1024×1024 pixels

After auto-crop, sprites are trimmed to content with power-of-2 dimensions (GPU-friendly).

## Output Structure

```
sprites/
  ├── barrel.png          # Single rotation
  ├── barrel.json         # Metadata
  ├── chest_s.png         # 4-directional: south
  ├── chest_e.png         # 4-directional: east
  ├── chest_n.png         # 4-directional: north
  ├── chest_w.png         # 4-directional: west
  └── chest_s.json        # Metadata for each
```

## Utilities

### Auto-Crop Sprites

Crop transparent pixels and resize to power-of-2 dimensions:

```bash
./crop_sprites.sh ./sprites
```

### Inspect Model Sizes

Analyze 3D model dimensions to determine scale factor:

```bash
blender --background --python inspect_model_sizes.py -- ./models/*.gltf
```

## Compatible Asset Packs

This tool works with any 3D models in supported formats. Here are some excellent free CC0 asset sources:

| Source | License | Notes |
|--------|---------|-------|
| [Kenney](https://kenney.nl/) | CC0 | Huge variety, consistent style |
| [Quaternius](https://quaternius.com/) | CC0 | Low-poly, fantasy/medieval |
| [KayKit](https://kaylousberg.itch.io/) | CC0 | Stylized dungeon/adventure |

### Example: Kenney Graveyard Kit

```bash
# Download from kenney.nl and extract
# Models are in Models/GLTF format

# Create config
cat > configs/kenney-graveyard.conf << 'EOF'
ASSET_PACK_NAME="Kenney Graveyard Kit"
INPUT_DIR="./kenney_graveyard-kit/Models/GLTF format"
OUTPUT_DIR="./graveyard-sprites"
CAMERA_ANGLE=60
ORTHO_SCALE=4.0
PIXELS_PER_UNIT=256
SCALE_FACTOR=1.0
SAMPLES=64
ROTATIONS=4
EOF

# Render
./batch_render.sh configs/kenney-graveyard.conf
```

### Scale Factor by Asset Pack

Different packs use different scales. Common settings:

| Asset Pack | Scale Factor | Notes |
|------------|--------------|-------|
| Kenney | 1.0 | Standard metric scale |
| Quaternius | 1.0 | Standard metric scale |
| KayKit | 0.5 | Models are 2x larger |

Use `inspect_model_sizes.py` to determine the right scale for your models.

## Performance

Estimated render times (per sprite at 1024×1024, 64 samples):
- Simple objects: 3-7 seconds
- Medium objects: 7-15 seconds
- Complex objects: 15-30 seconds

**Tips:**
- Use `--samples 16` for quick drafts
- Use `--skip-existing` to resume interrupted batches
- Run large batches overnight

## Troubleshooting

### "No models found"
- Check input path exists: `ls ./your-input-path`
- Verify file extensions: `.gltf`, `.glb`, `.obj`, `.fbx`

### "Failed to import"
- Ensure `.bin` files exist alongside `.gltf` files
- Try opening the model in Blender GUI to diagnose

### Blender not found
```bash
# macOS: Add to PATH or use full path
/Applications/Blender.app/Contents/MacOS/Blender --background --python ...

# Or add to ~/.zshrc:
export PATH="/Applications/Blender.app/Contents/MacOS:$PATH"
```

### Sprites too small/large
- Adjust `--ortho-scale` (smaller = tighter framing)
- Check `--scale-factor` matches your asset pack

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT License - see [LICENSE](LICENSE) for details.

## Credits

Inspired by the needs of 2D game developers working with 3D asset packs.

Example assets: [Kenney](https://kenney.nl/) (CC0), [Quaternius](https://quaternius.com/) (CC0)
