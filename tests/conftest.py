"""Keep pytest's implicit runtime databases and generated files out of the checkout."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


_test_runtime = tempfile.TemporaryDirectory(prefix="autoprofit-pytest-")
_test_runtime_path = Path(_test_runtime.name)
os.environ.setdefault("AUTOPROFIT_DATA_DIR", str(_test_runtime_path / "backend-data"))
os.environ.setdefault("AUTOPROFIT_APPS_DIR", str(_test_runtime_path / "generated-apps"))
