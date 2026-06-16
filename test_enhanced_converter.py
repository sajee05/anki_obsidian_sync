--- START OF FILE test_enhanced_converter.py ---
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for the enhanced HTML to Markdown converter.
Tests exact table preservation, cloze resolution, and media links.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from html_converter import convert_html_to_markdown

test_cases = [
    {
        "name": "Complex Table with Clozes",
        "input": """<div><u></u><table class="table_class_basic_full_width" style="font-size: 85%; width: 100%; border-collapse: collapse; border: 1px solid;"><tbody><tr><td style="width: 33%; padding: 2px; border: 1px solid;"><br>WHAT IS GEOGRAPHY? (1:20:14)</td><td style="width: 33%; padding: 2px; border: 1px solid;">Definition &amp; History</td><td style="width: 33%; padding: 2px; border: 1px solid;"><ul>
<li>GEOGRAPHY: {{c1::Description of Earth::DiscOE}}</li>
<li>{{c1::ERATOSTHENES::E}}: Father of Geography, coined the term</li>
<li>Study of PLACES &amp; RELATIONSHIP BETWEEN PEOPLE AND THEIR ENVIRONMENT</li></ul></td></tr></tbody></table></div>""",
        "expected_highlights": ["==Description of Earth==", "==ERATOSTHENES=="],
        "expected_table": True
    },
    {
        "name": "Media Content",
        "input": """<img src="paste-3d0da76d8d30ea27ff59b2d1b43059a6babe556f.jpg" width="115">
[sound:pronunciation.mp3]
<video src="demo.mp4"></video>""",
        "expected_media": ["![Image](paste-3d0da76d8d30ea27ff59b2d1b43059a6babe556f.jpg)", "![Audio](pronunciation.mp3)", "![Video](demo.mp4)"]
    }
]

def run_tests():
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