import sys
from pathlib import Path

# Add src to sys.path so tests can import calculator without installation
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from calculator.core import add, multiply

def test_add():
    assert add(2, 2) == 4, f"Expected 4, got {add(2, 2)}"

def test_multiply():
    assert multiply(3, 4) == 12
