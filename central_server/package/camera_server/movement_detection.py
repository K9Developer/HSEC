from tabnanny import verbose
import cv2
from ultralytics import YOLO

class MovementDetector:
    def __init__(self, logger, threshold=70):
        self.threshold = threshold
        self.logger = logger
        self.logger.info("Setting up model...")
        self.yolo = YOLO('assets/yolov8s.pt')

    def __get_colours(self, cls_num):
        base_colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        color_index = cls_num % len(base_colors)
        increments = [(1, -2, 1), (-2, 1, -1), (1, -1, 2)]
        color = [base_colors[color_index][i] + increments[color_index][i] * (cls_num // len(base_colors)) % 256 for i in range(3)]
        return tuple(color)

    def detect_frame(self, cv2_frame, draw_box=False):
        results = self.yolo.track(cv2_frame, stream=False, verbose=False)
        detected_objects = []

        for result in results:
            classes_names = result.names
            for box in result.boxes:
                if box.conf[0] * 100 >= self.threshold:
                    [x1, y1, x2, y2] = box.xyxy[0]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    cls = int(box.cls[0])
                    class_name = classes_names[cls]

                    detected_objects.append({
                        'class': class_name,
                        'confidence': box.conf[0],
                        'coordinates': (x1, y1, x2, y2)
                    })

                    if draw_box:
                        colour = self.__get_colours(cls)
                        cv2.rectangle(cv2_frame, (x1, y1), (x2, y2), colour, 2)

        return cv2_frame, detected_objects
                    