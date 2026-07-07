import numpy as np
import tensorflow as tf
import cv2

model = tf.keras.models.load_model("data/model.keras")

img = cv2.imread("data/images/test/nough/2.jpg", cv2.IMREAD_GRAYSCALE)
img = cv2.resize(img, (32, 32))

# 1. Add the channel dimension -> shape becomes (32, 32, 1)
img = np.expand_dims(img, axis=-1)

# 2. ADD THIS: Add the batch dimension -> shape becomes (1, 32, 32, 1)
img = np.expand_dims(img, axis=0)

# 3. Convert to float and scale (don't forget to divide by 255.0 if trained that way!)
img_float = img.astype(np.float32) / 255.0

# Now predict will work perfectly
predictions = model.predict(img_float)

# 8. Interpret the results
print("Raw probabilities:", predictions)
predicted_class = np.argmax(predictions, axis=1)
print("Predicted class index:", predicted_class[0])