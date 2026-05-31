"""test_lyrics_generation.py — Test lyrics generation with MiniMax API"""
import sys
sys.path.insert(0, ".")

from services.ai.music_generator import quick_lyrics

print("Testing lyrics generation...")
result = quick_lyrics("A happy electronic song about coding")
print(f"Success: {result.get('success')}")
if result.get("success"):
    lyrics = result.get("lyrics", "")
    print(f"\nLyrics preview:\n{lyrics[:800]}")
    # Save to file
    with open("C:/React-Nextjs-Projects/Jarvis AI/tests_output/lyrics_test.txt", "w", encoding="utf-8") as f:
        f.write(lyrics)
    print("\nSaved to tests_output/lyrics_test.txt")
else:
    print(f"Error: {result.get('error', 'unknown')}")
