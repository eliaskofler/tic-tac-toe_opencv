import cv2

cap = cv2.VideoCapture(2)

if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Can't receive frame.")
        break
    
    frame = cv2.rotate(frame, cv2.ROTATE_180)

    # 1. Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    
    # 4. Apply inverted binary threshold (for detecting shapes on paper)
    _, thresh_inv = cv2.threshold(gray, 170, 255, cv2.THRESH_BINARY_INV)
    
    # 5. Apply Gaussian blur on inverted threshold
    thresh_inv_blurred = cv2.GaussianBlur(thresh_inv, (7, 7), 0)
    
    # Display the results
    cv2.imshow('1. Original', frame)
    #cv2.imshow('2. Grayscale', gray)
    cv2.imshow('5. Threshold (Binary Inv)', thresh_inv)
    cv2.imshow('6. Threshold (Binary Inv + Blur)', thresh_inv_blurred)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()