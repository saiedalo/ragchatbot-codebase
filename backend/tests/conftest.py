import sys
import os

# Add the backend directory to sys.path so modules import without package prefix
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
