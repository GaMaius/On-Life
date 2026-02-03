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
            
            # 어깨 중심점 계산
            shoulder_center_x = (shoulder_l.x + shoulder_r.x) / 2
            shoulder_center_y = (shoulder_l.y + shoulder_r.y) / 2
            
            # 거북목 판정: 머리(코)가 어깨보다 앞으로 나온 정도
            # X축: 머리가 어깨보다 앞에(카메라 방향으로) 나왔는지
            # Y축: 머리가 어깨보다 아래에 있는지 (화면에서 아래 = 얼굴이 카메라에 가까움)
            
            # 주요 지표: X축 차이 (머리가 어깨보다 얼마나 앞으로 나왔는지)
            forward_distance = abs(nose.x - shoulder_center_x)
            
            # 보조 지표: Y축 차이 (값이 작을수록 거북목 - 머리가 어깨 높이에 가까움)
            vertical_diff = shoulder_center_y - nose.y
            
            # 거북목 점수 계산
            # forward_distance가 클수록 거북목 가능성 높음
            # vertical_diff가 작을수록 거북목 가능성 높음
            posture_score = (forward_distance * 2.0) + (0.15 - vertical_diff)
            
            # 보정값 적용
            posture_score -= Config.POSTURE_OFFSET_Y 

        # 2. Face Analysis (졸음/미소)
        face_results = self.face_mesh.process(rgb)
        is_drowsy = False
        is_smiling = False
        
        face_landmarks_draw = None

        if face_results.multi_face_landmarks:
            lms = face_results.multi_face_landmarks[0].landmark
            face_landmarks_draw = face_results.multi_face_landmarks[0]
            
            # 졸음 (눈 감음 판정 - Normalized EAR)
            # Left Eye: Top(159), Bottom(145), Inner(33), Outer(133)
            # Right Eye: Top(386), Bottom(374), Inner(362), Outer(263)
            
            def get_dist(i1, i2):
                x1, y1 = lms[i1].x, lms[i1].y
                x2, y2 = lms[i2].x, lms[i2].y
                return ((x1-x2)**2 + (y1-y2)**2)**0.5

            # Left Eye EAR
            l_h = get_dist(159, 145)
            l_w = get_dist(33, 133)
            ear_l = l_h / l_w if l_w > 0 else 0

            # Right Eye EAR
            r_h = get_dist(386, 374)
            r_w = get_dist(362, 263)
            ear_r = r_h / r_w if r_w > 0 else 0
            
            avg_ear = (ear_l + ear_r) / 2.0
            
            # Config.EAR_THRESHOLD (0.18) 보다 작으면 눈 감음
            if avg_ear < Config.EAR_THRESHOLD:
                is_drowsy = True
            
            # 미소 (입꼬리 61, 291과 입술 위아래 거리 비율)
            mouth_w = abs(lms[61].x - lms[291].x)
            mouth_h = abs(lms[13].y - lms[14].y)
            if mouth_w > 0 and (mouth_h / mouth_w) < 0.3: # 입이 옆으로 길어짐
                is_smiling = True

        return posture_score, is_drowsy, is_smiling, face_landmarks_draw

    def check_action_movement(self, frame):
        """스트레칭/일어서기 감지 (어깨 위로 손을 올리거나, 일어서기)"""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pose_results = self.pose.process(rgb)
        
        if not pose_results.pose_landmarks:
            # 사람이 프레임에서 사라짐 (일어서서 나감 or 화면 밖으로 이동)
            return True
            
        landmarks = pose_results.pose_landmarks.landmark
        
        # 1. 일어서기 감지 (어깨가 화면 상단으로 이동)
        mid_shoulder_y = (landmarks[11].y + landmarks[12].y) / 2
        if mid_shoulder_y < 0.2: 
            return True
            
        # 2. 스트레칭 감지 (손목이 어깨보다 높이 올라감)
        # Y좌표는 위쪽이 0이므로, 값이 작을수록 높이 있는 것
        shoulder_l = landmarks[11]
        shoulder_r = landmarks[12]
        wrist_l = landmarks[15]
        wrist_r = landmarks[16]
        
        # 한쪽 손이라도 어깨보다 높이 있으면 스트레칭으로 간주
        if wrist_l.y < shoulder_l.y or wrist_r.y < shoulder_r.y:
            return True

        return False