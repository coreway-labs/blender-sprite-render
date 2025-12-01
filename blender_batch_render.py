#!/usr/bin/env python3
"""
Blender Batch 3D-to-2D Sprite Renderer

Converts 3D models to 2D sprites with consistent lighting and framing.
Supports batch processing, multi-directional rendering, and auto-cropping.

Usage:
    blender --background --python blender_batch_render.py -- \
        --input ./models \
        --output ./sprites \
        --scale-factor 1.0 \
        --samples 64 \
        --rotations 4

For full options: blender --background --python blender_batch_render.py -- --help

See README.md for detailed documentation.
"""

import bpy
import math
import os
import sys
import argparse
import json
from pathlib import Path
from typing import Tuple, Optional, List
import logging
from mathutils import Vector

# Optional PIL import for auto-crop feature
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("WARNING: PIL/Pillow not installed - auto-crop feature disabled")
    print("To enable: /Applications/Blender.app/Contents/Resources/4.5/python/bin/python3.11 -m pip install Pillow")


# ============================================================================
# Configuration
# ============================================================================

class RenderConfig:
    """Configuration for batch rendering"""

    def __init__(self):
        # Paths
        self.input_dir: str = ""
        self.output_dir: str = "./rendered_sprites"

        # Render settings
        self.resolution: int = 512  # Default, will be calculated per-object
        self.camera_angle: float = 55.0  # degrees from horizontal (55 = classic angled view, 90 = pure top-down)
        self.camera_yaw: float = 0.0  # degrees Z-rotation (0 = north-facing, 45 = isometric diamond)
        self.samples: int = 64  # anti-aliasing quality

        # Real-world scaling (FIXED SCALE APPROACH) - Render at 2× for quality
        self.ortho_scale: float = 4.0  # Ortho camera shows 4x4 Blender units (fits all assets)
        self.pixels_per_unit: float = 256.0  # 256 pixels per Blender unit (2× quality for 128px tiles)
        self.min_canvas_size: int = 256
        self.max_canvas_size: int = 1024  # Cap at 1024px for larger sprites

        # Rotations
        self.rotations: int = 1  # 1 or 4 (for N/S/E/W directional sprites)

        # Light settings
        self.light_strength: float = 3.0
        self.light_angle_x: float = 45.0
        self.light_angle_z: float = 315.0  # Southeast - illuminates south-facing surfaces (player view)

        # Processing
        self.formats: List[str] = ['.gltf', '.glb', '.obj', '.fbx']
        self.skip_existing: bool = False
        self.auto_crop: bool = PIL_AVAILABLE  # Trim transparent pixels (requires PIL/Pillow)
        self.scale_factor: float = 1.0  # Scale imported models (e.g., 0.5 to halve size)

        # Output
        self.verbose: bool = False
        self.log_file: Optional[str] = None


# ============================================================================
# Logging Setup
# ============================================================================

def setup_logging(config: RenderConfig) -> logging.Logger:
    """Configure logging for the script"""
    logger = logging.getLogger('blender_batch_render')
    logger.setLevel(logging.DEBUG if config.verbose else logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if config.verbose else logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if config.log_file:
        # Ensure log file directory exists
        log_dir = os.path.dirname(config.log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(config.log_file, mode='w')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


# ============================================================================
# Scene Setup
# ============================================================================

def clear_scene():
    """Remove all default objects from the scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Clear orphaned data
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)
    for block in bpy.data.textures:
        if block.users == 0:
            bpy.data.textures.remove(block)
    for block in bpy.data.images:
        if block.users == 0:
            bpy.data.images.remove(block)


def setup_camera(config: RenderConfig) -> bpy.types.Object:
    """Create and configure orthographic camera"""
    # Add camera
    bpy.ops.object.camera_add()
    camera = bpy.context.active_object
    camera.name = "OrthographicCamera"

    # Set rotation (position will be set per-object by calculate_canvas_and_position)
    angle_rad = math.radians(config.camera_angle)
    yaw_rad = math.radians(config.camera_yaw)
    camera.rotation_euler = (
        angle_rad,  # X: pitch angle (90° = top-down, lower = more angled)
        0.0,        # Y: no roll
        yaw_rad     # Z: yaw rotation (0° = north-facing, 45° = diamond view)
    )

    # Set as orthographic with FIXED scale (consistent for all assets)
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = config.ortho_scale

    # Set as active camera
    bpy.context.scene.camera = camera

    return camera


def setup_lighting(config: RenderConfig) -> bpy.types.Object:
    """Create directional sun light"""
    bpy.ops.object.light_add(type='SUN')
    light = bpy.context.active_object
    light.name = "DirectionalLight"

    # Rotation: 45° from top-left to bottom-right
    light.rotation_euler = (
        math.radians(config.light_angle_x),  # X: 45° down
        0.0,                                  # Y: no rotation
        math.radians(config.light_angle_z)   # Z: 135° (top-left)
    )

    # Intensity
    light.data.energy = config.light_strength

    return light


def setup_render_settings(config: RenderConfig):
    """Configure render engine and output settings"""
    scene = bpy.context.scene

    # Render engine: Eevee (fast)
    # Blender 4.0+ uses BLENDER_EEVEE_NEXT, older versions use BLENDER_EEVEE
    if 'BLENDER_EEVEE_NEXT' in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items.keys():
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    else:
        scene.render.engine = 'BLENDER_EEVEE'

    # Sampling (anti-aliasing)
    scene.eevee.taa_render_samples = config.samples

    # Output settings
    scene.render.resolution_x = config.resolution
    scene.render.resolution_y = config.resolution
    scene.render.resolution_percentage = 100

    # File format: PNG with alpha
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.render.image_settings.compression = 15

    # Transparency
    scene.render.film_transparent = True

    # Color management (keep colors accurate)
    scene.view_settings.view_transform = 'Standard'


# ============================================================================
# Object Import & Framing
# ============================================================================

def import_model(filepath: str, scale_factor: float, logger: logging.Logger) -> bool:
    """Import a 3D model into the scene and apply scaling"""
    ext = Path(filepath).suffix.lower()

    try:
        if ext == '.gltf' or ext == '.glb':
            bpy.ops.import_scene.gltf(filepath=filepath)
        elif ext == '.obj':
            bpy.ops.import_scene.obj(filepath=filepath)
        elif ext == '.fbx':
            bpy.ops.import_scene.fbx(filepath=filepath)
        else:
            logger.warning(f"Unsupported format: {ext}")
            return False

        # Apply scale factor to root objects only (children inherit the transform)
        if scale_factor != 1.0:
            for obj in bpy.context.selected_objects:
                if obj.parent is None:  # Only scale root objects to avoid double-scaling
                    obj.scale = (scale_factor, scale_factor, scale_factor)
                    # Apply scale to make it permanent
                    bpy.context.view_layer.objects.active = obj
                    bpy.ops.object.transform_apply(scale=True)
            logger.debug(f"Applied scale factor: {scale_factor}")

        return True

    except Exception as e:
        logger.error(f"Failed to import {filepath}: {e}")
        return False


def calculate_canvas_and_position(camera: bpy.types.Object, config: RenderConfig, logger: logging.Logger) -> Tuple[int, dict]:
    """
    Calculate canvas size and position camera at object center using FIXED ortho_scale.
    Center-center alignment: object center = canvas center.
    Returns canvas size and metadata dict.
    """
    # Get bounding box for all mesh objects
    min_x = min_y = min_z = float('inf')
    max_x = max_y = max_z = float('-inf')

    mesh_count = 0
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            mesh_count += 1
            for corner in obj.bound_box:
                # Convert to world space
                world_coord = obj.matrix_world @ Vector(corner)
                min_x = min(min_x, world_coord.x)
                max_x = max(max_x, world_coord.x)
                min_y = min(min_y, world_coord.y)
                max_y = max(max_y, world_coord.y)
                min_z = min(min_z, world_coord.z)
                max_z = max(max_z, world_coord.z)

    if mesh_count == 0:
        logger.warning("No mesh objects found to frame")
        return config.min_canvas_size, {}

    # Calculate object center (bounding box center)
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    center_z = (min_z + max_z) / 2

    # Calculate object dimensions
    width = max_x - min_x
    height = max_y - min_y
    depth = max_z - min_z

    # Position camera at object center with angle offset
    # Formula verified through manual Blender testing
    angle_rad = math.radians(config.camera_angle)
    yaw_rad = math.radians(config.camera_yaw)

    # Calculate camera offset distance (far enough to see everything)
    camera_distance = 10.0  # Ortho camera distance doesn't affect view, just needs to be > 0

    # Calculate offsets based on angle (from horizontal) and yaw (around Z axis)
    # First calculate offset in local coordinates (camera facing -Y)
    local_y_offset = -camera_distance * math.cos(angle_rad)
    local_z_offset = camera_distance * math.sin(angle_rad)

    # Rotate offset around Z axis by yaw to get world coordinates
    # Yaw 0° = camera faces -Y (south), 90° = faces -X (east), etc.
    world_x_offset = local_y_offset * math.sin(yaw_rad)
    world_y_offset = local_y_offset * math.cos(yaw_rad)

    # Position camera offset from center
    camera_pos = Vector((
        center_x + world_x_offset,   # Move based on yaw rotation
        center_y + world_y_offset,   # Move based on yaw rotation
        center_z + local_z_offset    # Move up based on angle
    ))
    camera.location = camera_pos

    # Point camera at object center using look-at math
    # Calculate direction vector from camera to center
    object_center = Vector((center_x, center_y, center_z))
    direction = object_center - camera_pos
    direction.normalize()

    # Calculate rotation to point camera at target
    # Based on Blender camera coordinate system: camera -Z axis points forward
    rot_quat = direction.to_track_quat('-Z', 'Y')
    camera.rotation_euler = rot_quat.to_euler()

    logger.debug(f"Camera positioned at: ({camera.location.x:.2f}, {camera.location.y:.2f}, {camera.location.z:.2f})")
    logger.debug(f"Camera rotation_euler: ({math.degrees(camera.rotation_euler.x):.1f}°, {math.degrees(camera.rotation_euler.y):.1f}°, {math.degrees(camera.rotation_euler.z):.1f}°)")

    # Calculate required canvas size based on FIXED ortho_scale
    # ortho_scale already has padding built in (8.0 means 8x8 unit view with margin)
    required_pixels = int(config.ortho_scale * config.pixels_per_unit)
    canvas_size = 2 ** math.ceil(math.log2(required_pixels))
    canvas_size = max(config.min_canvas_size, min(canvas_size, config.max_canvas_size))

    # Update scene resolution
    bpy.context.scene.render.resolution_x = canvas_size
    bpy.context.scene.render.resolution_y = canvas_size

    # Simplified metadata (no ground plane or texture_origin offsets)
    metadata = {
        "canvas_width": canvas_size,
        "canvas_height": canvas_size,
        "ortho_scale": config.ortho_scale,
        "pixels_per_unit": config.pixels_per_unit,
        "object_bounds": {
            "width": width,
            "height": height,
            "depth": depth,
            "center": {"x": center_x, "y": center_y, "z": center_z}
        }
    }

    logger.debug(f"Object dimensions: {width:.2f} x {height:.2f} x {depth:.2f} Blender units")
    logger.debug(f"Object center: ({center_x:.2f}, {center_y:.2f}, {center_z:.2f})")
    logger.debug(f"Camera positioned at: ({camera.location.x:.2f}, {camera.location.y:.2f}, {camera.location.z:.2f})")
    logger.debug(f"Fixed ortho_scale: {config.ortho_scale:.2f}")
    logger.debug(f"Canvas size: {canvas_size}x{canvas_size}")

    return canvas_size, metadata


# ============================================================================
# Metadata Export
# ============================================================================

def export_metadata(output_path: str, metadata: dict, logger: logging.Logger) -> bool:
    """Export sprite metadata as JSON for Godot import automation"""
    try:
        # Metadata file path: same as PNG but with .json extension
        metadata_path = output_path.replace('.png', '.json')

        # Ensure output directory exists
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)

        # Write JSON
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.debug(f"Exported metadata: {metadata_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to export metadata: {e}")
        return False


def auto_crop_sprite(image_path: str, logger: logging.Logger) -> dict:
    """
    Crop transparent pixels from sprite and return crop metadata.
    Reduces file size and memory usage while preserving visual quality.

    Returns dict with crop_offset and cropped_size for repositioning in Godot.
    """
    if not PIL_AVAILABLE:
        logger.warning("Auto-crop skipped: PIL/Pillow not installed")
        return {}

    try:
        img = Image.open(image_path)
        original_size = img.size

        # Get bounding box of non-transparent pixels
        bbox = img.getbbox()

        if bbox:
            # Crop to content
            cropped = img.crop(bbox)

            # Calculate offset and size
            offset = {"x": bbox[0], "y": bbox[1]}
            size = {"w": bbox[2] - bbox[0], "h": bbox[3] - bbox[1]}

            # Save cropped image
            cropped.save(image_path)

            logger.debug(f"Auto-cropped: {original_size[0]}×{original_size[1]} → {size['w']}×{size['h']} (offset: {offset['x']}, {offset['y']})")

            return {
                "original_size": {"w": original_size[0], "h": original_size[1]},
                "crop_offset": offset,
                "cropped_size": size
            }
        else:
            logger.warning(f"No visible pixels found in {image_path}")
            return {}

    except Exception as e:
        logger.error(f"Failed to auto-crop {image_path}: {e}")
        return {}


# ============================================================================
# Rendering
# ============================================================================

def render_sprite(output_path: str, logger: logging.Logger) -> bool:
    """Render the current scene to a PNG file"""
    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Set output path
        bpy.context.scene.render.filepath = output_path

        # Render
        bpy.ops.render.render(write_still=True)

        # Verify output
        if not os.path.exists(output_path):
            logger.error(f"Render completed but file not found: {output_path}")
            return False

        logger.debug(f"Rendered successfully: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Render failed: {e}")
        return False


# ============================================================================
# Batch Processing
# ============================================================================

def find_models(input_dir: str, formats: List[str]) -> List[Path]:
    """Find all 3D model files in directory (recursive)"""
    input_path = Path(input_dir)
    models = []

    for fmt in formats:
        models.extend(input_path.rglob(f"*{fmt}"))

    return sorted(models)


def process_batch(config: RenderConfig, logger: logging.Logger):
    """Process all models in input directory"""

    # Find all models
    models = find_models(config.input_dir, config.formats)

    if not models:
        logger.error(f"No models found in {config.input_dir}")
        return

    logger.info(f"Found {len(models)} models to process")

    # Setup scene once
    logger.info("Setting up scene...")
    clear_scene()
    camera = setup_camera(config)
    light = setup_lighting(config)
    setup_render_settings(config)

    # Statistics
    processed = 0
    skipped = 0
    failed = 0
    failed_files = []

    input_path = Path(config.input_dir)
    output_path = Path(config.output_dir)

    # Process each model
    for idx, model_path in enumerate(models, 1):
        # Calculate relative path to preserve directory structure
        rel_path = model_path.relative_to(input_path)
        output_file = output_path / rel_path.with_suffix('.png')

        logger.info(f"[{idx}/{len(models)}] Processing: {rel_path}")

        # Skip if output exists and skip_existing is enabled
        if config.skip_existing and output_file.exists():
            logger.info(f"  Skipping (already exists): {output_file}")
            skipped += 1
            continue

        # Clear previous objects (keep camera and light)
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH' or obj.type == 'EMPTY':
                obj.select_set(True)
            else:
                obj.select_set(False)
        bpy.ops.object.delete()

        # Import model
        if not import_model(str(model_path), config.scale_factor, logger):
            failed += 1
            failed_files.append(str(rel_path))
            continue

        # Render with rotations if enabled
        if config.rotations == 4:
            # Render 4 directional sprites (N/S/E/W)
            # With fixed ortho_scale, canvas size is consistent across all rotations
            rotations = [
                (0, '_s', 'South'),
                (90, '_e', 'East'),
                (180, '_n', 'North'),
                (270, '_w', 'West')
            ]

            # Save original camera yaw to restore after rotations
            original_yaw = config.camera_yaw

            render_success = True
            for angle, suffix, direction in rotations:
                # Rotate CAMERA around model instead of rotating the model
                # This shows the "proper" face from each direction
                logger.debug(f"  Rotating camera to {angle}° for {direction}")

                # Temporarily update camera yaw for this rotation
                config.camera_yaw = angle

                # Force complete depsgraph update to propagate transforms
                bpy.context.view_layer.update()
                depsgraph = bpy.context.evaluated_depsgraph_get()
                depsgraph.update()

                # Calculate canvas and position camera (fixed ortho_scale = consistent canvas size)
                canvas_size, metadata = calculate_canvas_and_position(camera, config, logger)

                # Add rotation info to metadata
                metadata['rotation_degrees'] = angle
                metadata['direction'] = direction

                # Generate output path with suffix
                rotated_output = str(output_file).replace('.png', f'{suffix}.png')

                if not render_sprite(rotated_output, logger):
                    render_success = False
                    failed += 1
                    failed_files.append(f"{rel_path} ({direction})")
                    logger.error(f"  ✗ Failed {direction}: {rotated_output}")
                else:
                    # Auto-crop transparent pixels if enabled
                    if config.auto_crop:
                        crop_meta = auto_crop_sprite(rotated_output, logger)
                        metadata.update(crop_meta)

                    # Export metadata alongside sprite
                    export_metadata(rotated_output, metadata, logger)
                    logger.debug(f"  ✓ Rendered {direction}: {rotated_output}")

            # Restore original camera yaw
            config.camera_yaw = original_yaw

            if render_success:
                processed += 1
                logger.info(f"  ✓ Saved 4 rotations to: {output_file.parent}/{output_file.stem}_*.png")
        else:
            # Single render (south-facing by default)
            # Calculate canvas and position camera
            canvas_size, metadata = calculate_canvas_and_position(camera, config, logger)

            # Add rotation info (single render defaults to south-facing)
            metadata['rotation_degrees'] = 0
            metadata['direction'] = 'South'

            if render_sprite(str(output_file), logger):
                # Auto-crop transparent pixels if enabled
                if config.auto_crop:
                    crop_meta = auto_crop_sprite(str(output_file), logger)
                    metadata.update(crop_meta)

                # Export metadata alongside sprite
                export_metadata(str(output_file), metadata, logger)
                processed += 1
                logger.info(f"  ✓ Saved: {output_file}")
            else:
                failed += 1
                failed_files.append(str(rel_path))
                logger.error(f"  ✗ Failed: {output_file}")

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("BATCH RENDER COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total models found: {len(models)}")
    logger.info(f"Successfully processed: {processed}")
    logger.info(f"Skipped (existing): {skipped}")
    logger.info(f"Failed: {failed}")

    if failed_files:
        logger.info("")
        logger.info("Failed files:")
        for f in failed_files:
            logger.info(f"  - {f}")

    logger.info("=" * 60)


# ============================================================================
# CLI Argument Parsing
# ============================================================================

def parse_arguments() -> RenderConfig:
    """Parse command-line arguments"""

    # Arguments after '--' are for this script
    # (everything before is for Blender)
    argv = sys.argv
    if '--' in argv:
        argv = argv[argv.index('--') + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(
        description='Batch render 3D models to 2D isometric sprites',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  blender --background --python blender_batch_render.py -- \\
      --input ./models --output ./sprites

  # Custom resolution and angle
  blender --background --python blender_batch_render.py -- \\
      --input ./models --output ./sprites \\
      --resolution 512 --angle 60 --samples 128

  # Load from config file
  blender --background --python blender_batch_render.py -- \\
      --config render_config.json
        """
    )

    parser.add_argument('--input', '-i',
                        help='Input directory containing 3D models')
    parser.add_argument('--output', '-o',
                        help='Output directory for rendered sprites')
    parser.add_argument('--resolution', '-r', type=int,
                        help='Output resolution (square, e.g., 512 for 512x512)')
    parser.add_argument('--angle', '-a', type=float,
                        help='Camera pitch angle in degrees (90 = top-down, 85-75 = angled)')
    parser.add_argument('--camera-yaw', type=float,
                        help='Camera yaw rotation in degrees (0 = north-facing, 45 = diamond view)')
    parser.add_argument('--ortho-scale', type=float,
                        help='Fixed orthographic scale in Blender units (default: 8.0)')
    parser.add_argument('--samples', '-s', type=int,
                        help='Anti-aliasing samples (higher = smoother, slower)')
    parser.add_argument('--pixels-per-unit', type=float,
                        help='Pixels per Blender unit for real-world scaling (default: 128)')
    parser.add_argument('--rotations', type=int, choices=[1, 4],
                        help='Number of rotations to render: 1 (single) or 4 (N/S/E/W)')
    parser.add_argument('--light-strength', type=float,
                        help='Light intensity (default: 3.0)')
    parser.add_argument('--scale-factor', type=float,
                        help='Scale factor for imported models (e.g., 0.5 to halve size, default: 1.0)')
    parser.add_argument('--skip-existing', action='store_true',
                        help='Skip files that already exist in output directory')
    parser.add_argument('--no-auto-crop', action='store_true',
                        help='Disable automatic cropping of transparent pixels')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('--log-file', type=str,
                        help='Write log to file')
    parser.add_argument('--config', '-c', type=str,
                        help='Load settings from JSON config file')

    args = parser.parse_args(argv)

    # Create config
    config = RenderConfig()

    # Load from config file if specified
    if args.config:
        with open(args.config, 'r') as f:
            config_data = json.load(f)
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)

    # Override with command-line arguments
    if args.input:
        config.input_dir = args.input
    if args.output:
        config.output_dir = args.output
    if args.resolution:
        config.resolution = args.resolution
    if args.angle is not None:
        config.camera_angle = args.angle
    if args.camera_yaw is not None:
        config.camera_yaw = args.camera_yaw
    if args.ortho_scale is not None:
        config.ortho_scale = args.ortho_scale
    if args.samples:
        config.samples = args.samples
    if args.pixels_per_unit:
        config.pixels_per_unit = args.pixels_per_unit
    if args.rotations:
        config.rotations = args.rotations
    if args.light_strength:
        config.light_strength = args.light_strength
    if args.scale_factor is not None:
        config.scale_factor = args.scale_factor
    if args.skip_existing:
        config.skip_existing = True
    if args.no_auto_crop:
        config.auto_crop = False
    if args.verbose:
        config.verbose = True
    if args.log_file:
        config.log_file = args.log_file

    # Validate
    if not config.input_dir:
        parser.error("--input is required")

    return config


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point"""
    config = parse_arguments()
    logger = setup_logging(config)

    logger.info("Blender Batch 3D-to-2D Sprite Renderer (Angled Top-Down)")
    logger.info(f"Input: {config.input_dir}")
    logger.info(f"Output: {config.output_dir}")
    logger.info(f"Camera angle: {config.camera_angle}° (55° = classic, 90° = pure top-down)")
    logger.info(f"Camera yaw: {config.camera_yaw}° (0° = north-facing)")
    logger.info(f"Ortho scale: {config.ortho_scale} Blender units (FIXED)")
    logger.info(f"Pixels per unit: {config.pixels_per_unit}")
    logger.info(f"Scale factor: {config.scale_factor}× (import scaling)")
    logger.info(f"Samples: {config.samples}")
    logger.info(f"Rotations: {config.rotations}")
    logger.info(f"Auto-crop: {'enabled' if config.auto_crop else 'disabled'}")
    logger.info("")

    process_batch(config, logger)


if __name__ == "__main__":
    main()
