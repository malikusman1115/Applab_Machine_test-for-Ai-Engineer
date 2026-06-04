from __future__ import annotations

import json
import sys
import time
from typing import Any


def emit(event: str, **fields: Any) -> None:
    payload = {"event": event, "timestamp": time.time(), **fields}
    sys.stdout.write(json.dumps(payload, default=str, ensure_ascii=False) + "\n")
    sys.stdout.flush()
