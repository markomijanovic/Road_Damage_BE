
import cv2
import supervision as sv
from inference import get_model
from . import crud, schemas
from dotenv import load_dotenv
import os
import json
import uuid


class VideoProcessor():
    def __init__(self, model_id):
        self.output_dir = "./app/output_videos"
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
    
    def read_metadata(self, path):
        with open(path, "r") as f:
            meta_data = json.load(f)
        return meta_data
    
    def record_processed_video(self, input_path, db, job_id, metadata_file_path, fps = 30):
        detected = {}
        output_path = f"{self.output_dir}/{job_id}.mp4"
        metadata: dict = self.read_metadata(metadata_file_path)
        dynamic_metadata: list[dict] = metadata["dynamicMetadata"]
        last_position = (dynamic_metadata[0]["latitude"], dynamic_metadata[0]["longitude"])

        if input_path == "":
            input_path = "../demovid.mp4"

        cap = cv2.VideoCapture(input_path)

        framerate = cap.get(cv2.CAP_PROP_FPS)
        update_pos_step = int(framerate/30)
       
        if update_pos_step == 0:
            update_pos_step = 1

        tracker = sv.ByteTrack()

        if not cap.isOpened():
            raise Exception("Cannot open input video")

        annotated_frames = []
        current_frame = 0
        while True:
            if current_frame % update_pos_step == 0:
                ind = current_frame // update_pos_step
                last_position = (dynamic_metadata[ind]["latitude"], dynamic_metadata[ind]["longitude"])
            
            success, frame = cap.read()
            if not success:
                break
            

            output_frame = self.process_frame(frame, tracker, detected, last_position)
           
            annotated_frames.append(output_frame)

            current_frame += 1

        cap.release()
      
        for k, v in detected.items():
            crud.create_pothole(db=db, pothole=schemas.PotholeCreate(**v))

        if len(annotated_frames) == 0:
            raise Exception("No frames processed")

        height, width, layers = annotated_frames[0].shape

        # Correct fourcc for MP4
        
        #fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        fourcc = cv2.VideoWriter_fourcc(*'H264')
        video = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        for img in annotated_frames:
            video.write(img)

        video.release()
        cv2.destroyAllWindows()

        print("Saved:", output_path)

