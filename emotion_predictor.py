"""
Emotion Predictor Module
Improved audio feature analysis for emotion detection
"""

import os
import numpy as np
import librosa
from scipy import stats

class EmotionPredictor:
    """
    Emotion recognition using audio feature analysis.
    """
    
    def __init__(self, model_path=None, labels_path=None):
        self.model_path = model_path
        self.labels_path = labels_path
        self.label_classes = np.array([
            'angry', 'disgust', 'fear', 'happy', 
            'neutral', 'pleasant_surprise', 'sad'
        ])
        print("Emotion predictor initialized (improved audio analysis)")
    
    def predict(self, audio_path):
        return self._audio_based_predict(audio_path)
    
    def _audio_based_predict(self, audio_path):
        """
        Improved audio feature-based emotion prediction.
        """
        try:
            # Load audio
            y, sr = librosa.load(audio_path, sr=22050, duration=3)
            
            # Ensure we have enough audio
            if len(y) < sr * 0.5:  # Less than 0.5 seconds
                return "neutral", 0.3
            
            # Extract features
            features = self._extract_features(y, sr)
            
            # Classify based on features
            emotion, confidence = self._classify_emotion(features)
            
            print(f"Prediction: {emotion} ({confidence:.2f})")
            print(f"  Energy: {features['energy']:.3f}, Pitch: {features['pitch']:.0f}Hz, "
                  f"Speech rate: {features['speech_rate']:.1f}")
            
            return emotion, confidence
            
        except Exception as e:
            print(f"Error: {e}")
            return "neutral", 0.5
    
    def _extract_features(self, y, sr):
        """Extract comprehensive audio features."""
        features = {}
        
        # 1. Energy (RMS)
        rms = librosa.feature.rms(y=y)[0]
        features['energy'] = np.mean(rms)
        features['energy_std'] = np.std(rms)
        features['energy_max'] = np.max(rms)
        
        # 2. Zero Crossing Rate (speech rate indicator)
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        features['zcr'] = np.mean(zcr)
        features['zcr_std'] = np.std(zcr)
        
        # 3. Pitch estimation using autocorrelation
        try:
            # Simple pitch detection via autocorrelation
            autocorr = np.correlate(y, y, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            # Find the first peak after the zero-lag peak
            min_lag = int(sr / 500)  # Max frequency 500Hz
            max_lag = int(sr / 50)   # Min frequency 50Hz
            if max_lag < len(autocorr):
                peak_idx = np.argmax(autocorr[min_lag:max_lag]) + min_lag
                if peak_idx > 0:
                    features['pitch'] = sr / peak_idx
                else:
                    features['pitch'] = 150  # Default
            else:
                features['pitch'] = 150
        except:
            features['pitch'] = 150
        
        # 4. Spectral features
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        features['spectral_centroid'] = np.mean(spectral_centroid)
        
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
        features['spectral_rolloff'] = np.mean(spectral_rolloff)
        
        # 5. MFCC features (voice timbre)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        features['mfcc_mean'] = np.mean(mfcc, axis=1)
        features['mfcc_std'] = np.std(mfcc, axis=1)
        
        # 6. Speech rate estimation (based on energy peaks)
        energy_threshold = np.mean(rms) + np.std(rms)
        speech_frames = np.sum(rms > energy_threshold)
        features['speech_rate'] = (speech_frames / len(rms)) * sr / 512  # Approximate
        
        # 7. Voice intensity variation
        features['intensity_var'] = np.var(rms) / (np.mean(rms) + 1e-10)
        
        return features
    
    def _classify_emotion(self, f):
        """Classify emotion based on extracted features."""
        scores = {}
        
        energy = f['energy']
        pitch = f.get('pitch', 150)
        zcr = f['zcr']
        speech_rate = f.get('speech_rate', 0)
        intensity_var = f.get('intensity_var', 0)
        spectral_centroid = f.get('spectral_centroid', 2000)
        
        # Normalize pitch to typical range
        pitch = max(50, min(400, pitch))
        
        # EMOTION SCORING RULES
        # =====================
        
        # ANGRY: High energy, high pitch, high speech rate, high variation
        angry_score = 0.0
        if energy > 0.05:
            angry_score += 0.3
        if energy > 0.1:
            angry_score += 0.2
        if pitch > 170:
            angry_score += 0.2
        if pitch > 200:
            angry_score += 0.15
        if zcr > 0.06:
            angry_score += 0.15
        if intensity_var > 0.3:
            angry_score += 0.1
        scores['angry'] = min(angry_score, 1.0)
        
        # FEAR: Very high pitch, irregular, variable energy
        fear_score = 0.0
        if pitch > 200:
            fear_score += 0.3
        if pitch > 250:
            fear_score += 0.2
        if intensity_var > 0.4:
            fear_score += 0.2
        if zcr > 0.08:
            fear_score += 0.15
        if energy < 0.08:  # Often quiet with spikes
            fear_score += 0.15
        scores['fear'] = min(fear_score, 1.0)
        
        # SAD: Low energy, low pitch, slow speech
        sad_score = 0.0
        if energy < 0.04:
            sad_score += 0.4
        if energy < 0.02:
            sad_score += 0.2
        if pitch < 150:
            sad_score += 0.2
        if pitch < 120:
            sad_score += 0.15
        if speech_rate < 3:
            sad_score += 0.15
        scores['sad'] = min(sad_score, 1.0)
        
        # HAPPY: Medium-high energy, medium-high pitch, regular
        happy_score = 0.0
        if energy > 0.04:
            happy_score += 0.2
        if energy > 0.07:
            happy_score += 0.15
        if 140 < pitch < 280:
            happy_score += 0.25
        if intensity_var < 0.25:
            happy_score += 0.2
        if spectral_centroid > 2000:
            happy_score += 0.1
        if zcr < 0.07:
            happy_score += 0.1
        scores['happy'] = min(happy_score, 1.0)
        
        # DISGUST: Irregular, low-medium energy, unusual timbre
        disgust_score = 0.0
        if intensity_var > 0.35:
            disgust_score += 0.3
        if zcr > 0.07:
            disgust_score += 0.2
        if energy < 0.06:
            disgust_score += 0.2
        if spectral_centroid < 1800:
            disgust_score += 0.2
        scores['disgust'] = min(disgust_score, 1.0)
        
        # PLEASANT SURPRISE: High energy, high pitch, rising pattern
        surprise_score = 0.0
        if energy > 0.08:
            surprise_score += 0.3
        if pitch > 220:
            surprise_score += 0.3
        if intensity_var > 0.3:
            surprise_score += 0.2
        if spectral_centroid > 2500:
            surprise_score += 0.2
        scores['pleasant_surprise'] = min(surprise_score, 1.0)
        
        # NEUTRAL: Default - not matching other emotions strongly
        neutral_score = 0.3
        if 0.02 < energy < 0.08:
            neutral_score += 0.2
        if 120 < pitch < 200:
            neutral_score += 0.2
        if intensity_var < 0.2:
            neutral_score += 0.2
        if zcr < 0.06:
            neutral_score += 0.1
        scores['neutral'] = min(neutral_score, 1.0)
        
        # Find best match
        best_emotion = max(scores, key=scores.get)
        confidence = scores[best_emotion]
        
        # Boost confidence if there's a clear winner
        sorted_scores = sorted(scores.values(), reverse=True)
        if len(sorted_scores) > 1:
            margin = sorted_scores[0] - sorted_scores[1]
            if margin > 0.2:
                confidence = min(confidence * 1.2, 1.0)
        
        # Minimum confidence
        confidence = max(confidence, 0.35)
        
        return best_emotion, confidence
    
    def predict_batch(self, audio_paths):
        results = []
        for audio_path in audio_paths:
            result = self.predict(audio_path)
            results.append(result)
        return results
    
    def get_model_summary(self):
        return "Audio feature analysis (improved)"


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
