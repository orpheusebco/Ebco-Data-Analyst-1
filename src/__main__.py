import sys
from pathlib import Path

# Ensure the package root (src/) is importable so top-level imports like
# `from api import app` resolve when launched via `python -m src`.
_SRC = str(Path(__file__).resolve().parent)
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import uvicorn

if __name__ == "__main__":
    from api import app

    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)
