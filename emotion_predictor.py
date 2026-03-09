"""
Emotion Predictor Module
Uses audio feature analysis to detect emotions
(No TensorFlow required - works with audio characteristics)
"""

import os
import numpy as np
import librosa

class EmotionPredictor:
    """
    Emotion recognition predictor using audio feature analysis.
    Analyzes audio characteristics (energy, pitch, speech rate) to determine emotion.
    """
    
    def __init__(self, model_path=None, labels_path=None):
        """
        Initialize the emotion predictor.
        
        Args:
            model_path: Not used (kept for compatibility)
            labels_path: Not used (kept for compatibility)
        """
        self.model_path = model_path
        self.labels_path = labels_path
        self.model = None
        
        # Default emotion labels
        self.label_classes = np.array([
            'angry', 'disgust', 'fear', 'happy', 
            'neutral', 'pleasant_surprise', 'sad'
        ])
        
        print("Emotion predictor initialized (audio analysis mode)")
    
    def predict(self, audio_path):
        """
        Predict emotion from an audio file using audio feature analysis.
        
        Args:
            audio_path: Path to the audio file
        
        Returns:
            tuple: (predicted_emotion, confidence)
        """
        return self._audio_based_predict(audio_path)
    
    def _audio_based_predict(self, audio_path):
        """
        Audio feature-based emotion prediction.
        Analyzes audio characteristics to determine emotion.
        """
        try:
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
            
            # 6. Spectral rolloff
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
            sr_mean = np.mean(spectral_rolloff)
            
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
            if rms_mean > 0.08:
                scores['angry'] += 0.4
            if pitch_mean > 180:
                scores['angry'] += 0.3
            if zcr_mean > 0.08:
                scores['angry'] += 0.2
            if rms_std > 0.08:
                scores['angry'] += 0.1
            
            # Fear: High pitch, irregular speech, variable energy
            if pitch_mean > 200:
                scores['fear'] += 0.3
            if pitch_std > 80:
                scores['fear'] += 0.3
            if rms_std > 0.1:
                scores['fear'] += 0.2
            if zcr_std > 0.05:
                scores['fear'] += 0.1
            
            # Sad: Low energy, low pitch, slow speech
            if rms_mean < 0.05:
                scores['sad'] += 0.5
            if pitch_mean < 160:
                scores['sad'] += 0.3
            if zcr_mean < 0.05:
                scores['sad'] += 0.2
            
            # Happy: High energy, medium-high pitch, regular
            if rms_mean > 0.06:
                scores['happy'] += 0.3
            if 150 < pitch_mean < 280:
                scores['happy'] += 0.3
            if zcr_std < 0.04:
                scores['happy'] += 0.2
            if sc_mean > 2500:
                scores['happy'] += 0.1
            
            # Neutral: Medium energy, normal pitch
            if 0.03 < rms_mean < 0.08:
                scores['neutral'] += 0.3
            if 120 < pitch_mean < 220:
                scores['neutral'] += 0.3
            if zcr_std < 0.03:
                scores['neutral'] += 0.2
            
            # Disgust: Similar to angry but with more irregularity
            if rms_std > 0.12:
                scores['disgust'] += 0.4
            if zcr_std > 0.06:
                scores['disgust'] += 0.3
            
            # Pleasant surprise: High energy with rising pitch pattern
            if rms_mean > 0.1:
                scores['pleasant_surprise'] += 0.3
            if pitch_mean > 220:
                scores['pleasant_surprise'] += 0.3
            
            # Normalize scores and find best match
            total_score = sum(scores.values())
            if total_score > 0:
                for emotion in scores:
                    scores[emotion] /= total_score
            
            # Get the emotion with highest score
            best_emotion = max(scores, key=scores.get)
            confidence = scores[best_emotion]
            
            # Ensure minimum confidence
            if confidence < 0.25:
                confidence = 0.25
            
            print(f"Audio-based prediction: {best_emotion} (confidence: {confidence:.2f})")
            print(f"  Energy: {rms_mean:.3f}, Pitch: {pitch_mean:.1f}Hz, ZCR: {zcr_mean:.3f}")
            
            return best_emotion, confidence
            
        except Exception as e:
            print(f"Audio analysis error: {e}")
            # Ultimate fallback
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
        """Get model info."""
        return "Using audio feature analysis (no deep learning model)"


# Helper function for direct prediction
def quick_predict(audio_path, model_path=None, labels_path=None):
    """
    Quick prediction function for single audio file.
    
    Args:
        audio_path: Path to audio file
        model_path: Not used
        labels_path: Not used
    
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
        emotion, confidence = quick_predict(audio_file)
        print(f"Emotion: {emotion}, Confidence: {confidence}")
    else:
        print("Usage: python emotion_predictor.py <audio_file>")
