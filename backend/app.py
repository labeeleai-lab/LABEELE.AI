"""
Duke Enterprise Entry Point (Upgraded)
This file bridges the Uvicorn server to the 'coordinator_api.py' logic.
It includes enhanced error handling and path debugging for Cloud deployment.
"""
import sys
import os
import logging

# 1. Configure Enterprise Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("DukeBridge")

# 2. Configure Pathing (Critical for Imports)
# We ensure both the 'backend' folder and the 'root' folder are visible to Python
current_dir = os.path.dirname(os.path.abspath(__file__)) # .../backend
parent_dir = os.path.dirname(current_dir)                # .../ (Root)

if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

logger.info(f"🔧 Duke Bridge Initialized.")
logger.info(f"📂 Execution Context: {current_dir}")

# 3. Import the Core Application
try:
    # Attempt to import the main application instance
    # This triggers the loading of the Duke Brain, DB, and Agent Toolkit
    from backend.coordinator_api import app
    logger.info("✅ Successfully loaded 'app' from backend.coordinator_api")

except ImportError as e:
    logger.warning(f"⚠️ Direct import failed: {e}. Attempting fallback...")
    
    # Fallback for different directory structures (common in Docker)
    try:
        from coordinator_api import app
        logger.info("✅ Successfully loaded 'app' from coordinator_api (Local Context)")
    except ImportError as e2:
        logger.error("❌ CRITICAL ERROR: Could not import Duke App Logic.")
        logger.error(f"   Attempt 1 error: {e}")
        logger.error(f"   Attempt 2 error: {e2}")
        logger.error(f"   Current sys.path: {sys.path}")
        # Re-raise so the deployment fails visibly rather than silently
        raise e2

# 4. Launch Logic (For local debugging)
if __name__ == "__main__":
    import uvicorn
    # Use the PORT environment variable if available (Good practice for Cloud)
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 Launching Uvicorn on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)