<<<<<<< HEAD
--- START OF FILE test_enhanced_converter.py ---
=======
>>>>>>> 8413eca9f1e93d7cf1c5475af7081e74e9f08b3c
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for the enhanced HTML to Markdown converter.
<<<<<<< HEAD
Tests exact table preservation, cloze resolution, and media links.
=======
Tests complex table conversion, cloze deletion handling, and media preservation.
>>>>>>> 8413eca9f1e93d7cf1c5475af7081e74e9f08b3c
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from html_converter import convert_html_to_markdown

<<<<<<< HEAD
=======
# Test cases
>>>>>>> 8413eca9f1e93d7cf1c5475af7081e74e9f08b3c
test_cases = [
    {
        "name": "Complex Table with Clozes",
        "input": """<div><u></u><table class="table_class_basic_full_width" style="font-size: 85%; width: 100%; border-collapse: collapse; border: 1px solid;"><tbody><tr><td style="width: 33%; padding: 2px; border: 1px solid;"><br>WHAT IS GEOGRAPHY? (1:20:14)</td><td style="width: 33%; padding: 2px; border: 1px solid;">Definition &amp; History</td><td style="width: 33%; padding: 2px; border: 1px solid;"><ul>
<li>GEOGRAPHY: {{c1::Description of Earth::DiscOE}}</li>
<li>{{c1::ERATOSTHENES::E}}: Father of Geography, coined the term</li>
<li>Study of PLACES &amp; RELATIONSHIP BETWEEN PEOPLE AND THEIR ENVIRONMENT</li></ul></td></tr></tbody></table></div>""",
<<<<<<< HEAD
        "expected_highlights": ["==Description of Earth==", "==ERATOSTHENES=="],
        "expected_table": True
=======
        "expected_highlights": ["==Description of Earth==", "==ERATOSTHENES=="]
    },
    {
        "name": "Highlighted Content",
        "input": """<span style="background-color: rgb(85, 85, 255);">LITTLE AND SWAMP FOREST</span> with {{c1::MANGROVE::M}} VEGETATION""",
        "expected_highlights": ["==LITTORAL AND SWAMP FOREST==", "==MANGROVE=="]
>>>>>>> 8413eca9f1e93d7cf1c5475af7081e74e9f08b3c
    },
    {
        "name": "Media Content",
        "input": """<img src="paste-3d0da76d8d30ea27ff59b2d1b43059a6babe556f.jpg" width="115">
[sound:pronunciation.mp3]
<video src="demo.mp4"></video>""",
<<<<<<< HEAD
        "expected_media": ["![Image](paste-3d0da76d8d30ea27ff59b2d1b43059a6babe556f.jpg)", "![Audio](pronunciation.mp3)", "![Video](demo.mp4)"]
=======
        "expected_media": ["![Image](paste-3d0da76d8d30ea27ff59b2d1b43059a6babe556f.jpg)", "[Audio: pronunciation.mp3]", "[Video: demo.mp4]"]
    },
    {
        "name": "Nested Tables",
        "input": """<table><tr><td>Forest Type</td><td>{{c1::Tropical Rainforest::TR}}</td></tr><tr><td>Location</td><td><ul><li><span style="background-color: rgb(85, 85, 255);">Near Equator</span></li></ul></td></tr></table>""",
        "expected_table": True
>>>>>>> 8413eca9f1e93d7cf1c5475af7081e74e9f08b3c
    }
]

def run_tests():
<<<<<<< HEAD
    print("=" * 60)
    print("ENHANCED HTML TO MARKDOWN CONVERTER TESTS")
    print("=" * 60)
    passed, failed = 0, 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['name']}\n{'-' * 40}")
        try:
            result = convert_html_to_markdown(test["input"])
            print(f"Output:\n{result}\n")
            
            if "expected_highlights" in test:
                for expected in test["expected_highlights"]:
                    if expected in result: print(f"✓ Found highlight: {expected}")
                    else: print(f"✗ Missing highlight: {expected}"); failed += 1
            
            if "expected_media" in test:
                for expected in test["expected_media"]:
                    if expected in result: print(f"✓ Found media: {expected}")
                    else: print(f"✗ Missing media: {expected}"); failed += 1
            
            if test.get("expected_table"):
                if "<table" in result.lower(): print("✓ HTML Table protected & preserved")
                else: print("✗ Table not properly preserved"); failed += 1
                
            passed += 1
        except Exception as e:
            print(f"✗ Test failed with error: {e}")
            failed += 1
            
    print("\n" + "=" * 60 + f"\nRESULTS: {passed} passed, {failed} failed\n" + "=" * 60)

if __name__ == "__main__":
    run_tests()
--- END OF FILE test_enhanced_converter.py ---
=======
    """Run all test cases."""
    print("=" * 60)
    print("ENHANCED HTML TO MARKDOWN CONVERTER TESTS")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['name']}")
        print("-" * 40)
        
        try:
            result = convert_html_to_markdown(test["input"])
            print(f"Input (truncated): {test['input'][:100]}...")
            print(f"Output:\n{result}\n")
            
            # Check for expected highlights
            if "expected_highlights" in test:
                for expected in test["expected_highlights"]:
                    if expected in result:
                        print(f"✓ Found expected highlight: {expected}")
                    else:
                        print(f"✗ Missing expected highlight: {expected}")
                        failed += 1
                        continue
            
            # Check for expected media
            if "expected_media" in test:
                for expected in test["expected_media"]:
                    if expected in result:
                        print(f"✓ Found expected media: {expected}")
                    else:
                        print(f"✗ Missing expected media: {expected}")
                        failed += 1
                        continue
            
            # Check for table conversion
            if test.get("expected_table"):
                if "|" in result:
                    print("✓ Table converted to Markdown format")
                else:
                    print("✗ Table not properly converted")
                    failed += 1
                    continue
            
            passed += 1
            print(f"✓ Test passed")
            
        except Exception as e:
            print(f"✗ Test failed with error: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
>>>>>>> 8413eca9f1e93d7cf1c5475af7081e74e9f08b3c
