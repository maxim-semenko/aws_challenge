import sys
from pathlib import Path

# Same import layout as the packaged zip: the function module and the shared helpers are top-level modules.
# lambdas/shared/tests holds the shared test doubles (bedrock_stub); it is never packaged.
FUNCTION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FUNCTION_DIR.parent / "shared" / "tests"))
sys.path.insert(0, str(FUNCTION_DIR.parent / "shared"))
sys.path.insert(0, str(FUNCTION_DIR))
