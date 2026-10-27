
import cv2
import supervision as sv
from . import crud, schemas
import os


class VideoProcessor():
    def __init__(self, model_id):
        self.output_dir = "./app/output_videos"
        if os.getenv("ROBOFLOW_INFERENCE_BACKEND", "local") == "hosted":
            from .hosted_inference import HostedModel
            self.model = HostedModel(model_id, os.environ["ROBOFLOW_API_KEY"])
        else:
            from inference import get_model
            self.model = get_model(model_id=model_id, api_key=os.environ["ROBOFLOW_API_KEY"])
        
         

    def process_frame(self, frame, tracker, detected, position):
      

        results = self.model.infer(frame, verbose=False, confidence=0.1, iou_threshold=0.5)[0]
       
        detections = sv.Detections.from_inference(results)
        tracked = tracker.update_with_detections(detections)

        box_annotator = sv.BoxAnnotator()
        label_annotator = sv.LabelAnnotator()

        labels = []

        for i in range(len(tracked)):
            curr_id = tracked.tracker_id[i] 

            
            detected[curr_id] = {"class_name": tracked.data["class_name"][i], "latitude": position[0], "longitude": position[1] ,"confidence": tracked.confidence[i]}
          
                
            tracker_id = curr_id
            class_name = tracked.data["class_name"][i]
            conf = tracked.confidence[i]
            labels.append(f"ID {tracker_id} | {class_name} {conf:.2f}")

        annotated_image = frame.copy()
        annotated_image = box_annotator.annotate(scene=annotated_image, detections=tracked)
        annotated_image = label_annotator.annotate(scene=annotated_image, detections=tracked, labels=labels)

        return annotated_image
    
    def record_processed_video(self, input_path, db, job_id, metadata_file_path, fps=30):
        from pathlib import Path
        import math
        from .metadata import read_positions, position_at_frame

        positions = read_positions(metadata_file_path)
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        output_path = str(Path(self.output_dir) / f"{job_id}.mp4")
        cap = cv2.VideoCapture(input_path)
        writer = None
        completed = False
        detected = {}
        try:
            if not cap.isOpened():
                raise ValueError("Cannot open input video")
            source_fps = cap.get(cv2.CAP_PROP_FPS)
            if not math.isfinite(source_fps) or source_fps <= 0:
                raise ValueError("Invalid video frame rate")
            tracker = sv.ByteTrack()
            frame_number = 0
            while True:
                success, frame = cap.read()
                if not success:
                    break
                position = position_at_frame(positions, frame_number, source_fps)
                annotated = self.process_frame(frame, tracker, detected, position)
                if writer is None:
                    height, width = annotated.shape[:2]
                    writer = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*"mp4v"), source_fps, (width, height))
                    if not writer.isOpened():
                        raise ValueError("Cannot create output video")
                writer.write(annotated)
                frame_number += 1
            if not frame_number:
                raise ValueError("No frames processed")
            for detection in detected.values():
                crud.create_pothole(db=db, pothole=schemas.PotholeCreate(**detection))
            completed = True
        finally:
            cap.release()
            if writer is not None:
                writer.release()
            if not completed:
                Path(output_path).unlink(missing_ok=True)
        return output_path
