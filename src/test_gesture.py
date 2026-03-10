import cv2
from hand_mode.gesture_engine import get_gesture

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    frame = cv2.flip(frame, 1)

    gesture, _, _, hand_count, frame = get_gesture(frame)

    cv2.putText(frame, f"Gesture: {gesture}", (50, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

    cv2.imshow("Test Gesture", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()