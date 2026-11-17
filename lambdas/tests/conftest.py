import sys
from pathlib import Path

# Tests of the build tooling in lambdas/ (package.py); not a function, never packaged.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
