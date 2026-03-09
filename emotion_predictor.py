"""
Emotion Predictor Module
Ultra-aggressive emotion detection for reliable results
"""

import os
import numpy as np
import librosa

class EmotionPredictor:
    """
    Emotion recognition using audio feature analysis.
    Optimized for aggressive emotion detection.
    """
    
    def __init__(self, model_path=None, labels_path=None):
        self.model_path = model_path
        self.labels_path = labels_path
        self.label_classes = np.array([
            'angry', 'disgust', 'fear', 'happy', 
            'neutral', 'pleasant_surprise', 'sad'
        ])
        print("Emotion predictor initialized (ultra-aggressive mode)")
    
    def predict(self, audio_path):
        return self._audio_based_predict(audio_path)
    
    def _audio_based_predict(self, audio_path):
        """
        Ultra-aggressive emotion prediction.
        """
        try:
            # Load audio
            y, sr = librosa.load(audio_path, sr=22050, duration=3)
            
            # Ensure we have enough audio
            if len(y) < sr * 0.5:
                return "neutral", 0.3
            
            # Extract features
            features = self._extract_features(y, sr)
            
            # Classify based on features
            emotion, confidence = self._classify_emotion(features)
            
            print(f"Prediction: {emotion} ({confidence:.2f})")
            print(f"  Energy: {features['energy']:.3f}, Pitch: {features.get('pitch', 150):.0f}Hz")
            
            return emotion, confidence
            
        except Exception as e:
            print(f"Error: {e}")
            return "neutral", 0.5
    
    def _extract_features(self, y, sr):
        """Extract audio features."""
        features = {}
        
        # Energy (RMS)
        rms = librosa.feature.rms(y=y)[0]
        features['energy'] = np.mean(rms)
        features['energy_std'] = np.std(rms)
        features['energy_max'] = np.max(rms)
        
        # Zero Crossing Rate
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        features['zcr'] = np.mean(zcr)
        features['zcr_std'] = np.std(zcr)
        
        # Pitch using pyin
        try:
            pitches, voiced_probs, voiced_frames = librosa.pyin(
                y, fmin=50, fmax=500, sr=sr
            )
            valid_pitches = pitches[~np.isnan(pitches)]
            if len(valid_pitches) > 0:
                features['pitch'] = np.mean(valid_pitches)
                features['pitch_std'] = np.std(valid_pitches)
            else:
                features['pitch'] = 150
                features['pitch_std'] = 30
        except:
            features['pitch'] = 150
            features['pitch_std'] = 30
        
        # Spectral features
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        features['spectral_centroid'] = np.mean(spectral_centroid)
        
        # MFCC
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        features['mfcc_mean'] = np.mean(mfcc, axis=1)
        
        # Intensity variation
        features['intensity_var'] = np.var(rms) / (np.mean(rms) + 1e-10)
        
        return features
    
    def _classify_emotion(self, f):
        """Classify emotion with aggressive scoring."""
        
        energy = f['energy']
        pitch = f.get('pitch', 150)
        pitch_std = f.get('pitch_std', 30)
        zcr = f['zcr']
        intensity_var = f.get('intensity_var', 0)
        spectral_centroid = f.get('spectral_centroid', 2000)
        
        # DEBUG: Print raw features
        print(f"DEBUG: energy={energy:.4f}, pitch={pitch:.1f}, zcr={zcr:.4f}, intensity_var={intensity_var:.4f}")
        
        # Normalize pitch
        pitch = max(50, min(400, pitch))
        
        # Calculate scores with LOWER thresholds for more detections
        scores = {}
        
        # ANGRY: High energy OR high pitch OR high zcr
        angry = 0
        if energy > 0.03:  # Lowered from 0.05
            angry += 0.4
        if energy > 0.06:
            angry += 0.3
        if pitch > 150:  # Lowered from 170
            angry += 0.3
        if zcr > 0.04:  # Lowered from 0.06
            angry += 0.2
        if intensity_var > 0.2:  # Lowered from 0.3
            angry += 0.2
        scores['angry'] = min(angry, 1.0)
        
        # FEAR: High pitch variation OR high pitch OR variable energy
        fear = 0
        if pitch > 180:  # Lowered from 200
            fear += 0.4
        if pitch_std > 40:  # Lowered from 80
            fear += 0.3
        if intensity_var > 0.25:  # Lowered from 0.4
            fear += 0.3
        if zcr > 0.05:  # Lowered from 0.08
            fear += 0.2
        if energy < 0.07:
            fear += 0.1
        scores['fear'] = min(fear, 1.0)
        
        # SAD: Low energy OR low pitch
        sad = 0
        if energy < 0.03:  # Lowered from 0.04
            sad += 0.5
        if energy < 0.05:
            sad += 0.2
        if pitch < 170:  # Lowered from 180
            sad += 0.3
        if pitch < 140:  # Lowered from 160
            sad += 0.2
        if zcr < 0.04:  # Lowered from 0.05
            sad += 0.2
        scores['sad'] = min(sad, 1.0)
        
        # HAPPY: Medium energy + normal pitch + regular
        happy = 0
        if energy > 0.02:  # Very low threshold
            happy += 0.3
        if 120 < pitch < 300:
            happy += 0.4
        if intensity_var < 0.3:  # Lowered from 0.25
            happy += 0.3
        if spectral_centroid > 1500:  # Lowered from 2000
            happy += 0.2
        scores['happy'] = min(happy, 1.0)
        
        # DISGUST: Irregular patterns
        disgust = 0
        if intensity_var > 0.2:  # Lowered from 0.35
            disgust += 0.4
        if zcr > 0.05:  # Lowered from 0.07
            disgust += 0.3
        if energy < 0.05:
            disgust += 0.3
        scores['disgust'] = min(disgust, 1.0)
        
        # PLEASANT SURPRISE: High energy + high pitch
        surprise = 0
        if energy > 0.04:  # Lowered from 0.08
            surprise += 0.4
        if pitch > 200:  # Lowered from 220
            surprise += 0.4
        if intensity_var > 0.2:  # Lowered from 0.3
            surprise += 0.3
        scores['pleasant_surprise'] = min(surprise, 1.0)
        
        # NEUTRAL: Only if nothing else scores high
        neutral = 0.2
        if 0.01 < energy < 0.06:
            neutral += 0.2
        if 100 < pitch < 220:
            neutral += 0.2
        if intensity_var < 0.15:
            neutral += 0.2
        scores['neutral'] = min(neutral, 0.8)
        
        # DEBUG: Print all scores
        print(f"DEBUG SCORES: {scores}")
        
        # Find best match
        best_emotion = max(scores, key=scores.get)
        confidence = scores[best_emotion]
        
        # If neutral is winning but confidence is low, pick second best
        if best_emotion == 'neutral' and confidence < 0.5:
            sorted_emotions = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            if len(sorted_emotions) > 1:
                best_emotion = sorted_emotions[1][0]
                confidence = sorted_emotions[1][1]
        
        # Ensure minimum confidence
        confidence = max(confidence, 0.4)
        
        return best_emotion, confidence
    
    def predict_batch(self, audio_paths):
        results = []
        for audio_path in audio_paths:
            result = self.predict(audio_path)
            results.append(result)
        return results
    
    def get_model_summary(self):
        return "Ultra-aggressive audio feature analysis"


def quick_predict(audio_path, model_path=None, labels_path=None):
    predictor = EmotionPredictor(model_path, labels_path)
    return predictor.predict(audio_path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        emotion, confidence = quick_predict(sys.argv[1])
        print(f"Emotion: {emotion}, Confidence: {confidence}")
    else:
        print("Usage: python emotion_predictor.py <audio_file>")
