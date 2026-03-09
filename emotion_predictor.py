"""
Emotion Predictor Module
Loads the trained model and makes predictions
"""

import os
import numpy as np
from tensorflow.keras.models import load_model
import pickle

class EmotionPredictor:
    """
    Emotion recognition predictor using trained neural network model.
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
                print("Using fallback prediction method")
                self.model = None
        except Exception as e:
            print(f"Error loading model: {e}")
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
        from feature_extraction import extract_mfcc_features
        
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
                return self._fallback_predict(features)
        else:
            return self._fallback_predict(features)
    
    def _fallback_predict(self, features):
        """
        Fallback prediction when model is not available.
        Returns random emotion for demonstration.
        """
        # Return neutral as default fallback
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
        return "Model not loaded"


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

