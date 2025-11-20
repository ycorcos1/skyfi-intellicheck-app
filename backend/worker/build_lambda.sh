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
# Install for Lambda platform (Linux x86_64, Python 3.11)
# Lambda uses Python 3.11, so we need to specify the Python version and ABI
python3 -m pip install -r "${SCRIPT_DIR}/requirements.txt" -t "$BUILD_DIR" \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --python-version 3.11 \
    --implementation cp \
    --abi cp311 \
    --no-cache-dir 2>&1 | grep -v "WARNING: Target platform" || {
    echo "Warning: Platform-restricted install failed, trying without Python version restriction..."
    python3 -m pip install -r "${SCRIPT_DIR}/requirements.txt" -t "$BUILD_DIR" --platform manylinux2014_x86_64 --only-binary=:all: --no-cache-dir 2>&1 | grep -v "WARNING: Target platform" || {
        echo "Warning: Platform install failed, using regular install (may have platform issues)..."
        python3 -m pip install -r "${SCRIPT_DIR}/requirements.txt" -t "$BUILD_DIR" --no-cache-dir
    }
}

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

if [ -f "${SCRIPT_DIR}/../app/models/document.py" ]; then
    cp "${SCRIPT_DIR}/../app/models/document.py" "$BUILD_DIR/app/models/"
fi

# Copy all other model files that might be needed
for model_file in "${SCRIPT_DIR}/../app/models"/*.py; do
    if [ -f "$model_file" ]; then
        filename=$(basename "$model_file")
        if [ "$filename" != "__init__.py" ]; then
            cp "$model_file" "$BUILD_DIR/app/models/" 2>/dev/null || true
        fi
    fi
done

# Create minimal stubs for app.core modules (worker doesn't use these, but models import them)
# Create minimal config.py stub
cat > "$BUILD_DIR/app/core/config.py" << 'EOFCONFIG'
"""Minimal config stub for Lambda worker - avoids pydantic-settings dependency."""
from functools import lru_cache
from typing import Optional

class Settings:
    """Stub Settings class - not used by worker."""
    def __init__(self):
        self.db_url: str = ""
        self.api_version: str = "1.0.0"
        self.environment: str = "development"
        self.host: str = "0.0.0.0"
        self.port: int = 8000
        self.cognito_region: str = "us-east-1"
        self.cognito_user_pool_id: Optional[str] = None
        self.cognito_app_client_id: Optional[str] = None
        self.cognito_issuer: Optional[str] = None
        self.git_sha: Optional[str] = None

@lru_cache
def get_settings() -> Settings:
    """Return stub settings - worker uses WorkerConfig instead."""
    return Settings()
EOFCONFIG

# Create minimal database.py stub (worker only needs Base, not the engine)
cat > "$BUILD_DIR/app/core/database.py" << 'EOFDATABASE'
"""Minimal database stub for Lambda worker - only provides Base for models."""
from sqlalchemy.ext.declarative import declarative_base

# Export Base for models to use
Base = declarative_base()

# Stub other exports that models might reference (not used by worker)
def get_db():
    """Stub - worker uses DatabaseManager instead."""
    raise NotImplementedError("Worker uses DatabaseManager, not get_db")
EOFDATABASE

# Create deployment package
echo "Creating deployment package..."
cd "$BUILD_DIR"
zip -r "../${PACKAGE_NAME}" . -x "*.pyc" -x "*__pycache__*" -x "*.git*" -x "*.DS_Store" > /dev/null

# Clean up build directory
cd "$SCRIPT_DIR"
rm -rf "$BUILD_DIR"

echo "✅ Deployment package created: ${SCRIPT_DIR}/${PACKAGE_NAME}"
echo "Size: $(du -h "${SCRIPT_DIR}/${PACKAGE_NAME}" | cut -f1)"

