"""
Distress Detection Logic Module
Determines if detected emotions indicate distress requiring SOS alert
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DistressDetector:
    """
    Determines if detected emotions indicate distress.
    """
    
    # High-risk emotions that indicate distress
    DISTRESS_EMOTIONS = ['angry', 'fear', 'sad', 'disgust']
    
    # Moderate-risk emotions
    MODERATE_RISK_EMOTIONS = ['pleasant_surprise']
    
    # Low-risk/positive emotions
    SAFE_EMOTIONS = ['happy', 'neutral']
    
    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.7
    MODERATE_CONFIDENCE_THRESHOLD = 0.5
    
    def __init__(self):
        """Initialize the distress detector."""
        self.distress_count = 0
        self.consecutive_distress = 0
        self.threshold = int(os.getenv('DISTRESS_THRESHOLD', '3'))
    
    def is_distress(self, emotion, confidence):
        """
        Determine if the emotion and confidence level indicate distress.
        
        Args:
            emotion: Predicted emotion string
            confidence: Prediction confidence (0-1)
        
        Returns:
            bool: True if distress detected, False otherwise
        """
        emotion = emotion.lower() if emotion else ""
        
        # Check for high-risk emotions with high confidence
        if emotion in self.DISTRESS_EMOTIONS:
            if confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
                self.consecutive_distress += 1
                self.distress_count += 1
                return True
            elif confidence >= self.MODERATE_CONFIDENCE_THRESHOLD:
                self.consecutive_distress += 1
                if self.consecutive_distress >= self.threshold:
                    self.distress_count += 1
                    return True
                return False
        
        # Check for moderate risk emotions
        elif emotion in self.MODERATE_RISK_EMOTIONS:
            if confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
                self.consecutive_distress += 1
                if self.consecutive_distress >= self.threshold:
                    return True
                return False
        
        # Reset counter for safe emotions
        elif emotion in self.SAFE_EMOTIONS:
            self.consecutive_distress = max(0, self.consecutive_distress - 1)
        
        return False
    
    def get_distress_level(self, emotion, confidence):
        """
        Get the level of distress.
        
        Args:
            emotion: Predicted emotion
            confidence: Prediction confidence
        
        Returns:
            str: 'high', 'moderate', or 'low'
        """
        emotion = emotion.lower() if emotion else ""
        
        if emotion in self.DISTRESS_EMOTIONS:
            if confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
                return 'high'
            elif confidence >= self.MODERATE_CONFIDENCE_THRESHOLD:
                return 'moderate'
        
        elif emotion in self.MODERATE_RISK_EMOTIONS:
            if confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
                return 'moderate'
        
        return 'low'
    
    def get_recommendation(self, emotion, confidence):
        """
        Get recommendation based on emotion and confidence.
        
        Args:
            emotion: Predicted emotion
            confidence: Prediction confidence
        
        Returns:
            str: Recommendation message
        """
        distress_level = self.get_distress_level(emotion, confidence)
        
        recommendations = {
            'high': "Immediate attention recommended. Consider reaching out for help.",
            'moderate': "Monitor the situation. Seek support if needed.",
            'low': "No immediate concern. Continue normal activities."
        }
        
        return recommendations.get(distress_level, "Unable to assess.")
    
    def reset_counters(self):
        """Reset distress counters."""
        self.distress_count = 0
        self.consecutive_distress = 0
    
    def get_stats(self):
        """Get distress detection statistics."""
        return {
            'total_distress_detections': self.distress_count,
            'consecutive_distress': self.consecutive_distress,
            'threshold': self.threshold
        }


# Standalone function for simple distress check
def check_distress(emotion, confidence, threshold=3):
    """
    Simple function to check for distress.
    
    Args:
        emotion: Predicted emotion
        confidence: Prediction confidence
        threshold: Number of consecutive distress detections
    
    Returns:
        bool: True if distress detected
    """
    detector = DistressDetector()
    detector.threshold = threshold
    return detector.is_distress(emotion, confidence)


if __name__ == "__main__":
    # Test the distress detector
    detector = DistressDetector()
    
    test_cases = [
        ("angry", 0.8),
        ("fear", 0.6),
        ("sad", 0.9),
        ("happy", 0.7),
        ("neutral", 0.8),
        ("disgust", 0.5),
    ]
    
    print("Distress Detection Tests:")
    print("-" * 50)
    for emotion, confidence in test_cases:
        is_distress = detector.is_distress(emotion, confidence)
        level = detector.get_distress_level(emotion, confidence)
        rec = detector.get_recommendation(emotion, confidence)
        print(f"Emotion: {emotion:20s} | Confidence: {confidence:.2f} | Distress: {is_distress} | Level: {level}")
        print(f"  Recommendation: {rec}")
        print()

