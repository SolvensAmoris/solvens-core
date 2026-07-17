# BUILD & RELEASE GUIDE
## Cosmos v0.4.5-rc1

---

## Prerequisites

```bash
# Install build tools
pip install build twine wheel pyinstaller

# Install cosmos dependencies
pip install -e ".[cosmos]"
```

---

## 1. Build Package (PyPI)

### Build Source Distribution

```bash
python -m build
# Output: dist/solvens_core-0.4.5rc1.tar.gz
```

### Build Wheel

```bash
python -m build --wheel
# Output: dist/solvens_core-0.4.5rc1-py3-none-any.whl
```

### Upload to PyPI

```bash
# Test PyPI (recommended first)
twine upload --repository testpypi dist/*

# Production PyPI
twine upload dist/*
```

### Install from PyPI

```bash
pip install cosmos-compiler
cosmos --version
```

---

## 2. Build Binary (PyInstaller)

### Single Binary (all platforms)

```bash
# Linux/Mac
pyinstaller --onefile --name cosmos --console cosmos/cli.py

# Windows
pyinstaller --onefile --name cosmos.exe --console cosmos/cli.py
```

### Output

```
dist/cosmos         # Linux/Mac
dist/cosmos.exe     # Windows
```

### Cross-compile (advanced)

```bash
# Using docker for cross-compilation
docker run --rm -v $(pwd):/app python:3.12-slim \
    sh -c "pip install pyinstaller && pyinstaller --onefile /app/cosmos/cli.py"
```

---

## 3. Build Docker Image

```bash
# Build API image
docker build -f docker/Dockerfile.api -t solvens/cosmos:latest .

# Build all-in-one
docker build -t solvens/cosmos:latest -f docker/Dockerfile.all-in-one .
```

### Run with Docker Compose

```bash
docker-compose up -d
docker-compose ps
```

---

## 4. VSCode Extension

### Package

```bash
cd vscode-extension
npm install
npm run compile
vsce package
# Output: cosmos-dsl-0.4.5.vsix
```

### Publish to Marketplace

```bash
# Create publisher account at https://marketplace.visualstudio.com/
vsce login <publisher-name>
vsce publish
```

### Install locally

```bash
code --install-extension cosmos-dsl-0.4.5.vsix
```

---

## 5. Release Checklist

### Pre-release

- [ ] Run all tests: `pytest tests/ -v`
- [ ] Update version in `pyproject.toml`
- [ ] Update CHANGELOG.md
- [ ] Update docs/EXPORT_SCHEMA.md if schema changed

### Build verification

- [ ] `python -m build` succeeds
- [ ] `pip install dist/solvens_core-*.whl` succeeds
- [ ] `cosmos --version` works
- [ ] `cosmos compile tests/fixtures/valid_cosmos.cosmos` works

### Release

- [ ] Create git tag: `git tag v0.4.5-rc1`
- [ ] Push tag: `git push origin v0.4.5-rc1`
- [ ] Upload to PyPI: `twine upload dist/*`
- [ ] Publish VSCode extension
- [ ] Create GitHub Release

---

## 6. Quick Start Scripts

### build.sh

```bash
#!/bin/bash
set -e

echo "Building Cosmos v0.4.5-rc1..."

# Clean
rm -rf dist/ build/ *.egg-info

# Build
python -m build

# Test
pip install dist/solvens_core-*.whl --force-reinstall

echo "Build complete!"
echo "Files:"
ls -la dist/
```

### release.sh

```bash
#!/bin/bash
set -e

VERSION=$1

if [ -z "$VERSION" ]; then
    echo "Usage: ./release.sh 0.4.5"
    exit 1
fi

echo "Releasing Cosmos v$VERSION..."

# Build
./build.sh

# Upload
twine upload dist/*

# Tag
git tag v$VERSION
git push origin v$VERSION

echo "Release complete!"
```

---

## 7. CI/CD (GitHub Actions)

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          
      - name: Install dependencies
        run: |
          pip install build twine
          pip install -e ".[cosmos]"
          
      - name: Build
        run: python -m build
        
      - name: Upload to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
        run: twine upload dist/*
```

---

## 8. Version Numbering

Format: `MAJOR.MINOR.PATCH[-PRERELEASE]`

Examples:
- `0.4.5` - Stable release
- `0.4.5-rc1` - Release candidate
- `0.5.0-alpha1` - Alpha preview

---

## 9. Troubleshooting

### PyInstaller issues

```bash
# Rebuild
pyinstaller --clean --onefile cosmos/cli.py

# Debug
pyinstaller --debug=all cosmos/cli.py
```

### Import errors

```bash
# Reinstall
pip uninstall cosmos-compiler -y
pip install -e ".[cosmos]"
```

### PyPI upload fails

```bash
# Check credentials
twine check dist/*

# Try again with verbose
twine upload --verbose dist/*
```

---

## 10. Post-Release

1. Create GitHub Release with changelog
2. Update documentation website
3. Announce on social media
4. Update README.md with new version
5. Close related GitHub issues

---

*Author: Luis Alberto Burciaga Miker*  
*Version: 0.4.5-rc1*
