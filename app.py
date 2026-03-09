"""
AI SOS System - Backend FastAPI Application
Speech Emotion Recognition and SOS Alert System
"""

import os
import numpy as np
import librosa
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

# Import local modules
from feature_extraction import extract_mfcc_features
from emotion_predictor import EmotionPredictor
from distress_logic import DistressDetector
from sos_alert import SOSAlertManager
from location_service import LocationService

# ============================================
# Configuration
# ============================================
app = FastAPI(
    title="AI SOS System API",
    description="Speech Emotion Recognition and SOS Alert System",
    version="1.0.0"
)

# Add CORS middleware to allow mobile app connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model", "emotion_model.h5")
LABELS_PATH = os.path.join(os.path.dirname(__file__), "model", "label_classes.npy")

# Global predictor (loaded once)
predictor = None
distress_detector = None
sos_manager = None
location_service = None

# ============================================
# Startup Event
# ============================================
@app.on_event("startup")
async def startup_event():
    """Initialize models and services on startup."""
    global predictor, distress_detector, sos_manager, location_service
    
    print("Initializing emotion recognition (audio analysis)...")
    predictor = EmotionPredictor(MODEL_PATH, LABELS_PATH)
    
    print("Initializing distress detector...")
    distress_detector = DistressDetector()
    
    print("Initializing SOS alert manager...")
    sos_manager = SOSAlertManager()
    
    print("Initializing location service...")
    location_service = LocationService()
    
    print("AI SOS System ready!")

# ============================================
# Root Endpoint
# ============================================
@app.get("/")
async def root():
    """Root endpoint - returns API status."""
    return {
        "status": "online",
        "service": "AI SOS System",
        "version": "1.0.0",
        "message": "Speech Emotion Recognition API is running"
    }

# ============================================
# Health Check Endpoint
# ============================================
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model_loaded": predictor is not None,
        "services": {
            "emotion_recognition": predictor is not None,
            "distress_detection": distress_detector is not None,
            "sos_alerts": sos_manager is not None,
            "location_service": location_service is not None
        }
    }

# ============================================
# Emotion Recognition Endpoint (alias for /predict)
# ============================================
@app.post("/predict")
@app.post("/predict-emotion")
async def predict_emotion(
    audio: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None)
):
    """
    Analyze audio file for emotion recognition.
    
    Args:
        audio: Audio file (wav, mp3, etc.)
        latitude: Optional GPS latitude
        longitude: Optional GPS longitude
    
    Returns:
        Emotion prediction results
    """
    try:
        # Save uploaded file temporarily
        temp_audio_path = f"temp_{audio.filename}"
        with open(temp_audio_path, "wb") as f:
            content = await audio.read()
            f.write(content)
        
        # Extract features and predict
        emotion, confidence = predictor.predict(temp_audio_path)
        
        # Check for distress
        is_distress = distress_detector.is_distress(emotion, confidence)
        
        # Get location if provided
        location = None
        if latitude and longitude:
            location = {
                "latitude": latitude,
                "longitude": longitude,
                "address": location_service.get_address(latitude, longitude)
            }
        
        # Prepare response
        result = {
            "emotion": emotion,
            "confidence": float(confidence),
            "is_distress": is_distress,
            "location": location
        }
        
        # Trigger SOS if distress detected
        if is_distress and location:
            sos_alert = await sos_manager.trigger_alert(
                emotion=emotion,
                confidence=confidence,
                location=location
            )
            result["sos_triggered"] = True
            result["sos_alert"] = sos_alert
        else:
            result["sos_triggered"] = False
        
        # Clean up temp file
        os.remove(temp_audio_path)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

# ============================================
# Batch Emotion Analysis
# ============================================
@app.post("/analyze-batch")
async def analyze_batch(
    audio_files: list[UploadFile] = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None)
):
    """
    Analyze multiple audio files for emotion patterns.
    
    Returns aggregated distress analysis.
    """
    try:
        results = []
        
        for audio in audio_files:
            temp_path = f"temp_{audio.filename}"
            with open(temp_path, "wb") as f:
                content = await audio.read()
                f.write(content)
            
            emotion, confidence = predictor.predict(temp_path)
            is_distress = distress_detector.is_distress(emotion, confidence)
            
            results.append({
                "file": audio.filename,
                "emotion": emotion,
                "confidence": float(confidence),
                "is_distress": is_distress
            })
            
            os.remove(temp_path)
        
        # Aggregate results
        distress_count = sum(1 for r in results if r["is_distress"])
        avg_confidence = np.mean([r["confidence"] for r in results])
        
        return JSONResponse(content={
            "individual_results": results,
            "summary": {
                "total_files": len(results),
                "distress_count": distress_count,
                "average_confidence": float(avg_confidence),
                "overall_distress": distress_count > len(results) / 2
            }
        })
        
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

# ============================================
# Manual SOS Alert
# ============================================
@app.post("/trigger-sos")
async def trigger_sos(
    latitude: float = Form(...),
    longitude: float = Form(...),
    message: Optional[str] = Form(None)
):
    """Trigger manual SOS alert with current location."""
    try:
        location = {
            "latitude": latitude,
            "longitude": longitude,
            "address": location_service.get_address(latitude, longitude)
        }
        
        alert = await sos_manager.trigger_alert(
            emotion="manual",
            confidence=1.0,
            location=location,
            message=message
        )
        
        return JSONResponse(content=alert)
        
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

# ============================================
# Test Alert Endpoint
# ============================================
@app.post("/test-alert")
async def test_alert(
    latitude: float = Form(...),
    longitude: float = Form(...)
):
    """
    Test the alert system with given coordinates.
    
    Args:
        latitude: GPS latitude
        longitude: GPS longitude
    
    Returns:
        Test alert result
    """
    try:
        # Get location info
        location = {
            "latitude": latitude,
            "longitude": longitude,
            "address": location_service.get_address(latitude, longitude)
        }
        
        # Trigger test alert
        alert = await sos_manager.trigger_alert(
            emotion="test",
            confidence=1.0,
            location=location,
            message="This is a TEST alert to verify the SOS system is working."
        )
        
        return JSONResponse(content={
            "status": "test_alert_sent",
            "alert": alert,
            "location": location
        })
        
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

# ============================================
# Get Model Info
# ============================================
@app.get("/model-info")
async def model_info():
    """Get information about the emotion recognition model."""
    return {
        "model_type": "audio_feature_analysis",
        "sample_rate": 22050,
        "duration_seconds": 3,
        "n_mfcc": 40,
        "supported_emotions": [
            "angry", "disgust", "fear", "happy", 
            "neutral", "pleasant_surprise", "sad"
        ]
    }

# ============================================
# Location Lookup
# ============================================
@app.get("/location/{latitude}/{longitude}")
async def get_location(latitude: float, longitude: float):
    """Reverse geocode coordinates to address."""
    try:
        address = location_service.get_address(latitude, longitude)
        return {
            "latitude": latitude,
            "longitude": longitude,
            "address": address
        }
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
