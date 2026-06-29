

import os
import json
import numpy as np
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tensorflow.keras import layers, models

# ── Paths ──────────────────────────────────────────────────────
DATA_DIR    = "training/landmark_data"
MODEL_PATH  = "training/models/asl_landmark.h5"
LABELS_PATH = "training/models/landmark_label_map.json"


# ── Normalization (MUST match cnn_predictor.py exactly) ────────
def normalize_landmarks(sample):
    """
    Normalize a 63-element landmark array to the hand's bounding box.

    Makes the model position-invariant and scale-invariant:
      - x, y are normalized to [0, 1] within the hand's bounding box
      - z (depth) is kept as-is (already relative in MediaPipe)
    """
    coords = sample.reshape(21, 3).copy()
    x = coords[:, 0]
    y = coords[:, 1]

    min_x, max_x = x.min(), x.max()
    min_y, max_y = y.min(), y.max()
    range_x = max(max_x - min_x, 0.001)
    range_y = max(max_y - min_y, 0.001)

    coords[:, 0] = (x - min_x) / range_x
    coords[:, 1] = (y - min_y) / range_y

    return coords.flatten()


# ── Data Augmentation ──────────────────────────────────────────
def augment_landmarks(X, y, noise_level=0.015, copies=5):
    """
    Create augmented samples by adding Gaussian noise
    to landmark positions. Simulates natural hand variation.
    """
    X_aug = [X]
    y_aug = [y]

    for _ in range(copies):
        noise = np.random.normal(0, noise_level, X.shape).astype("float32")
        X_aug.append(X + noise)
        y_aug.append(y)

    return np.concatenate(X_aug), np.concatenate(y_aug)


# ── Step 1: Load Data ─────────────────────────────────────────
print("=" * 55)
print("  SIGNDESK — LANDMARK MODEL TRAINING")
print("=" * 55)

if not os.path.exists(DATA_DIR):
    print(f"\nERROR: No data found at '{DATA_DIR}'")
    print("Run collect_landmarks.py first!")
    exit(1)

npy_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith(".npy")])
if not npy_files:
    print(f"\nERROR: No .npy files found in '{DATA_DIR}'")
    print("Run collect_landmarks.py first!")
    exit(1)

labels = [f.replace(".npy", "") for f in npy_files]
label_map = {letter: idx for idx, letter in enumerate(labels)}

print(f"\nFound data for {len(labels)} letters: {', '.join(labels)}")

X, y = [], []

for letter in labels:
    data = np.load(os.path.join(DATA_DIR, f"{letter}.npy"))
    for sample in data:
        normalized = normalize_landmarks(sample)
        X.append(normalized)
        y.append(label_map[letter])
    print(f"  [{letter}] {len(data):>4d} samples")

X = np.array(X, dtype="float32")
y = np.array(y, dtype="int32")

print(f"\nTotal samples:  {len(X)}")
print(f"Classes:        {len(labels)}")
print(f"Feature shape:  {X.shape[1]} (21 landmarks × 3 coords)")

# ── Step 2: Train / Validation Split ──────────────────────────
X_train, X_val, y_train, y_val = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"\nTraining:    {len(X_train)} samples")
print(f"Validation:  {len(X_val)} samples")

# ── Step 3: Augment Training Data ─────────────────────────────
X_train_aug, y_train_aug = augment_landmarks(X_train, y_train)
print(f"Augmented:   {len(X_train_aug)} samples (5× noise copies)")

# ── Step 4: Build Dense Model ─────────────────────────────────
print("\nBuilding model...")

num_classes = len(labels)

model = models.Sequential([
    layers.Input(shape=(63,)),

    layers.Dense(512, activation="relu"),
    layers.BatchNormalization(),
    layers.Dropout(0.3),

    layers.Dense(256, activation="relu"),
    layers.BatchNormalization(),
    layers.Dropout(0.3),

    layers.Dense(128, activation="relu"),
    layers.BatchNormalization(),
    layers.Dropout(0.2),

    layers.Dense(64, activation="relu"),
    layers.Dropout(0.2),

    layers.Dense(num_classes, activation="softmax")
])

model.compile(
    optimizer="adam",
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"]
)

model.summary()

# ── Step 5: Train ─────────────────────────────────────────────
print("\nTraining...")

os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

callbacks = [
    tf.keras.callbacks.EarlyStopping(
        monitor="val_accuracy",
        patience=15,
        restore_best_weights=True,
        verbose=1
    ),
    tf.keras.callbacks.ModelCheckpoint(
        MODEL_PATH,
        monitor="val_accuracy",
        save_best_only=True,
        verbose=1
    ),
    tf.keras.callbacks.ReduceLROnPlateau(
        monitor="val_loss",
        factor=0.5,
        patience=5,
        verbose=1
    )
]

history = model.fit(
    X_train_aug, y_train_aug,
    epochs=150,
    batch_size=32,
    validation_data=(X_val, y_val),
    callbacks=callbacks,
    verbose=1
)

# ── Step 6: Evaluate ──────────────────────────────────────────
val_loss, val_acc = model.evaluate(X_val, y_val, verbose=0)
print(f"\n{'=' * 55}")
print(f"  Final Validation Accuracy: {val_acc * 100:.2f}%")
print(f"  Final Validation Loss:     {val_loss:.4f}")
print(f"{'=' * 55}")

# ── Step 7: Save Label Map ────────────────────────────────────
with open(LABELS_PATH, "w") as f:
    json.dump(label_map, f, indent=2)

print(f"\n  Model saved  → {MODEL_PATH}")
print(f"  Labels saved → {LABELS_PATH}")
print()
print("  Your app will now use this model automatically!")
print("  Run: python main.py")
print()
