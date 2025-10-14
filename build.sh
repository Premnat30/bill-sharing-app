#!/bin/bash
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Creating necessary directories..."
mkdir -p static/css static/js static/images templates uploads

echo "Build completed successfully!"
