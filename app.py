"""
AI SOS System - Backend FastAPI Application
Wrapper that imports from AI_SOS_SYSTEM/backend
"""

import sys
import os

# Add the backend path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AI_SOS_SYSTEM', 'backend'))

# Import the main app
from app import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

