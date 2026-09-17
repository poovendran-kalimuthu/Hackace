"""
Convenience launcher for DocuCraft
"""
import os
import sys

base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docucraft")
sys.path.insert(0, base_dir)

from docucraft.main import main

if __name__ == "__main__":
    main()
