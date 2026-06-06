import os
import re

with open("src/main.py", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "def _perform_search" in line or "def perform_search" in line or "def do_search" in line or "self.current_results" in line:
        print(f"{i+1}: {line.strip()}")
