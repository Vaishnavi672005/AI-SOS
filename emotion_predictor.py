"""
Emotion Predictor Module
Uses scipy for audio processing (compatible with Python 3.12+)
"""

import os
import numpy as np
from scipy.io import wavfile
import scipy.signal

class EmotionPredictor:
    """
    Emotion recognition using audio feature analysis with scipy.
    Optimized for aggressive distress/fear detection.
    """
    
    def __init__(self, model_path=None, labels_path=None):
        self.model_path = model_path
        self.labels_path = labels_path
        self.model = None
        self.label_classes = np.array([
            'angry', 'disgust', 'fear', 'happy', 
            'neutral', 'sad'
        ])
        print("Emotion predictor initialized (scipy-based, fear-optimized)")
    
    def predict(self, audio_path):
        return self._audio_based_predict(audio_path)
    
    def _audio_based_predict(self, audio_path):
        """
        Ultra-aggressive emotion prediction using scipy.
        Enhanced for fear detection.
        """
        try:
            # Load audio using scipy
            rate, data = wavfile.read(audio_path)
            
            # Convert to float
            if data.dtype != np.float32:
                data = data.astype(np.float32)
            
            # Handle stereo to mono
            if len(data.shape) > 1:
                data = data.mean(axis=1)
            
            # Normalize
            if np.abs(data).max() > 1.0:
                data = data / 32768.0
            
            # Resample to 22050 if needed
            if rate != 22050:
                num_samples = int(len(data) * 22050 / rate)
                data = scipy.signal.resample(data, num_samples)
            
            # Ensure we have 3 seconds of audio
            target_length = 22050 * 3
            if len(data) < target_length:
                data = np.pad(data, (0, target_length - len(data)), mode='constant')
            else:
                data = data[:target_length]
            
            # Extract features
            features = self._extract_features(data, 22050)
            
            # Classify based on features
            emotion, confidence = self._classify_emotion(features)
            
            print(f"Prediction: {emotion} ({confidence:.2f})")
            print(f"  Energy: {features['energy']:.3f}, Pitch: {features.get('pitch', 150):.0f}Hz")
            
            return emotion, confidence
            
        except Exception as e:
            print(f"Error: {e}")
            return "neutral", 0.5
    
    def _extract_features(self, y, sr):
        """Extract audio features using scipy."""
        features = {}
        
        # Energy (RMS) - computed manually
        features['energy'] = np.sqrt(np.mean(y**2))
        features['energy_std'] = np.std(y)
        features['energy_max'] = np.max(np.abs(y))
        
        # Zero Crossing Rate - computed manually
        zero_crossings = np.sum(np.abs(np.diff(np.sign(y)))) / 2
        features['zcr'] = zero_crossings / len(y)
        features['zcr_std'] = np.std(np.abs(np.diff(np.sign(y))))
        
        # Pitch estimation using autocorrelation
        pitch, pitch_std = self._estimate_pitch(y, sr)
        features['pitch'] = pitch
        features['pitch_std'] = pitch_std
        
        # Spectral features using scipy
        f, t, Sxx = scipy.signal.spectrogram(y, fs=sr, nperseg=2048)
        Sxx_log = np.log(Sxx + 1e-10)
        
        # Spectral centroid
        frequencies = f[:, np.newaxis]
        spectral_centroid = np.sum(frequencies * Sxx, axis=0) / (np.sum(Sxx, axis=0) + 1e-10)
        features['spectral_centroid'] = np.mean(spectral_centroid)
        
        # Intensity variation (using rolling window)
        window_size = sr // 10  # 0.1 second windows
        energies = []
        for i in range(0, len(y) - window_size, window_size):
            energies.append(np.sqrt(np.mean(y[i:i+window_size]**2)))
        energies = np.array(energies)
        features['intensity_var'] = np.var(energies) / (np.mean(energies) + 1e-10)
        features['rms_dynamic_range'] = np.max(energies) - np.min(energies)
        
        return features
    
    def _estimate_pitch(self, y, sr):
        """Estimate pitch using autocorrelation."""
        try:
            # Compute autocorrelation
            corr = scipy.signal.correlate(y, y, mode='full')
            corr = corr[len(corr)//2:]  # Take second half
            
            # Find the first significant peak after the zero-lag peak
            min_lag = sr // 500  # Max frequency 500 Hz
            max_lag = sr // 50   # Min frequency 50 Hz
            
            if max_lag < len(corr):
                corr_subset = corr[min_lag:max_lag]
                if len(corr_subset) > 0:
                    peak_idx = np.argmax(corr_subset) + min_lag
                    if peak_idx > 0:
                        pitch = sr / peak_idx
                        # Estimate pitch variation from nearby peaks
                        if peak_idx + 5 < len(corr) and peak_idx - 5 > 0:
                            pitch_std = np.std([sr / (peak_idx + i) for i in range(-5, 6) if peak_idx + i > 0])
                        else:
                            pitch_std = 20
                        return pitch, pitch_std
            
            return 150, 30  # Default values
        except:
            return 150, 30
    
    def _classify_emotion(self, f):
        """
        Classify emotion with BALANCED scoring for fear detection.
        """
        
        energy = f['energy']
        pitch = f.get('pitch', 150)
        pitch_std = f.get('pitch_std', 30)
        zcr = f['zcr']
        intensity_var = f.get('intensity_var', 0)
        spectral_centroid = f.get('spectral_centroid', 2000)
        rms_dynamic_range = f.get('rms_dynamic_range', 0)
        
        # DEBUG: Print raw features
        print(f"DEBUG: energy={energy:.4f}, pitch={pitch:.1f}, zcr={zcr:.4f}, intensity_var={intensity_var:.4f}")
        
        # Normalize pitch
        pitch = max(50, min(400, pitch))
        
        # Calculate scores - BALANCED thresholds
        scores = {}
        
        # FEAR: Detect trembling, high pitch variation
        fear = 0
        if pitch_std > 25:  # High pitch variation = nervous/afraid
            fear += 0.6
        if pitch > 180:  # Higher pitch
            fear += 0.3
        if intensity_var > 0.15:  # Variable intensity
            fear += 0.4
        if zcr > 0.04:  # Higher zcr
            fear += 0.3
        if rms_dynamic_range > 0.02:  # Trembling
            fear += 0.4
        if energy < 0.08:  # Lower energy
            fear += 0.2
        scores['fear'] = min(fear, 1.0)
        
        # ANGRY: High energy OR high pitch OR high zcr
        angry = 0
        if energy > 0.03:
            angry += 0.5
        if energy > 0.06:
            angry += 0.3
        if pitch > 140:
            angry += 0.3
        if zcr > 0.04:
            angry += 0.3
        if intensity_var > 0.15:
            angry += 0.3
        scores['angry'] = min(angry, 1.0)
        
        # SAD: Low energy OR low pitch
        sad = 0
        if energy < 0.02:
            sad += 0.6
        if energy < 0.04:
            sad += 0.3
        if pitch < 160:
            sad += 0.3
        if pitch < 130:
            sad += 0.3
        if zcr < 0.03:
            sad += 0.3
        scores['sad'] = min(sad, 1.0)
        
        # HAPPY: Medium energy + normal pitch + regular patterns
        happy = 0
        if energy > 0.02:
            happy += 0.3
        if 100 < pitch < 280:
            happy += 0.4
        if intensity_var < 0.3:
            happy += 0.3
        if spectral_centroid > 1000:
            happy += 0.2
        scores['happy'] = min(happy, 1.0)
        
        # DISGUST: Irregular patterns with low energy
        disgust = 0
        if intensity_var > 0.15:
            disgust += 0.4
        if zcr > 0.04:
            disgust += 0.3
        if energy < 0.04:
            disgust += 0.4
        scores['disgust'] = min(disgust, 1.0)
        
        # NEUTRAL: Calm, regular patterns
        neutral = 0.3
        if 0.01 < energy < 0.04:
            neutral += 0.2
        if 120 < pitch < 200:
            neutral += 0.2
        if intensity_var < 0.1:
            neutral += 0.2
        if pitch_std < 20:
            neutral += 0.2
        scores['neutral'] = min(neutral, 0.8)
        
        # DEBUG: Print all scores
        print(f"DEBUG SCORES: {scores}")
        
        # Find best match
        best_emotion = max(scores, key=scores.get)
        confidence = scores[best_emotion]
        
        # If neutral wins but distress has decent score, prefer distress
        if best_emotion == 'neutral' and confidence < 0.6:
            distress_emotions = ['fear', 'angry', 'sad', 'disgust']
            distress_scores = {e: scores[e] for e in distress_emotions}
            best_distress = max(distress_scores, key=distress_scores.get)
            
            # If any distress emotion has significant score, prefer it
            if scores[best_distress] >= 0.4:
                best_emotion = best_distress
                confidence = scores[best_distress]
        
        # Ensure minimum confidence
        if best_emotion in ['fear', 'angry', 'sad', 'disgust']:
            confidence = max(confidence, 0.4)
        else:
            confidence = max(confidence, 0.35)
        
        return best_emotion, confidence
    
    def predict_batch(self, audio_paths):
        results = []
        for audio_path in audio_paths:
            result = self.predict(audio_path)
            results.append(result)
        return results
    
    def get_model_summary(self):
        return "Scipy-based audio feature analysis (fear-optimized)"


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

