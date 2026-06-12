import os
import json
import numpy as np
import cv2
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tensorflow.keras import layers, models

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_PATH   = "training/data/AtoZ_3.1"
MODEL_PATH  = "training/models/asl_cnn.h5"
LABELS_PATH = "training/models/label_map.json"
IMG_SIZE    = 64  # resize all images to 64x64 for faster training

# ── Step 1: Load and label the dataset ────────────────────────────────────────
print("Loading dataset...")

labels     = sorted(os.listdir(DATA_PATH))  # ['A', 'B', ... 'Z']
label_map  = {letter: idx for idx, letter in enumerate(labels)}

X, y = [], []

for letter in labels:
    folder = os.path.join(DATA_PATH, letter)
    images = os.listdir(folder)
    for img_file in images:
        img_path = os.path.join(folder, img_file)
        img      = cv2.imread(img_path)
        if img is None:
            continue
        img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
        img = img / 255.0  # normalize to 0-1
        X.append(img)
        y.append(label_map[letter])
    print(f"  Loaded {len(images)} images for '{letter}'")

X = np.array(X, dtype="float32")
y = np.array(y, dtype="int32")
print(f"\nTotal images loaded: {len(X)}")
print(f"Labels: {label_map}")

# ── Step 2: Train / Validation split ──────────────────────────────────────────
X_train, X_val, y_train, y_val = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"\nTraining samples:   {len(X_train)}")
print(f"Validation samples: {len(X_val)}")

# ── Step 3: Build the CNN ──────────────────────────────────────────────────────
print("\nBuilding model...")

model = models.Sequential([
    # Block 1
    layers.Conv2D(32, (3, 3), activation="relu",
                  input_shape=(IMG_SIZE, IMG_SIZE, 3)),
    layers.BatchNormalization(),
    layers.MaxPooling2D(2, 2),

    # Block 2
    layers.Conv2D(64, (3, 3), activation="relu"),
    layers.BatchNormalization(),
    layers.MaxPooling2D(2, 2),

    # Block 3
    layers.Conv2D(128, (3, 3), activation="relu"),
    layers.BatchNormalization(),
    layers.MaxPooling2D(2, 2),

    # Classifier
    layers.Flatten(),
    layers.Dense(256, activation="relu"),
    layers.Dropout(0.4),
    layers.Dense(26, activation="softmax")
])

model.compile(
    optimizer="adam",
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"]
)

model.summary()

# ── Step 4: Data Augmentation ──────────────────────────────────────────────────
# Helps compensate for the small dataset (~180 images per letter)
datagen = tf.keras.preprocessing.image.ImageDataGenerator(
    rotation_range=10,
    width_shift_range=0.1,
    height_shift_range=0.1,
    zoom_range=0.1,
    horizontal_flip=False  # ASL signs are NOT mirrored
)
datagen.fit(X_train)

# ── Step 5: Train ──────────────────────────────────────────────────────────────
print("\nTraining...")

callbacks = [
    tf.keras.callbacks.EarlyStopping(
        monitor="val_accuracy",
        patience=5,
        restore_best_weights=True,
        verbose=1
    ),
    tf.keras.callbacks.ModelCheckpoint(
        MODEL_PATH,
        monitor="val_accuracy",
        save_best_only=True,
        verbose=1
    )
]

history = model.fit(
    datagen.flow(X_train, y_train, batch_size=32),
    epochs=30,
    validation_data=(X_val, y_val),
    callbacks=callbacks,
    verbose=1
)

# ── Step 6: Evaluate ───────────────────────────────────────────────────────────
val_loss, val_acc = model.evaluate(X_val, y_val, verbose=0)
print(f"\nFinal Validation Accuracy: {val_acc * 100:.2f}%")
print(f"Final Validation Loss:     {val_loss:.4f}")

# ── Step 7: Save label map ─────────────────────────────────────────────────────
os.makedirs("training/models", exist_ok=True)
with open(LABELS_PATH, "w") as f:
    json.dump(label_map, f, indent=2)

print(f"\nModel saved  → {MODEL_PATH}")
print(f"Labels saved → {LABELS_PATH}")
print("\nDone! Ready for Day 3 integration.")