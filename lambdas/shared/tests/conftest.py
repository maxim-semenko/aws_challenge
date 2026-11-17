import sys
from pathlib import Path

# Tests import the helper the way the packaged function does: as a top-level module `db`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
