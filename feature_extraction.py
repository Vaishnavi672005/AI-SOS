"""
Feature Extraction Module for Speech Emotion Recognition
Extracts MFCC features from audio files
"""

import numpy as np
import os
import sys

# ============================================
# Configuration
# ============================================
SAMPLE_RATE = 22050
DURATION = 3  # seconds
N_MFCC = 40
N_FFT = 2048
HOP_LENGTH = 512

# Lazy import flags
LIBROSA_AVAILABLE = None
SCIPY_AVAILABLE = None


def _check_librosa():
    """Check if librosa is available without triggering soundfile import."""
    global LIBROSA_AVAILABLE
    if LIBROSA_AVAILABLE is not None:
        return LIBROSA_AVAILABLE
    
    try:
        # Import just the version to check availability
        # This won't trigger soundfile import
        import importlib
        spec = importlib.util.find_spec("librosa")
        if spec is None:
            LIBROSA_AVAILABLE = False
            return False
        
        # Try importing with minimal dependencies
        import librosa
        # Check if librosa.load works
        LIBROSA_AVAILABLE = True
        return True
    except Exception as e:
        print(f"Librosa not available: {e}")
        LIBROSA_AVAILABLE = False
        return False


def _check_scipy():
    """Check if scipy is available."""
    global SCIPY_AVAILABLE
    if SCIPY_AVAILABLE is not None:
        return SCIPY_AVAILABLE
    
    try:
        from scipy.io import wavfile
        import scipy.signal
        SCIPY_AVAILABLE = True
        return True
    except ImportError:
        SCIPY_AVAILABLE = False
        return False


def _load_audio_scipy(audio_path, sr=SAMPLE_RATE, duration=DURATION):
    """Load audio using scipy."""
    try:
        from scipy.io import wavfile
        import scipy.signal
        
        # Read wav file
        rate, data = wavfile.read(audio_path)
        
        # Convert to float
        if data.dtype != np.float32:
            data = data.astype(np.float32)
        
        # Handle stereo to mono
        if len(data.shape) > 1:
            data = data.mean(axis=1)
        
        # Normalize
        if data.max() > 1.0:
            data = data / 32768.0
        
        # Resample if needed
        if rate != sr:
            num_samples = int(len(data) * sr / rate)
            data = scipy.signal.resample(data, num_samples)
        
        # Trim or pad to duration
        target_length = sr * duration
        if len(data) < target_length:
            data = np.pad(data, (0, target_length - len(data)), mode='constant')
        else:
            data = data[:target_length]
        
        return data, sr
    except Exception as e:
        print(f"Error loading audio with scipy: {e}")
        return None, None


def _load_audio_librosa(audio_path, sr=SAMPLE_RATE, duration=DURATION):
    """Load audio using librosa."""
    try:
        import librosa
        audio, audio_sr = librosa.load(audio_path, sr=sr, duration=duration)
        return audio, audio_sr
    except Exception as e:
        print(f"Error loading audio with librosa: {e}")
        return None, None


def extract_mfcc_features(audio_path, sr=SAMPLE_RATE, duration=DURATION, n_mfcc=N_MFCC):
    """
    Extract MFCC features from an audio file.
    
    Args:
        audio_path: Path to audio file
        sr: Sample rate (default: 22050)
        duration: Duration in seconds (default: 3)
        n_mfcc: Number of MFCCs to extract (default: 40)
    
    Returns:
        numpy array of MFCC features
    """
    audio = None
    audio_sr = sr
    
    # Try librosa first (best quality)
    if _check_librosa():
        try:
            audio, audio_sr = _load_audio_librosa(audio_path, sr, duration)
        except Exception as e:
            print(f"Librosa failed: {e}")
    
    # Fallback to scipy if librosa failed
    if audio is None and _check_scipy():
        try:
            audio, audio_sr = _load_audio_scipy(audio_path, sr, duration)
        except Exception as e:
            print(f"Scipy failed: {e}")
    
    if audio is None:
        print(f"Error: No audio loading method available for {audio_path}")
        return None
    
    # Pad or trim to fixed length
    max_len = sr * duration
    if len(audio) < max_len:
        audio = np.pad(audio, (0, max_len - len(audio)), mode='constant')
    else:
        audio = audio[:max_len]
    
    # Extract MFCC features
    if _check_librosa():
        try:
            import librosa
            
            mfcc = librosa.feature.mfcc(y=audio, sr=audio_sr, n_mfcc=n_mfcc)
            
            # Delta and delta-delta features
            mfcc_delta = librosa.feature.delta(mfcc)
            mfcc_delta2 = librosa.feature.delta(mfcc, order=2)
            
            # Combine features
            features = np.vstack([mfcc, mfcc_delta, mfcc_delta2])
            
            # Take mean across time axis
            features_mean = np.mean(features.T, axis=0)
            features_std = np.std(features.T, axis=0)
            
            # Combine mean and std
            final_features = np.concatenate([features_mean, features_std])
            
            return final_features
        except Exception as e:
            print(f"Librosa MFCC extraction failed: {e}")
    
    # Fallback: Use scipy spectrogram as features
    if _check_scipy():
        try:
            import scipy.signal
            
            # Compute spectrogram
            f, t, Sxx = scipy.signal.spectrogram(audio, fs=audio_sr, nperseg=2048)
            
            # Take log of spectrogram (simplified MFCC-like features)
            Sxx_log = np.log(Sxx + 1e-10)
            
            # Take mean and std
            features_mean = np.mean(Sxx_log, axis=1)
            features_std = np.std(Sxx_log, axis=1)
            
            # Combine mean and std
            final_features = np.concatenate([features_mean, features_std])
            
            return final_features
        except Exception as e:
            print(f"Scipy feature extraction failed: {e}")
    
    print(f"Error extracting features from {audio_path}")
    return None


def extract_all_features(audio_path):
    """
    Extract all available audio features for comprehensive analysis.
    
    Args:
        audio_path: Path to audio file
    
    Returns:
        Dictionary of all extracted features
    """
    if not _check_librosa():
        print("Librosa required for extract_all_features")
        return None
    
    try:
        import librosa
        
        audio, sr = librosa.load(audio_path, sr=SAMPLE_RATE, duration=DURATION)
        
        # Pad/trim
        max_len = SAMPLE_RATE * DURATION
        if len(audio) < max_len:
            audio = np.pad(audio, (0, max_len - len(audio)), mode='constant')
        else:
            audio = audio[:max_len]
        
        features = {}
        
        # MFCC
        mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=N_MFCC)
        features['mfcc_mean'] = np.mean(mfcc, axis=1)
        features['mfcc_std'] = np.std(mfcc, axis=1)
        
        # Chroma
        chroma = librosa.feature.chroma_stft(y=audio, sr=sr)
        features['chroma_mean'] = np.mean(chroma, axis=1)
        
        # Spectral contrast
        contrast = librosa.feature.spectral_contrast(y=audio, sr=sr)
        features['contrast_mean'] = np.mean(contrast, axis=1)
        
        # Zero crossing rate
        zcr = librosa.feature.zero_crossing_rate(audio)
        features['zcr_mean'] = np.mean(zcr)
        features['zcr_std'] = np.std(zcr)
        
        # RMS energy
        rms = librosa.feature.rms(y=audio)
        features['rms_mean'] = np.mean(rms)
        features['rms_std'] = np.std(rms)
        
        # Spectral centroid
        centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)
        features['centroid_mean'] = np.mean(centroid)
        
        # Spectral rolloff
        rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr)
        features['rolloff_mean'] = np.mean(rolloff)
        
        return features
        
    except Exception as e:
        print(f"Error extracting all features: {e}")
        return None


def prepare_features_for_model(features):
    """
    Prepare features in the format expected by the model.
    
    Args:
        features: Feature array
    
    Returns:
        Reshaped feature array for model input
    """
    if features is None:
        return None
    
    # Ensure correct shape
    if len(features.shape) == 1:
        # Expand dimensions for single sample
        features = np.expand_dims(features, axis=0)
    
    return features

