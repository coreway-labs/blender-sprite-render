#!/usr/bin/env python3
"""
Quick script to inspect Blender Unit sizes of 3D models
Usage: blender --background --python inspect_model_sizes.py -- <model_path1> <model_path2> ...
"""

import bpy
import sys
from pathlib import Path
from mathutils import Vector

def clear_scene():
    """Remove all objects from the scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def inspect_model(filepath: str) -> dict:
    """Load a model and return its bounding box dimensions"""
    print(f"\nInspecting: {Path(filepath).name}")

    # Clear scene
    clear_scene()

    # Import model
    ext = Path(filepath).suffix.lower()
    try:
        if ext in ['.gltf', '.glb']:
            bpy.ops.import_scene.gltf(filepath=filepath)
        elif ext == '.obj':
            bpy.ops.import_scene.obj(filepath=filepath)
        elif ext == '.fbx':
            bpy.ops.import_scene.fbx(filepath=filepath)
        else:
            print(f"  ⚠️  Unsupported format: {ext}")
            return None
    except Exception as e:
        print(f"  ❌ Failed to import: {e}")
        return None

    # Calculate bounding box
    min_x = min_y = min_z = float('inf')
    max_x = max_y = max_z = float('-inf')

    mesh_count = 0
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            mesh_count += 1
            for corner in obj.bound_box:
                world_coord = obj.matrix_world @ Vector(corner)
                min_x = min(min_x, world_coord.x)
                max_x = max(max_x, world_coord.x)
                min_y = min(min_y, world_coord.y)
                max_y = max(max_y, world_coord.y)
                min_z = min(min_z, world_coord.z)
                max_z = max(max_z, world_coord.z)

    if mesh_count == 0:
        print("  ⚠️  No mesh objects found")
        return None

    # Calculate dimensions
    width = max_x - min_x
    height = max_y - min_y
    depth = max_z - min_z

    print(f"  Mesh objects: {mesh_count}")
    print(f"  Bounding box: {width:.3f} × {height:.3f} × {depth:.3f} BU")
    print(f"  Max dimension: {max(width, height, depth):.3f} BU")

    return {
        "file": Path(filepath).name,
        "width": width,
        "height": height,
        "depth": depth,
        "max": max(width, height, depth)
    }

def main():
    # Get arguments after '--'
    argv = sys.argv
    if '--' in argv:
        argv = argv[argv.index('--') + 1:]
    else:
        print("Usage: blender --background --python inspect_model_sizes.py -- <model_path1> <model_path2> ...")
        return

    if not argv:
        print("ERROR: No model paths provided")
        return

    print("=" * 60)
    print("Blender Model Size Inspector")
    print("=" * 60)

    results = []
    for model_path in argv:
        result = inspect_model(model_path)
        if result:
            results.append(result)

    # Summary
    if results:
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"{'Model':<40} {'Max Size (BU)':<15}")
        print("-" * 60)
        for r in results:
            print(f"{r['file']:<40} {r['max']:>14.3f}")

        avg_size = sum(r['max'] for r in results) / len(results)
        print("-" * 60)
        print(f"{'Average':<40} {avg_size:>14.3f}")
        print()

        # Recommendations
        print("SCALE FACTOR RECOMMENDATIONS:")
        print(f"  For 1 BU = 1 game tile: scale_factor = {1.0 / avg_size:.3f}")
        print(f"  For 2 BU = 1 game tile: scale_factor = {2.0 / avg_size:.3f}")
        print(f"  No scaling: scale_factor = 1.0")
        print()

if __name__ == "__main__":
    main()
