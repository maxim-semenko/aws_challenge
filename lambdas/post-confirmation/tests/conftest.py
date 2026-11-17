import sys
from pathlib import Path

# Same import layout as the packaged zip: the function module and the shared helper are top-level modules.
FUNCTION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FUNCTION_DIR.parent / "shared"))
sys.path.insert(0, str(FUNCTION_DIR))
