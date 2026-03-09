"""
Emotion Predictor Module
Loads the trained model and makes predictions
Uses audio feature analysis as fallback when model fails
"""

import os
import numpy as np
from tensorflow.keras.models import load_model
import pickle

class EmotionPredictor:
    """
    Emotion recognition predictor using trained neural network model.
    Falls back to audio feature analysis when model is not available.
    """
    
    def __init__(self, model_path, labels_path):
        """
        Initialize the emotion predictor.
        
        Args:
            model_path: Path to the trained model (.h5 file)
            labels_path: Path to the label classes file (.npy file)
        """
        self.model_path = model_path
        self.labels_path = labels_path
        self.model = None
        self.label_classes = None
        
        self._load_model()
        self._load_labels()
    
    def _load_model(self):
        """Load the trained Keras model."""
        try:
            if os.path.exists(self.model_path):
                self.model = load_model(self.model_path)
                print(f"Model loaded from {self.model_path}")
            else:
                print(f"Warning: Model not found at {self.model_path}")
                print("Using audio feature analysis for emotion detection")
                self.model = None
        except Exception as e:
            print(f"Error loading model: {e}")
            print("Using audio feature analysis for emotion detection")
            self.model = None
    
    def _load_labels(self):
        """Load the label classes."""
        try:
            if os.path.exists(self.labels_path):
                self.label_classes = np.load(self.labels_path, allow_pickle=True)
                print(f"Labels loaded: {self.label_classes}")
            else:
                print(f"Warning: Labels not found at {self.labels_path}")
                # Default emotion labels
                self.label_classes = np.array([
                    'angry', 'disgust', 'fear', 'happy', 
                    'neutral', 'pleasant_surprise', 'sad'
                ])
        except Exception as e:
            print(f"Error loading labels: {e}")
            self.label_classes = np.array([
                'angry', 'disgust', 'fear', 'happy', 
                'neutral', 'pleasant_surprise', 'sad'
            ])
    
    def predict(self, audio_path):
        """
        Predict emotion from an audio file.
        
        Args:
            audio_path: Path to the audio file
        
        Returns:
            tuple: (predicted_emotion, confidence)
        """
        # Import feature extraction
        from feature_extraction import extract_mfcc_features, extract_all_features
        
        # Extract features
        features = extract_mfcc_features(audio_path)
        
        if features is None:
            return "unknown", 0.0
        
        # Prepare features for model
        features = np.expand_dims(features, axis=0)
        
        # Make prediction
        if self.model is not None:
            try:
                prediction = self.model.predict(features, verbose=0)
                predicted_class = np.argmax(prediction[0])
                confidence = np.max(prediction[0])
                
                emotion = self.label_classes[predicted_class]
                return emotion, confidence
            except Exception as e:
                print(f"Prediction error: {e}")
                return self._audio_based_predict(audio_path)
        else:
            return self._audio_based_predict(audio_path)
    
    def _audio_based_predict(self, audio_path):
        """
        Audio feature-based emotion prediction.
        Analyzes audio characteristics to determine emotion.
        """
        try:
            import librosa
            
            # Load audio
            y, sr = librosa.load(audio_path, sr=22050, duration=3)
            
            # Extract various audio features
            # 1. RMS energy (volume)
            rms = librosa.feature.rms(y=y)[0]
            rms_mean = np.mean(rms)
            rms_std = np.std(rms)
            
            # 2. Zero crossing rate (speech characteristics)
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            zcr_mean = np.mean(zcr)
            zcr_std = np.std(zcr)
            
            # 3. Spectral centroid (brightness/timbre)
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            sc_mean = np.mean(spectral_centroid)
            
            # 4. Pitch/frequency analysis
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
            pitch_values = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_values.append(pitch)
            
            pitch_mean = np.mean(pitch_values) if pitch_values else 0
            pitch_std = np.std(pitch_values) if pitch_values else 0
            
            # 5. MFCC for voice characteristics
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            mfcc_mean = np.mean(mfcc, axis=1)
            
            # Analyze features to determine emotion
            # High energy + high pitch variation + fast speech = Angry/Fear
            # Low energy + low pitch + slow speech = Sad
            # High energy + high pitch + regular rhythm = Happy
            # Medium energy + neutral pitch = Neutral
            
            # Calculate emotion scores
            scores = {
                'angry': 0.0,
                'fear': 0.0,
                'sad': 0.0,
                'happy': 0.0,
                'neutral': 0.0,
                'disgust': 0.0,
                'pleasant_surprise': 0.0
            }
            
            # Angry: High energy, high pitch, high zcr
            if rms_mean > 0.1:
                scores['angry'] += 0.3
            if pitch_mean > 200:
                scores['angry'] += 0.2
            if zcr_mean > 0.1:
                scores['angry'] += 0.2
            
            # Fear: High pitch, irregular speech
            if pitch_mean > 250:
                scores['fear'] += 0.3
            if pitch_std > 100:
                scores['fear'] += 0.2
            if rms_std > 0.1:
                scores['fear'] += 0.2
            
            # Sad: Low energy, low pitch, slow speech
            if rms_mean < 0.05:
                scores['sad'] += 0.4
            if pitch_mean < 150:
                scores['sad'] += 0.2
            if zcr_mean < 0.05:
                scores['sad'] += 0.2
            
            # Happy: High energy, medium-high pitch, regular
            if rms_mean > 0.08:
                scores['happy'] += 0.3
            if 150 < pitch_mean < 300:
                scores['happy'] += 0.2
            if zcr_std < 0.05:
                scores['happy'] += 0.2
            
            # Neutral: Medium energy, normal pitch
            if 0.03 < rms_mean < 0.1:
                scores['neutral'] += 0.3
            if 100 < pitch_mean < 250:
                scores['neutral'] += 0.3
            
            # Disgust: Similar to angry but with more irregularity
            if rms_std > 0.15:
                scores['disgust'] += 0.3
            
            # Pleasant surprise: High energy with rising pitch pattern
            if rms_mean > 0.12:
                scores['pleasant_surprise'] += 0.2
            
            # Normalize scores and find best match
            total_score = sum(scores.values())
            if total_score > 0:
                for emotion in scores:
                    scores[emotion] /= total_score
            
            # Get the emotion with highest score
            best_emotion = max(scores, key=scores.get)
            confidence = scores[best_emotion]
            
            # Ensure minimum confidence
            if confidence < 0.3:
                confidence = 0.3
            
            print(f"Audio-based prediction: {best_emotion} (confidence: {confidence:.2f})")
            print(f"  Energy: {rms_mean:.3f}, Pitch: {pitch_mean:.1f}Hz, ZCR: {zcr_mean:.3f}")
            
            return best_emotion, confidence
            
        except Exception as e:
            print(f"Audio analysis error: {e}")
            # Ultimate fallback
            return "neutral", 0.5
    
    def _fallback_predict(self, features):
        """
        Fallback prediction when model is not available.
        """
        return "neutral", 0.5
    
    def predict_batch(self, audio_paths):
        """
        Predict emotions for multiple audio files.
        
        Args:
            audio_paths: List of paths to audio files
        
        Returns:
            List of tuples: [(emotion, confidence), ...]
        """
        results = []
        for audio_path in audio_paths:
            result = self.predict(audio_path)
            results.append(result)
        return results
    
    def get_model_summary(self):
        """Get model architecture summary."""
        if self.model is not None:
            return self.model.summary()
        return "Model not loaded - using audio feature analysis"


# Helper function for direct prediction
def quick_predict(audio_path, model_path, labels_path):
    """
    Quick prediction function for single audio file.
    
    Args:
        audio_path: Path to audio file
        model_path: Path to model
        labels_path: Path to labels
    
    Returns:
        tuple: (emotion, confidence)
    """
    predictor = EmotionPredictor(model_path, labels_path)
    return predictor.predict(audio_path)


if __name__ == "__main__":
    # Test the predictor
    import sys
    
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        model_path = "model/emotion_model.h5"
        labels_path = "model/label_classes.npy"
        
        emotion, confidence = quick_predict(audio_file, model_path, labels_path)
        print(f"Emotion: {emotion}, Confidence: {confidence}")
    else:
        print("Usage: python emotion_predictor.py <audio_file>")
