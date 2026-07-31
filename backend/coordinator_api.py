"""
AICP Coordinator Service + REAL Duke Machine Learning v5.0.0
FastAPI backend + PostgreSQL + JWT + OpenAI Integration
ENHANCED: Neural network swarm with advanced coordination

Thin entry point - all real logic lives in the coordinator_API/ package
(same directory in the local/GitHub layout, flat-copied to the repo root in
the Hugging Face Space layout). See coordinator_API/app_factory.py for the
FastAPI instance, CORS, StaticFiles mount, router registration, and the
duplicate-route startup guard; coordinator_API/lifespan.py for startup/
shutdown; and coordinator_API/routers/ for every route handler.
"""
import os

from coordinator_API.app_factory import create_app
from coordinator_API.personas.specialists import SPECIALIST_PERSONAS

app = create_app()

# ==================== MAIN ENTRY POINT ====================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))

    print("╔════════════════════════════════════════════════════════════════╗")
    print("║  AICP Coordinator + REAL Duke Machine Learning v5.0.0-Phase4 ║")
    print("║        ENTERPRISE DASHBOARD + SPECIALIST PERSONAS             ║")
    print("╚════════════════════════════════════════════════════════════════╝")

    if SPECIALIST_PERSONAS:
        for key, value in SPECIALIST_PERSONAS.items():
            print(f"   │ {value.get('name', 'Unknown'):30} ⭐ ({value.get('reputation_multiplier', 1)}x) │")

    print(f"\n🚀 Starting server on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
