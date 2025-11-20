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

# Copy index.py to root (Lambda handler entry point)
echo "Copying Lambda entry point..."
cp "${SCRIPT_DIR}/index.py" "$BUILD_DIR/" 2>/dev/null || true

# Create worker directory structure
echo "Creating worker directory structure..."
mkdir -p "$BUILD_DIR/worker"

# Copy worker code to worker/ directory (excluding index.py)
echo "Copying worker code..."
for py_file in "${SCRIPT_DIR}"/*.py; do
    filename=$(basename "$py_file")
    if [ "$filename" != "index.py" ]; then
        cp "$py_file" "$BUILD_DIR/worker/" 2>/dev/null || true
    fi
done

# Copy worker modules
if [ -d "${SCRIPT_DIR}/integrations" ]; then
    cp -r "${SCRIPT_DIR}/integrations" "$BUILD_DIR/worker/"
fi

if [ -d "${SCRIPT_DIR}/scoring" ]; then
    cp -r "${SCRIPT_DIR}/scoring" "$BUILD_DIR/worker/"
fi

# Copy worker __init__.py if it exists
if [ -f "${SCRIPT_DIR}/__init__.py" ]; then
    cp "${SCRIPT_DIR}/__init__.py" "$BUILD_DIR/worker/"
fi

# Copy other worker files (correlation, rate_limiter, observability, models, etc.)
for file in correlation.py rate_limiter.py observability.py models.py; do
    if [ -f "${SCRIPT_DIR}/${file}" ]; then
        cp "${SCRIPT_DIR}/${file}" "$BUILD_DIR/worker/"
    fi
done

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

# Copy core modules (database, config)
if [ -f "${SCRIPT_DIR}/../app/core/database.py" ]; then
    cp "${SCRIPT_DIR}/../app/core/database.py" "$BUILD_DIR/app/core/"
fi

if [ -f "${SCRIPT_DIR}/../app/core/config.py" ]; then
    cp "${SCRIPT_DIR}/../app/core/config.py" "$BUILD_DIR/app/core/"
fi

# Copy backend/config.py (required by app.core.config)
if [ -f "${SCRIPT_DIR}/../config.py" ]; then
    cp "${SCRIPT_DIR}/../config.py" "$BUILD_DIR/"
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

