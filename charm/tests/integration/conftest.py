import os
import sys

# Add src to path for pytest-django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "terrasquid"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "terrasquid.settings")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
