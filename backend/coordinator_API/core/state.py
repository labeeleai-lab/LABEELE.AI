"""
core/state.py - live mutable module-level state shared across the app:
duke_brain (set by lifespan.py at startup), active_connections, LOG_FILE,
and write_log().

duke_brain staleness fix (Step 7 in the modularization plan): duke_brain is
mutated by lifespan.py at startup. Routers (and any other consumer) must
read it as a live module attribute at call time -
    import coordinator_API.core.state as state
    ...
    state.duke_brain
never
    from coordinator_API.core.state import duke_brain
which would bind a stale None captured at import time and never see
lifespan's later assignment.
"""
import os
from datetime import datetime

# Initialize as None globally; lifespan.py sets this to a real
# DukeGenerativeBrain instance at startup (or leaves it None on failure).
duke_brain = None

# Active SSE connections tracking (see routers/health.py's /api/logs/stream
# and /api/metrics/system).
active_connections = set()

# Log file path. NOTE: intentionally a bare CWD-relative literal, exactly as
# in the original file - this is a pre-existing inconsistency (elsewhere in
# the app, e.g. core/config.py's logging.basicConfig, uses an APP_DIR-based
# absolute path) that is out of scope for this migration to "fix" into
# consistency. Preserved as-is per the approved plan.
LOG_FILE = "duke_system.log"

# Ensure log file exists
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w") as f:
        f.write(f"[{datetime.now().isoformat()}] INFO: Duke System Log initialized\n")


def write_log(message: str):
    """Write log message to file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}\n"
    with open(LOG_FILE, "a") as f:
        f.write(log_line)
