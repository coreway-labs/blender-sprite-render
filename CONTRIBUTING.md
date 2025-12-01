# Contributing to Blender Sprite Render

Thanks for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Create a branch for your changes

## Development Setup

### Prerequisites

- Blender 3.0+ with Python bundled
- ImageMagick (for crop_sprites.sh)
- Bash shell

### Testing Changes

1. Download a free 3D asset pack for testing:
   - [Kenney](https://kenney.nl/) - CC0 licensed game assets
   - [Quaternius](https://quaternius.com/) - CC0 licensed 3D models

2. Run the test script:
   ```bash
   ./test_render.sh ./path-to-models ./test-output
   ```

3. Verify output sprites have:
   - Transparent backgrounds
   - Correct framing
   - Power-of-2 dimensions after cropping

## Code Style

### Python (blender_batch_render.py)

- Follow PEP 8 style guidelines
- Use type hints where practical
- Add docstrings for functions
- Keep compatibility with Blender's bundled Python

### Shell Scripts

- Use `set -e` for error handling
- Quote all variables
- Provide helpful error messages
- Support both PATH-based and direct Blender invocation

## Submitting Changes

### Pull Request Process

1. Update the README.md if you've changed functionality
2. Test your changes with at least one asset pack
3. Keep commits focused and atomic
4. Write clear commit messages

### Commit Messages

Use clear, descriptive commit messages:

```
Add support for .dae (Collada) format

- Add Collada import in import_model()
- Update supported formats list
- Add to README documentation
```

## Feature Requests & Bug Reports

### Bug Reports

Please include:
- Blender version (`blender --version`)
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Sample model file (if possible)

### Feature Requests

Describe:
- The problem you're trying to solve
- Your proposed solution
- Alternative approaches considered

## Areas for Contribution

Some areas where contributions are welcome:

- **New export formats**: Support for additional output formats
- **Additional 3D formats**: Support for more input formats (.dae, etc.)
- **Performance**: Optimizations for large batch processing
- **Documentation**: Tutorials, examples, translations
- **Testing**: Test scripts, CI/CD integration

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
