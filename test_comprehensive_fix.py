#!/usr/bin/env python3
"""Test comprehensive name normalization fix"""

import sys
sys.path.append('.')

from utils import clean_player_name

def test_comprehensive_normalization():
    """Test bulletproof name normalization"""
    
    print("Testing Comprehensive Name Normalization...\n")
    
    # Test cases for José Ramírez
    test_cases = [
        ("José Ramírez", "Jose Ramirez"),        # Full name with accents
        ("Ramírez, José", "Jose Ramirez"),       # CSV format with accents
        ("J. Ramírez", "J Ramirez"),             # Initial with accent
        ("Peña, Salvador", "Salvador Pena"),     # Tilde
        ("Núñez, Renato", "Renato Nunez"),       # Tilde
        ("García, Luis", "Luis Garcia"),         # Accent
        ("Müller, Hans", "Hans Muller"),         # Umlaut
        ("Åberg, Erik", "Erik Aberg"),           # Scandinavian
    ]
    
    print("Basic normalization tests:")
    for original, expected in test_cases:
        result = clean_player_name(original)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{original}' → '{result}' (expected: '{expected}')")
    
    print("\nRoster.json compatibility test:")
    # This simulates what we expect to find in rosters.json
    roster_names = ["Jose Ramirez", "Salvador Pena", "Luis Garcia"]
    csv_names = ["Ramírez, José", "Peña, Salvador", "García, Luis"]
    
    for csv_name in csv_names:
        normalized = clean_player_name(csv_name)
        found_match = False
        for roster_name in roster_names:
            if normalized.lower() == roster_name.lower():
                print(f"✅ CSV '{csv_name}' → '{normalized}' matches roster '{roster_name}'")
                found_match = True
                break
        if not found_match:
            print(f"❌ CSV '{csv_name}' → '{normalized}' has no roster match")

    print("\n✅ Comprehensive normalization test complete!")

if __name__ == "__main__":
    test_comprehensive_normalization()