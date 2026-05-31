"""test_image_generation.py — Test image generation with Pollinations"""
import sys
sys.path.insert(0, ".")

from services.ai.image_generator import quick_generate

OUTPUT_DIR = "C:/React-Nextjs-Projects/Jarvis AI/tests_output"

print("Testing image generation...")
result = quick_generate(
    "A futuristic robot in a cyberpunk city",
    style="cyberpunk",
    aspect_ratio="16:9"
)
print(f"Success: {result.get('success')}")
if result.get("success"):
    print(f"Path: {result.get('path')}")
    print(f"URL: {result.get('url')}")
    print(f"Dimensions: {result.get('dimensions')}")
    print(f"Seed: {result.get('seed')}")
    print(f"File size: {result.get('metadata', {}).get('file_size', 'N/A')} bytes")
else:
    print(f"Error: {result.get('error', 'unknown')}")
