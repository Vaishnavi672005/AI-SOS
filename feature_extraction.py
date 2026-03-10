"""
Feature Extraction Module
Extracts MFCC features from audio files
"""

import numpy as np
import librosa


def extract_mfcc_features(audio_path, n_mfcc=40, duration=3):
    """
    Extract MFCC features from audio file.
    
    Args:
        audio_path: Path to audio file
        n_mfcc: Number of MFCCs to extract
        duration: Duration of audio to analyze (seconds)
    
    Returns:
        numpy array of MFCC features
    """
    try:
        # Load audio file
        y, sr = librosa.load(audio_path, duration=duration)
        
        # Extract MFCCs
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
        
        # Compute statistics
        mfccs_mean = np.mean(mfccs, axis=1)
        mfccs_std = np.std(mfccs, axis=1)
        
        # Combine mean and std
        features = np.concatenate([mfccs_mean, mfccs_std])
        
        return features
        
    except Exception as e:
        print(f"Error extracting features: {e}")
        return None


def extract_all_features(audio_path):
    """
    Extract all audio features including MFCC, chroma, mel spectrogram, etc.
    
    Args:
        audio_path: Path to audio file
    
    Returns:
        numpy array of all features
    """
    try:
        y, sr = librosa.load(audio_path)
        
        # MFCCs
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40)
        mfccs_mean = np.mean(mfccs, axis=1)
        mfccs_std = np.std(mfccs, axis=1)
        
        # Chroma
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        chroma_mean = np.mean(chroma, axis=1)
        chroma_std = np.std(chroma, axis=1)
        
        # Mel spectrogram
        mel = librosa.feature.melspectrogram(y=y, sr=sr)
        mel_db = librosa.power_to_db(mel, ref=np.max)
        mel_mean = np.mean(mel_db, axis=1)
        mel_std = np.std(mel_db, axis=1)
        
        # Spectral contrast
        contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
        contrast_mean = np.mean(contrast, axis=1)
        contrast_std = np.std(contrast, axis=1)
        
        # Tonnetz
        tonnetz = librosa.feature.tonnetz(y=y, sr=sr)
        tonnetz_mean = np.mean(tonnetz, axis=1)
        tonnetz_std = np.std(tonnetz, axis=1)
        
        # Combine all features
        features = np.concatenate([
            mfccs_mean, mfccs_std,
            chroma_mean, chroma_std,
            mel_mean, mel_std,
            contrast_mean, contrast_std,
            tonnetz_mean, tonnetz_std
        ])
        
        return features
        
    except Exception as e:
        print(f"Error extracting features: {e}")
        return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        features = extract_mfcc_features(sys.argv[1])
        if features is not None:
            print(f"Extracted {len(features)} features")
            print(features[:10])
    else:
        print("Usage: python feature_extraction.py <audio_file>")

