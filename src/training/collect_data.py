import cv2
import mediapipe as mp
import csv

CURRENT_LABEL = input("Enter gesture label: ")
DATA_FILE = "gesture_data.csv"

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)
count = 0

print(f"Recording for label: {CURRENT_LABEL}")
print("Press 'S' to save a frame, 'Q' to quit.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb_frame)

    landmarks = None

    if result.multi_hand_landmarks:
        hand_landmarks = result.multi_hand_landmarks[0]
        mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        base_x = hand_landmarks.landmark[0].x
        base_y = hand_landmarks.landmark[0].y

        landmarks = []
        for lm in hand_landmarks.landmark:
            landmarks.extend([lm.x - base_x, lm.y - base_y])

    cv2.putText(frame, f"Label: {CURRENT_LABEL} | Samples: {count}",
                (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 0, 0),
                2)

    cv2.imshow("Data Collector (Normalized)", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord('s') and landmarks is not None:
        with open(DATA_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(landmarks + [CURRENT_LABEL])
        count += 1
        print(f"Captured {count} samples for {CURRENT_LABEL}")

    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()