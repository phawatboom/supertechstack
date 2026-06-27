from pathlib import Path
import sys


API_ROOT = Path(__file__).resolve().parents[1]
api_root_path = str(API_ROOT)

if api_root_path not in sys.path:
    sys.path.insert(0, api_root_path)
