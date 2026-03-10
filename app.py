"""
AI SOS System - Backend FastAPI Application
Wrapper that imports from AI_SOS_SYSTEM/backend
"""

import sys
import os

# Add the backend path
backend_path = os.path.join(os.path.dirname(__file__), 'AI_SOS_SYSTEM', 'backend')
sys.path.insert(0, backend_path)

# Import the main app with a different name to avoid circular import
import importlib.util
spec = importlib.util.spec_from_file_location("backend_app", os.path.join(backend_path, "app.py"))
backend_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend_module)

app = backend_module.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

