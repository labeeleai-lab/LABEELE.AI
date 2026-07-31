"""
core/config.py - environment bootstrap, path resolution, logging, and the
duke_config re-exports used across the package.

APP_DIR (Finding B in the modularization plan): every `__file__`-based path
computation that used to assume `__file__` was coordinator_api.py's own
location must be rewritten to use APP_DIR instead, since that code now lives
one or two directories deeper (coordinator_API/<subpkg>/...). APP_DIR is
computed once here, relying on coordinator_API/ always being a direct child
of the directory containing coordinator_api.py in both deployments:
  - Local/GitHub layout: APP_DIR == backend/
  - Hugging Face Space (flat-copy) layout: APP_DIR == repo root
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# ==================== APP_DIR ====================
# this file:      .../coordinator_API/core/config.py
# .parent:        .../coordinator_API/
# .parent.parent: .../  (APP_DIR - backend/ locally, repo root on HF)
_PACKAGE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = _PACKAGE_DIR.parent

# Make sure APP_DIR-relative imports (tools/, duke_config.py, knowledge.py,
# etc., which live alongside coordinator_api.py in both deployments) resolve.
sys.path.append(str(APP_DIR))

# ==================== ENV LOADING ====================
# Consolidated: the original file called load_dotenv() three separate times
# (module top, mid-file duplicate import block, and again with an explicit
# env_path). A single explicit load from APP_DIR/.env covers all of them.
load_dotenv(dotenv_path=APP_DIR / ".env")

# ==================== DUKE INTEGRATION ====================
try:
    import duke_config
    print("✅ duke_config.py loaded successfully")
except ImportError:
    print("⚠️ duke_config.py not found. Using local fallback if available.")

# ==================== LOGGING & CONFIG ====================
log_path = os.path.join(str(APP_DIR), "data", "duke_system.log")
os.makedirs(os.path.dirname(log_path), exist_ok=True)  # fresh checkouts don't have data/ yet

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=log_path,  # Redirects to <APP_DIR>/data/duke_system.log
    filemode='a'
)
logger = logging.getLogger(__name__)

# ==================== GEMINI CONFIGURATION ====================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-1.5-pro"

if not GEMINI_API_KEY:
    print("=" * 70)
    print("⚠️  WARNING: GEMINI_API_KEY not set!")
    print("=" * 70)

# ==================== CONFIGURATION USING NEW SYSTEM ====================
from duke_config import (
    initialize_duke_config,
    DukePathConfig,
    TrainingLoggerManager,
    SafeFileManager,
    get_environment,
    is_production
)

# Initialize configuration
try:
    paths, training_logger = initialize_duke_config()

    # Extract commonly used paths for backward compatibility
    BASE_DIR = paths.BASE_DIR
    DB_PATH = paths.DB_PATH
    DATABASE_URL = paths.DATABASE_URL
    ASSETS_DIR = paths.ASSETS_DIR
    DUKE_CHECKPOINT_DIR = paths.DUKE_CHECKPOINT_DIR

    # Checkpoint paths
    DUKE_MODEL_BEST = paths.DUKE_MODEL_BEST
    DUKE_MODEL_LAST = paths.DUKE_MODEL_LAST
    DUKE_EMBEDDER = paths.DUKE_EMBEDDER
    DUKE_RESPONSES = paths.DUKE_RESPONSES

    # Data files
    MEMORY_FILE = paths.MEMORY_FILE
    FEEDBACK_LOG_FILE = paths.FEEDBACK_LOG_FILE
    TRAINING_LOG_FILE = paths.TRAINING_LOG_FILE

    # Service URLs
    VISION_NODE_URL = paths.VISION_NODE_URL

    # Training logger functions
    log_openai_call = training_logger.log_openai_call
    get_training_stats = training_logger.get_training_stats
    load_training_data_for_duke = training_logger.load_training_data_for_duke
    get_api_key_status = training_logger.get_api_key_status

    logger.info("✅ Configuration initialized successfully")
    logger.info(f"📍 Environment: {get_environment()}")
    logger.info(f"💾 Database: {DATABASE_URL[:50]}...")

except Exception as e:
    logger.error(f"❌ Configuration initialization failed: {e}")
    raise RuntimeError(f"Failed to initialize DUKE configuration: {e}")
