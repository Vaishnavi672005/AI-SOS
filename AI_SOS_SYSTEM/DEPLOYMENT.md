# AI SOS System - Deployment Guide

This guide covers deploying the AI SOS System (backend + mobile app) to production.

---

## Architecture Overview

```
┌─────────────────┐         ┌──────────────────┐
│   Flutter App   │────────▶│   FastAPI        │
│  (Mobile App)   │ HTTP    │   Backend        │
│                 │         │   (Render)       │
└─────────────────┘         └──────────────────┘
                                   │
                                   ▼
                            ┌──────────────────┐
                            │  Twilio SMS      │
                            │  (Alerts)        │
                            └──────────────────┘
```

---

## Part 1: Backend Deployment (Render)

### Prerequisites

1. **GitHub Account** - You'll need to push your code to GitHub
2. **Render Account** - Sign up at https://render.com

### Step 1: Prepare Backend for Deployment

The backend is already configured for deployment. The following files are needed:

```
AI_SOS_SYSTEM/backend/
├── app.py                 # FastAPI application
├── requirements.txt       # Python dependencies
├── model/
│   ├── emotion_model.h5  # Trained Keras model
│   └── label_classes.npy # Emotion labels
├── sos_alert.py          # SMS alerts (Twilio)
├── location_service.py    # GPS geocoding
└── .env.example          # Environment variables template
```

### Step 2: Push Backend to GitHub

1. Create a new GitHub repository
2. Push only the `AI_SOS_SYSTEM/backend/` folder contents:

```bash
cd AI_SOS_SYSTEM/backend/
git init
git add .
git commit -m "Initial commit - AI SOS Backend"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ai-sos-backend.git
git push -u origin main
```

> **Important**: Make sure to include these files in your GitHub repository:
> - `app.py` - FastAPI application
> - `requirements.txt` - Python dependencies
> - `runtime.txt` - Python version specification (python-3.11.0)
> - `model/` - Emotion recognition model files
> - `.env.example` - Environment variables template

### Step 3: Deploy on Render

1. **Login to Render** - Go to https://dashboard.render.com
2. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the repository you just pushed

3. **Configure the Service**
   - Name: `ai-sos-backend` (or your preferred name)
   - Region: Select closest to your users
   - Branch: `main`

4. **Build Settings**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`

5. **Add Environment Variables**
   Click "Advanced" → "Add Environment Variables":

   | Variable | Value | Description |
   |----------|-------|-------------|
   | `TWILIO_ACCOUNT_SID` | Your Twilio SID | From Twilio Console |
   | `TWILIO_AUTH_TOKEN` | Your Twilio Token | From Twilio Console |
   | `TWILIO_PHONE_NUMBER` | +1234567890 | Your Twilio phone number |
   | `EMERGENCY_CONTACT` | +1234567890 | Emergency contact phone |

6. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment to complete (3-5 minutes)
   - Note your service URL (e.g., `https://ai-sos-backend.onrender.com`)

### Step 4: Verify Backend is Working

Visit your health check endpoint:
```
https://your-service-name.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "services": {
    "emotion_recognition": true,
    "distress_detection": true,
    "sos_alerts": true,
    "location_service": true
  }
}
```

---

## Part 2: Mobile App Configuration

### Step 1: Update Backend URL

Edit `AI_SOS_SYSTEM/mobile app/sos_app/lib/sos_service.dart`:

```dart
// Set this to true when deploying to production
static const bool isProduction = true;

// Replace with your Render URL
static const String productionUrl = "https://your-app-name.onrender.com";
```

### Step 2: Build the App

```bash
cd AI_SOS_SYSTEM/mobile app/sos_app

# Get dependencies
flutter pub get

# Build for Android
flutter build apk --release

# Build for iOS
flutter build ios --release
```

---

## Part 3: Twilio Setup (Optional but Recommended)

### Why Twilio?

Twilio enables the app to send SMS alerts to emergency contacts when distress is detected.

### Setup Steps

1. **Create Twilio Account**
   - Go to https://www.twilio.com
   - Sign up for a free account

2. **Get Credentials**
   - Account SID (from console)
   - Auth Token (from console)
   - Phone Number (buy a number)

3. **Add to Render**
   - Add the environment variables as shown above

4. **Test**
   - Use the `/test-alert` endpoint:
   ```
   POST https://your-service.onrender.com/test-alert
   Content-Type: application/x-www-form-url
   
   latitude=37.7749
   longitude=-122.4194
   ```

---

## Part 4: Docker Deployment (Recommended)

### Prerequisites

1. **Docker** - Install Docker Desktop from https://www.docker.com

### Quick Start with Docker Compose

1. **Copy environment file:**
```bash
cp env.example .env
# Edit .env with your Twilio credentials
```

2. **Build and run:**
```bash
docker-compose up --build
```

3. **Test the API:**
```bash
curl http://localhost:8000/health
```

### Manual Docker Build

If you prefer to build manually:

```bash
# Build the image
docker build -t ai-sos-backend .

# Run the container
docker run -p 8000:8000 \
  --env TWILIO_ACCOUNT_SID=your_sid \
  --env TWILIO_AUTH_TOKEN=your_token \
  --env TWILIO_PHONE_NUMBER=+1234567890 \
  --env EMERGENCY_CONTACT=+1234567890 \
  ai-sos-backend
```

### Docker Commands

| Command | Description |
|---------|-------------|
| `docker-compose up --build` | Build and start services |
| `docker-compose down` | Stop services |
| `docker-compose up -d` | Run in background |
| `docker-compose logs -f` | View logs |
| `docker-compose restart` | Restart services |
| `docker exec -it ai-sos-system-backend-1 bash` | Shell into container |

---

## API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root endpoint |
| `/health` | GET | Health check |
| `/predict-emotion` | POST | Analyze audio for emotion |
| `/analyze-batch` | POST | Analyze multiple audio files |
| `/trigger-sos` | POST | Manual SOS trigger |
| `/test-alert` | POST | Test alert system |
| `/model-info` | GET | Get model information |
| `/location/{lat}/{lon}` | GET | Reverse geocoding |

---

## Troubleshooting

### Common Issues

1. **Model not loading**
   - Ensure `emotion_model.h5` and `label_classes.npy` are in the `model/` folder
   - Check build logs on Render

2. **SMS not sending**
   - Verify Twilio credentials in environment variables
   - Check that phone numbers are in E.164 format (+1...)

3. **CORS errors in mobile app**
   - The FastAPI app doesn't have CORS configured for production
   - Add `fastapi.middleware.cors` if needed

4. **Audio upload fails**
   - Check file size limit (max ~10MB)
   - Ensure audio is in WAV or MP3 format

### Environment Variables Summary

| Variable | Required | Description |
|----------|----------|-------------|
| `TWILIO_ACCOUNT_SID` | No* | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | No* | Twilio Auth Token |
| `TWILIO_PHONE_NUMBER` | No* | Twilio phone number |
| `EMERGENCY_CONTACT` | No* | Emergency contact |
| `GEOCODING_API_KEY` | No | OpenCage API (optional) |

*Required only if you want SMS alerts. The app works without Twilio but won't send SMS.

---

## Security Notes

1. **Never commit `.env` files** - They're already in `.gitignore`
2. **Use environment variables** - Never hardcode credentials in code
3. **HTTPS** - Always use HTTPS in production
4. **Rate limiting** - Consider adding rate limiting for production

---

## Next Steps

After deployment:

1. Test the entire flow locally first
2. Deploy backend to Render
3. Update Flutter app with production URL
4. Build and distribute the app
5. Monitor logs on Render dashboard

---

## Support

For issues with:
- **Backend**: Check Render logs at https://dashboard.render.com
- **Twilio**: Visit https://console.twilio.com
- **Flutter**: Check Flutter documentation

