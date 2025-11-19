#!/bin/bash
# Lambda deployment package builder for SkyFi IntelliCheck Worker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/lambda_build"
PACKAGE_NAME="lambda_deployment_package.zip"

echo "Starting Lambda deployment package build..."

# Clean previous build
rm -rf "$BUILD_DIR"
rm -f "${SCRIPT_DIR}/${PACKAGE_NAME}"
mkdir -p "$BUILD_DIR"

# Install dependencies
echo "Installing Python dependencies..."
python3 -m pip install -r "${SCRIPT_DIR}/requirements.txt" -t "$BUILD_DIR" --platform manylinux2014_x86_64 --only-binary=:all: --no-cache-dir

# Copy worker code
echo "Copying worker code..."
cp -r "${SCRIPT_DIR}"/*.py "$BUILD_DIR/" 2>/dev/null || true

# Copy worker modules
if [ -d "${SCRIPT_DIR}/integrations" ]; then
    cp -r "${SCRIPT_DIR}/integrations" "$BUILD_DIR/"
fi

if [ -d "${SCRIPT_DIR}/scoring" ]; then
    cp -r "${SCRIPT_DIR}/scoring" "$BUILD_DIR/"
fi

# Copy necessary backend app modules (models)
echo "Copying backend app models..."
mkdir -p "$BUILD_DIR/app"
mkdir -p "$BUILD_DIR/app/models"
mkdir -p "$BUILD_DIR/app/core"

# Copy __init__.py files
if [ -f "${SCRIPT_DIR}/../app/__init__.py" ]; then
    cp "${SCRIPT_DIR}/../app/__init__.py" "$BUILD_DIR/app/"
fi

if [ -f "${SCRIPT_DIR}/../app/models/__init__.py" ]; then
    cp "${SCRIPT_DIR}/../app/models/__init__.py" "$BUILD_DIR/app/models/"
fi

if [ -f "${SCRIPT_DIR}/../app/core/__init__.py" ]; then
    cp "${SCRIPT_DIR}/../app/core/__init__.py" "$BUILD_DIR/app/core/"
fi

# Copy model files
if [ -f "${SCRIPT_DIR}/../app/models/company.py" ]; then
    cp "${SCRIPT_DIR}/../app/models/company.py" "$BUILD_DIR/app/models/"
fi

if [ -f "${SCRIPT_DIR}/../app/models/analysis.py" ]; then
    cp "${SCRIPT_DIR}/../app/models/analysis.py" "$BUILD_DIR/app/models/"
fi

# Copy database module
if [ -f "${SCRIPT_DIR}/../app/core/database.py" ]; then
    cp "${SCRIPT_DIR}/../app/core/database.py" "$BUILD_DIR/app/core/"
fi

# Create deployment package
echo "Creating deployment package..."
cd "$BUILD_DIR"
zip -r "../${PACKAGE_NAME}" . -x "*.pyc" -x "*__pycache__*" -x "*.git*" -x "*.DS_Store" > /dev/null

# Clean up build directory
cd "$SCRIPT_DIR"
rm -rf "$BUILD_DIR"

echo "✅ Deployment package created: ${SCRIPT_DIR}/${PACKAGE_NAME}"
echo "Size: $(du -h "${SCRIPT_DIR}/${PACKAGE_NAME}" | cut -f1)"

