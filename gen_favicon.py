#!/usr/bin/env python3
"""
Favicon Generator Script for MoviesThisDay

This script resizes a source PNG image (e.g., static/icon.png) to standard favicon size (32x32),
encodes it as a base64 PNG data URL, and prints the result for embedding in Python or HTML.

Usage:
    python gen_favicon.py

Configuration:
    - Set input_image_path to your source image (should be square and high-res for best results)
    - Output is printed to stdout as a data URL string

Dependencies:
    - pip install Pillow

Author: Jason A. Cox
Date: 2025-07-26
"""
from PIL import Image
import base64
import io
import sys
import os

# CONFIGURE
input_image_path = "static/icon.png"      # Path to your generated image
output_image_path = "static/favicon.png"  # Output path for the resized favicon
output_size = (32, 32)                    # Standard favicon size

# ARGUMENTS
if len(sys.argv) > 1:
    input_image_path = sys.argv[1]
if len(sys.argv) > 2:
    output_image_path = sys.argv[2]
# Ensure the input image exists
try:
    with open(input_image_path, "rb") as f:
        pass  # Just check if the file exists
except FileNotFoundError:
    print(f"Error: Input image '{input_image_path}' not found.")
    sys.exit(1)


# LOAD AND RESIZE
im = Image.open(input_image_path).convert("RGBA")
im = im.resize(output_size, Image.LANCZOS)

# CHECK IF OUTPUT FILE EXISTS AND PROMPT FOR OVERWRITE
if os.path.exists(output_image_path):
    resp = (
        input(f"Output file '{output_image_path}' already exists. Overwrite? [y/N]: ")
        .strip()
        .lower()
    )
    if resp not in ("y", "yes"):
        print("Aborted. Output file not overwritten.")
        sys.exit(0)

# SAVE RESIZED IMAGE TO OUTPUT FILE
im.save(output_image_path, format="PNG")

# SAVE TO BYTES
buffer = io.BytesIO()
im.save(buffer, format="PNG")
buffer.seek(0)
img_bytes = buffer.read()

# ENCODE BASE64
favicon_base64 = "data:image/png;base64," + base64.b64encode(img_bytes).decode("utf-8")

# PRINT THE RESULTING STRING
print(favicon_base64)
