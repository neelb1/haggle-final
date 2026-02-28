#!/bin/bash
# Build script for Render: installs Python deps + builds dashboard
set -e

# Python deps
pip install -r requirements.txt

# Build dashboard if it exists
if [ -d "../dashboard" ]; then
    # Check if Node.js is available
    if ! command -v node &> /dev/null; then
        echo "Installing Node.js..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - 2>/dev/null || true
        apt-get install -y nodejs 2>/dev/null || {
            echo "Node.js not available on this runtime, skipping dashboard build"
            exit 0
        }
    fi
    echo "Node.js version: $(node --version)"
    echo "npm version: $(npm --version)"
    echo "Building dashboard..."
    cd ../dashboard
    npm install
    npm run build
    # Copy built files into backend/static
    rm -rf ../backend/static
    cp -r dist ../backend/static
    cd ../backend
    echo "Dashboard built and copied to backend/static/"
else
    echo "No dashboard directory found, skipping frontend build"
fi
