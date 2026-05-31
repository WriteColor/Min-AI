#!/usr/bin/env python3
"""Test volume control fix."""

import sys
sys.path.insert(0, '.')

from services.system.windows_api import WindowsService

print("=== Testing Volume Control Fix ===\n")

service = WindowsService()

# Get initial volume
print("--- Getting initial volume ---")
initial = service.get_volume()
print(f"Initial volume: {initial}%")

# Set to 50%
print("\n--- Setting volume to 50% ---")
result = service.set_volume(50)
print(f"set_volume(50) result: {result}")

# Verify
print("\n--- Verifying volume ---")
after = service.get_volume()
print(f"Volume after setting: {after}%")

# Set to 75%
print("\n--- Setting volume to 75% ---")
result = service.set_volume(75)
print(f"set_volume(75) result: {result}")

# Verify
final = service.get_volume()
print(f"Final volume: {final}%")

# Test mute
print("\n--- Testing mute ---")
mute_result = service.mute_system()
print(f"mute_system() result: {mute_result}")

# Check if muted (volume should be 0 or very low)
after_mute = service.get_volume()
print(f"Volume after mute: {after_mute}%")

# Restore to 50%
print("\n--- Restoring to 50% ---")
service.set_volume(50)
restored = service.get_volume()
print(f"Restored volume: {restored}%")

print("\n=== Test Complete ===")

if final == 75 and after_mute == 0:
    print("\nSUCCESS: Volume control works correctly!")
else:
    print(f"\nFAIL: Expected final=75, after_mute=0, got final={final}, after_mute={after_mute}")