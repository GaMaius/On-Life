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
        # 눈 종횡비(EAR) 계산 로직 (간소화)
        # 실제 구현시에는 유클리드 거리 계산 필요
        try:
            top = np.array([landmarks[indices[1]].x, landmarks[indices[1]].y])
            bottom = np.array([landmarks[indices[5]].x, landmarks[indices[5]].y])
            v_dist = np.linalg.norm(top - bottom)
            return v_dist * 10 # 스케일 보정
        except:
            return 0.3

    def analyze_frame(self, frame):
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 1. Pose Analysis (거북목)
        pose_results = self.pose.process(rgb)
        posture_score = 0
        if pose_results.pose_landmarks:
            landmarks = pose_results.pose_landmarks.landmark
            nose = landmarks[self.mp_pose.PoseLandmark.NOSE.value]
            shoulder_l = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
            shoulder_r = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
            
            shoulder_y = (shoulder_l.y + shoulder_r.y) / 2
            # 코와 어깨의 Y거리 차이가 작을수록 거북목 (화면에 가까움)
            posture_score = shoulder_y - nose.y 

        # 2. Face Analysis (졸음/미소)
        face_results = self.face_mesh.process(rgb)
        is_drowsy = False
        is_smiling = False
        
        face_landmarks_draw = None

        if face_results.multi_face_landmarks:
            lms = face_results.multi_face_landmarks[0].landmark
            face_landmarks_draw = face_results.multi_face_landmarks[0]
            
            # 졸음 (왼쪽 눈 위아래 거리)
            # 159(위), 145(아래)
            eye_dist = abs(lms[159].y - lms[145].y) * 100
            if eye_dist < Config.EAR_THRESHOLD * 10:
                is_drowsy = True
            
            # 미소 (입꼬리 61, 291과 입술 위아래 거리 비율)
            mouth_w = abs(lms[61].x - lms[291].x)
            mouth_h = abs(lms[13].y - lms[14].y)
            if mouth_w > 0 and (mouth_h / mouth_w) < 0.3: # 입이 옆으로 길어짐
                is_smiling = True

        return posture_score, is_drowsy, is_smiling, face_landmarks_draw