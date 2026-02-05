# vision_engine.py
import cv2
import mediapipe as mp
import numpy as np
from config import Config

class VisionEngine:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def calculate_ear(self, landmarks, indices):
        try:
            top = np.array([landmarks[indices[1]].x, landmarks[indices[1]].y])
            bottom = np.array([landmarks[indices[5]].x, landmarks[indices[5]].y])
            v_dist = np.linalg.norm(top - bottom)
            return v_dist * 10 
        except:
            return 0.3

    def analyze_frame(self, frame):
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 1. Pose Analysis (Turtle Neck)
        pose_results = self.pose.process(rgb)
        posture_score = 0
        
        if pose_results.pose_landmarks:
            landmarks = pose_results.pose_landmarks.landmark
            nose = landmarks[self.mp_pose.PoseLandmark.NOSE.value]
            shoulder_l = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
            shoulder_r = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
            
            shoulder_center_x = (shoulder_l.x + shoulder_r.x) / 2
            shoulder_center_y = (shoulder_l.y + shoulder_r.y) / 2
            
            forward_distance = abs(nose.x - shoulder_center_x)
            vertical_diff = shoulder_center_y - nose.y
            
            # Heuristic Score
            posture_score = (forward_distance * 2.0) + (0.15 - vertical_diff)
            posture_score -= Config.POSTURE_OFFSET_Y 

        # 2. Face Analysis (Drowsiness/Smile)
        face_results = self.face_mesh.process(rgb)
        is_drowsy = False
        is_smiling = False
        is_eye_closed = False
        
        face_landmarks_draw = None

        if face_results.multi_face_landmarks:
            lms = face_results.multi_face_landmarks[0].landmark
            face_landmarks_draw = face_results.multi_face_landmarks[0]
            
            def get_dist(i1, i2):
                x1, y1 = lms[i1].x, lms[i1].y
                x2, y2 = lms[i2].x, lms[i2].y
                return ((x1-x2)**2 + (y1-y2)**2)**0.5

            l_h = get_dist(159, 145)
            l_w = get_dist(33, 133)
            ear_l = l_h / l_w if l_w > 0 else 0

            r_h = get_dist(386, 374)
            r_w = get_dist(362, 263)
            ear_r = r_h / r_w if r_w > 0 else 0
            
            avg_ear = (ear_l + ear_r) / 2.0
            
            if avg_ear < Config.EAR_THRESHOLD:
                is_drowsy = True
                is_eye_closed = True
            
            mouth_w = abs(lms[61].x - lms[291].x)
            mouth_h = abs(lms[13].y - lms[14].y)
            if mouth_w > 0 and (mouth_h / mouth_w) < 0.3:
                is_smiling = True

        return posture_score, is_drowsy, is_smiling, is_eye_closed, face_landmarks_draw

    def check_action_movement(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pose_results = self.pose.process(rgb)
        
        if not pose_results.pose_landmarks:
            return True # Standing up (Absent)
            
        landmarks = pose_results.pose_landmarks.landmark
        
        # 1. Standing Up Check (Shoulder Low Y = High Position)
        mid_shoulder_y = (landmarks[11].y + landmarks[12].y) / 2
        if mid_shoulder_y < 0.2: 
            return True
            
        # 2. Stretching Check (Wrist above shoulder)
        shoulder_l = landmarks[11]
        shoulder_r = landmarks[12]
        wrist_l = landmarks[15]
        wrist_r = landmarks[16]
        
        if wrist_l.y < shoulder_l.y or wrist_r.y < shoulder_r.y:
            return True

        return False