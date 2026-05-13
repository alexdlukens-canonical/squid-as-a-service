import os
import sys

_base = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_base, "src"))
sys.path.insert(0, os.path.join(_base, "src", "terrasquid"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "terrasquid.settings")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
