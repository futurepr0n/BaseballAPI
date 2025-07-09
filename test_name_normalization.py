#!/usr/bin/env python3
"""Test name normalization for special characters like José Ramírez"""

import sys
sys.path.append('.')

from utils import clean_player_name

# Test cases for name normalization
test_names = [
    ("Ramírez, José", "Jose Ramirez"),  # CSV format with accents
    ("José Ramírez", "Jose Ramirez"),    # Regular format with accents
    ("J. Ramírez", "J. Ramirez"),        # Initial format with accent
    ("Peña, Salvador", "Salvador Pena"), # Another example
    ("Núñez, Renato", "Renato Nunez"),   # Tilde example
    ("García, Luis", "Luis Garcia"),      # Accent example
]

print("Testing name normalization...\n")

for original, expected in test_names:
    cleaned = clean_player_name(original)
    status = "✓" if cleaned == expected else "✗"
    print(f"{status} '{original}' → '{cleaned}' (expected: '{expected}')")

print("\nTesting roster matching...")

# Simulate roster data
roster_data_list = [
    {'name': 'J. Ramirez', 'fullName': 'Jose Ramirez', 'name_cleaned': 'J. Ramirez', 'fullName_cleaned': 'Jose Ramirez'},
    {'name': 'S. Pena', 'fullName': 'Salvador Pena', 'name_cleaned': 'S. Pena', 'fullName_cleaned': 'Salvador Pena'},
]

from utils import match_player_name_to_roster

# Test matching with accented names
test_matches = [
    "J. Ramírez",  # With accent
    "J. Ramirez",  # Without accent
    "José Ramírez", # Full name with accent
    "Jose Ramirez", # Full name without accent
]

print("\nMatching results:")
for name in test_matches:
    result = match_player_name_to_roster(name, roster_data_list)
    print(f"'{name}' → {result if result else 'No match'}")

print("\n✅ Name normalization test complete!")