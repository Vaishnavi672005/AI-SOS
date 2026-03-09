# train_emotion_model.py
# Speech Emotion Recognition - TESS Dataset
# Run in VSCode with Python environment

import os
import numpy as np
import librosa
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Flatten, Dense, Dropout, BatchNormalization
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

# ============================================
# 1. CONFIGURATION
# ============================================
TESS_PATH = "./TESS"  # Relative path to TESS dataset directory
SAMPLE_RATE = 22050
DURATION = 3  # seconds
N_MFCC = 40
EPOCHS = 50
BATCH_SIZE = 32

# Emotion labels in TESS dataset
EMOTIONS = ["angry", "disgust", "fear", "happy", "neutral", "pleasant_surprise", "sad"]

# ============================================
# 2. FEATURE EXTRACTION
# ============================================
def extract_mfcc(file_path, sr=SAMPLE_RATE, duration=DURATION, n_mfcc=N_MFCC):
    """Extract MFCC features from an audio file."""
    try:
        audio, _ = librosa.load(file_path, sr=sr, duration=duration)
        # Pad or trim to fixed length
        max_len = sr * duration
        if len(audio) < max_len:
            audio = np.pad(audio, (0, max_len - len(audio)), mode='constant')
        else:
            audio = audio[:max_len]
        
        mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=n_mfcc)
        return mfcc.T  # Transpose: (time_steps, n_mfcc)
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

# ============================================
# 3. LOAD TESS DATASET
# ============================================
def load_tess_dataset(dataset_path):
    """Load all audio files and extract features + labels."""
    features = []
    labels = []
    
    for folder in os.listdir(dataset_path):
        folder_path = os.path.join(dataset_path, folder)
        if not os.path.isdir(folder_path):
            continue
        
        # TESS folder names: OAF_angry, YAF_angry, OAF_fear, etc.
        emotion = folder.split("_")[-1].lower()
        
        if emotion not in EMOTIONS:
            print(f"Skipping unknown emotion folder: {folder}")
            continue
        
        print(f"Processing: {folder} -> Emotion: {emotion}")
        
        for file_name in os.listdir(folder_path):
            if not file_name.endswith(".wav"):
                continue
            
            file_path = os.path.join(folder_path, file_name)
            mfcc = extract_mfcc(file_path)
            
            if mfcc is not None:
                features.append(mfcc)
                labels.append(emotion)
    
    return np.array(features), np.array(labels)

print("Loading TESS dataset...")
X, y = load_tess_dataset(TESS_PATH)
print(f"Dataset loaded: {X.shape[0]} samples, Feature shape: {X.shape[1:]}")

# ============================================
# 4. ENCODE LABELS
# ============================================
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)
y_onehot = to_categorical(y_encoded)
num_classes = y_onehot.shape[1]

print(f"Classes ({num_classes}): {list(label_encoder.classes_)}")

# Save label encoder classes for prediction later
np.save("model/label_classes.npy", label_encoder.classes_)

# ============================================
# 5. TRAIN-TEST SPLIT
# ============================================
X_train, X_test, y_train, y_test = train_test_split(
    X, y_onehot, test_size=0.2, random_state=42, stratify=y_onehot
)

# Reshape for Conv1D: (samples, time_steps, features)
print(f"Train: {X_train.shape}, Test: {X_test.shape}")

# ============================================
# 6. BUILD CNN MODEL
# ============================================
model = Sequential([
    # Block 1
    Conv1D(64, kernel_size=3, activation='relu', input_shape=(X_train.shape[1], X_train.shape[2])),
    BatchNormalization(),
    MaxPooling1D(pool_size=2),
    Dropout(0.3),
    
    # Block 2
    Conv1D(128, kernel_size=3, activation='relu'),
    BatchNormalization(),
    MaxPooling1D(pool_size=2),
    Dropout(0.3),
    
    # Block 3
    Conv1D(256, kernel_size=3, activation='relu'),
    BatchNormalization(),
    MaxPooling1D(pool_size=2),
    Dropout(0.4),
    
    # Block 4
    Conv1D(512, kernel_size=3, activation='relu'),
    BatchNormalization(),
    MaxPooling1D(pool_size=2),
    Dropout(0.4),
    
    # Classification head
    Flatten(),
    Dense(256, activation='relu'),
    Dropout(0.5),
    Dense(128, activation='relu'),
    Dropout(0.3),
    Dense(num_classes, activation='softmax')
])

model.compile(
    optimizer='adam',
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

model.summary()

# ============================================
# 7. TRAIN THE MODEL
# ============================================
os.makedirs("model", exist_ok=True)

callbacks = [
    EarlyStopping(monitor='val_loss', patience=8, restore_best_weights=True),
    ModelCheckpoint("model/emotion_model.h5", monitor='val_accuracy', save_best_only=True, verbose=1)
]

print("\nTraining started...")
history = model.fit(
    X_train, y_train,
    validation_data=(X_test, y_test),
    epochs=EPOCHS,
    batch_size=BATCH_SIZE,
    callbacks=callbacks
)

# ============================================
# 8. EVALUATE
# ============================================
loss, accuracy = model.evaluate(X_test, y_test)
print(f"\nTest Accuracy: {accuracy * 100:.2f}%")
print(f"Test Loss: {loss:.4f}")

# ============================================
# 9. PLOT TRAINING HISTORY (optional)
# ============================================
try:
    import matplotlib.pyplot as plt
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    ax1.plot(history.history['accuracy'], label='Train')
    ax1.plot(history.history['val_accuracy'], label='Validation')
    ax1.set_title('Model Accuracy')
    ax1.set_xlabel('Epoch')
    ax1.legend()
    
    ax2.plot(history.history['loss'], label='Train')
    ax2.plot(history.history['val_loss'], label='Validation')
    ax2.set_title('Model Loss')
    ax2.set_xlabel('Epoch')
    ax2.legend()
    
    plt.savefig("model/training_history.png")
    plt.show()
    print("Training plot saved to model/training_history.png")
except ImportError:
    print("Install matplotlib for training plots: pip install matplotlib")

print("\n✅ Model saved to model/emotion_model.h5")
print("✅ Label classes saved to model/label_classes.npy")

