from sys import flags
import time
import cv2
import pyautogui as p


def AuthenticateFace():
    flag = 0

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(r"backend\auth\trainer\trainer.yml")

    cascadePath = r"backend\auth\haarcascade_frontalface_default.xml"
    faceCascade = cv2.CascadeClassifier(cascadePath)

    font = cv2.FONT_HERSHEY_SIMPLEX
    names = ["", "", "Ranjeet"]

    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cam.set(3, 640)
    cam.set(4, 480)

    minW = 0.1 * cam.get(3)
    minH = 0.1 * cam.get(4)

    match_count = 0
    matches_required = 8

    while True:
        ret, img = cam.read()

        if not ret:
            break

        converted_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        faces = faceCascade.detectMultiScale(
            converted_image,
            scaleFactor=1.2,
            minNeighbors=5,
            minSize=(int(minW), int(minH)),
        )

        if len(faces) == 0:
            match_count = 0

        for (x, y, w, h) in faces:
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

            predicted_id, confidence = recognizer.predict(
                converted_image[y:y + h, x:x + w]
            )

            if predicted_id == 2 and confidence < 55:
                match_count += 1
                name = names[predicted_id]
                score = f"{round(100 - confidence)}%"

                if match_count >= matches_required:
                    flag = 1
            else:
                match_count = 0
                name = "Unknown"
                score = f"{max(0, round(100 - confidence))}%"
                flag = 0

            cv2.putText(
                img, name, (x + 5, y - 5),
                font, 1, (255, 255, 255), 2
            )

            cv2.putText(
                img, score, (x + 5, y + h - 5),
                font, 1, (255, 255, 0), 1
            )

        cv2.imshow("camera", img)

        k = cv2.waitKey(10) & 0xff
        if k == 27 or flag == 1:
            break

    cam.release()
    cv2.destroyAllWindows()

    return flag