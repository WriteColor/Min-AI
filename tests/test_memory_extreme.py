"""
test_memory_extreme.py — Extreme Memory System Tests
==================================================
Tests the memory system with extreme cases.
"""

import sys
import os
import json
import time
import threading
sys.path.insert(0, ".")

from memory.memory_manager import (
    load_memory, save_memory, update_memory, remember, forget,
    forget_memory, format_memory_for_prompt,
    _empty_memory, _truncate_value, _recursive_update, _all_entries,
    _trim_to_limit, MEMORY_PATH
)

OUTPUT_DIR = "C:/React-Nextjs-Projects/Jarvis AI/tests_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def test_load_save():
    """Test basic load and save."""
    print("\n[TEST 01] Load and Save")
    initial = load_memory()
    print(f"  Initial memory keys: {list(initial.keys())}")
    assert isinstance(initial, dict), "Memory should be a dict"
    print("  [PASS]")


def test_empty_memory():
    """Test empty memory structure."""
    print("\n[TEST 02] Empty Memory Structure")
    empty = _empty_memory()
    expected_keys = ["notes", "habits", "preferences", "context"]
    for key in expected_keys:
        assert key in empty, f"Missing key: {key}"
    print(f"  Empty structure: {empty}")
    print("  [PASS]")


def test_remember_single():
    """Test storing a single memory."""
    print("\n[TEST 03] Remember Single")
    remember("notes", "test_key", "Test value content")
    mem = load_memory()
    assert "notes" in mem, "notes category missing"
    assert "test_key" in mem["notes"], "test_key not found"
    assert mem["notes"]["test_key"]["value"] == "Test value content"
    print(f"  Stored and retrieved: {mem['notes']['test_key']}")
    print("  [PASS]")


def test_update_memory():
    """Test recursive update."""
    print("\n[TEST 04] Update Memory (Recursive)")
    updates = {
        "notes": {"update_test": {"value": "Updated content"}},
        "habits": {"daily_exercise": {"value": "Running"}},
        "new_category": {"new_key": {"value": "New category value"}}
    }
    update_memory(updates)
    mem = load_memory()
    assert mem["notes"]["update_test"]["value"] == "Updated content"
    assert mem["habits"]["daily_exercise"]["value"] == "Running"
    assert mem["new_category"]["new_key"]["value"] == "New category value"
    print("  [PASS]")


def test_forget():
    """Test forgetting a single value."""
    print("\n[TEST 05] Forget Single")
    remember("test_forget", "key_to_delete", "Temp value")
    forget("test_forget", "key_to_delete")
    mem = load_memory()
    assert "key_to_delete" not in mem.get("test_forget", {})
    print("  [PASS]")


def test_forget_memory():
    """Test clearing all memory."""
    print("\n[TEST 06] Forget All Memory")
    remember("notes", "temp1", "Value 1")
    remember("habits", "temp2", "Value 2")
    forget_memory()
    mem = load_memory()
    empty = _empty_memory()
    assert mem == empty, "Memory should be empty after forget_memory"
    print("  [PASS]")


def test_truncation():
    """Test value truncation for long values."""
    print("\n[TEST 07] Value Truncation")
    long_value = "A" * 600  # Exceeds MAX_VALUE_LENGTH (500)
    truncated = _truncate_value(long_value)
    assert len(truncated) <= 500 + len("... [truncated]"), "Should be truncated"
    assert truncated.endswith("... [truncated]"), "Should have truncation marker"
    print(f"  Original: {len(long_value)} chars -> Truncated: {len(truncated)} chars")
    print("  [PASS]")


def test_trim_to_limit():
    """Test memory trimming when it exceeds limit."""
    print("\n[TEST 08] Trim to Memory Limit")
    # Create a large memory
    large_mem = {"notes": {}}
    for i in range(100):
        large_mem["notes"][f"key_{i}"] = {"value": f"Content for key {i} " * 50}

    trimmed = _trim_to_limit(large_mem)
    entries = _all_entries(trimmed)
    total_len = sum(len(c) + len(k) + len(v) for c, k, v in entries)

    from memory.memory_manager import MEMORY_MAX_CHARS
    assert total_len <= MEMORY_MAX_CHARS, f"Should be under {MEMORY_MAX_CHARS}, got {total_len}"
    print(f"  Trimmed from ~{len(json.dumps(large_mem))} to {total_len} chars")
    print("  [PASS]")


def test_format_for_prompt():
    """Test formatting memory for system prompt."""
    print("\n[TEST 09] Format Memory for Prompt")
    mem = {
        "notes": {"idea1": {"value": "Build an AI"}},
        "habits": {"exercise": {"value": "Run daily"}}
    }
    formatted = format_memory_for_prompt(mem)
    assert "NOTES:" in formatted
    assert "HABITS:" in formatted
    assert "Build an AI" in formatted
    assert "Run daily" in formatted
    print(f"  Formatted preview:\n{formatted[:200]}...")
    print("  [PASS]")


def test_concurrent_updates():
    """Test thread-safe concurrent updates."""
    print("\n[TEST 10] Concurrent Updates (Thread Safety)")
    forget_memory()

    errors = []
    def update_task(thread_id):
        try:
            for i in range(20):
                update_memory({f"notes": {f"thread_{thread_id}_note_{i}": {"value": f"Content {i}"}}})
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=update_task, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Errors during concurrent access: {errors}"
    mem = load_memory()
    note_count = len(mem.get("notes", {}))
    print(f"  5 threads x 20 updates = {5*20} total, {note_count} stored")
    assert note_count == 100, f"Expected 100, got {note_count}"
    print("  [PASS]")


def test_recursive_update():
    """Test recursive update behavior."""
    print("\n[TEST 11] Recursive Update")
    base = {"a": {"b": {"c": "original"}, "d": "keep"}, "e": "new"}
    updates = {"a": {"b": {"c": "updated"}, "f": "added"}}
    result = _recursive_update(base, updates)

    assert result["a"]["b"]["c"] == "updated", "Nested value should be updated"
    assert result["a"]["d"] == "keep", "Existing sibling should be preserved"
    assert result["a"]["f"] == "added", "New nested value should be added"
    assert result["e"] == "new", "Top-level new value should be added"
    print(f"  Result: {result}")
    print("  [PASS]")


def test_all_entries():
    """Test extracting all entries from memory."""
    print("\n[TEST 12] All Entries Extraction")
    mem = {
        "notes": {"n1": {"value": "Note 1"}, "n2": {"value": "Note 2"}},
        "habits": {"h1": {"value": "Habit 1"}},
    }
    entries = _all_entries(mem)
    assert len(entries) == 3, f"Expected 3 entries, got {len(entries)}"
    print(f"  Entries: {entries}")
    print("  [PASS]")


def test_unicode_memory():
    """Test storing Unicode/special characters."""
    print("\n[TEST 13] Unicode Memory")
    unicode_text = "Hola mundo! Zmey Gorynych . ? ! @ # $ % ^ & * ( ) 中文 日本語 한국어 🎉🎊🔥"
    remember("notes", "unicode_test", unicode_text)
    mem = load_memory()
    assert mem["notes"]["unicode_test"]["value"] == unicode_text
    print(f"  Stored and retrieved: {unicode_text[:50]}...")
    print("  [PASS]")


def test_special_chars_memory():
    """Test storing special characters."""
    print("\n[TEST 14] Special Characters Memory")
    special = "<script>alert('xss')</script> & \"quotes\" 'single' `backticks`"
    remember("notes", "special_chars", special)
    mem = load_memory()
    assert mem["notes"]["special_chars"]["value"] == special
    print("  [PASS]")


def test_large_memory():
    """Test storing large amounts of data."""
    print("\n[TEST 15] Large Memory Storage")
    large_text = "Lorem ipsum dolor sit amet. " * 500  # About 9500 chars
    remember("notes", "large_data", large_text)
    mem = load_memory()
    stored = mem["notes"]["large_data"]["value"]
    # Should be truncated to MAX_VALUE_LENGTH
    from memory.memory_manager import MAX_VALUE_LENGTH
    assert len(stored) <= MAX_VALUE_LENGTH + len("... [truncated]")
    print(f"  Original: {len(large_text)} chars -> Stored: {len(stored)} chars")
    print("  [PASS]")


def test_empty_values():
    """Test handling of empty values."""
    print("\n[TEST 16] Empty Values")
    remember("notes", "empty_value", "")
    mem = load_memory()
    assert mem["notes"]["empty_value"]["value"] == ""
    print("  [PASS]")


def test_deep_nesting():
    """Test deep nesting in memory."""
    print("\n[TEST 17] Deep Nesting")
    deep_update = {
        "level1": {
            "level2": {
                "level3": {
                    "level4": {"value": "Deep value"}
                }
            }
        }
    }
    update_memory(deep_update)
    mem = load_memory()
    assert mem["level1"]["level2"]["level3"]["level4"]["value"] == "Deep value"
    print("  [PASS]")


def test_multiple_categories():
    """Test all categories work correctly."""
    print("\n[TEST 18] Multiple Categories")
    categories = ["notes", "habits", "preferences", "context"]
    for cat in categories:
        remember(cat, "test_key", f"Value for {cat}")
    mem = load_memory()
    for cat in categories:
        assert mem[cat]["test_key"]["value"] == f"Value for {cat}"
    print(f"  All {len(categories)} categories work correctly")
    print("  [PASS]")


def run_all_tests():
    print("=" * 60)
    print("EXTREME MEMORY SYSTEM TESTS")
    print("=" * 60)

    tests = [
        test_load_save,
        test_empty_memory,
        test_remember_single,
        test_update_memory,
        test_forget,
        test_forget_memory,
        test_truncation,
        test_trim_to_limit,
        test_format_for_prompt,
        test_concurrent_updates,
        test_recursive_update,
        test_all_entries,
        test_unicode_memory,
        test_special_chars_memory,
        test_large_memory,
        test_empty_values,
        test_deep_nesting,
        test_multiple_categories,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{len(tests)} passed, {failed} failed")
    print("=" * 60)

    # Show final memory state
    print("\nFinal Memory State:")
    mem = load_memory()
    for cat, keys in mem.items():
        if isinstance(keys, dict) and len(keys) > 0:
            print(f"  [{cat}] {len(keys)} entries")

    # Save results
    results_path = os.path.join(OUTPUT_DIR, "memory_test_results.txt")
    with open(results_path, "w", encoding="utf-8") as f:
        f.write(f"Memory Test Results\n")
        f.write(f"==================\n")
        f.write(f"Passed: {passed}/{len(tests)}\n")
        f.write(f"Failed: {failed}\n")
        f.write(f"\nMemory file location: {MEMORY_PATH}\n")
    print(f"\nResults saved to: {results_path}")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
