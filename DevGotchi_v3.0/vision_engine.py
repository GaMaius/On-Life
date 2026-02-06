import cv2
import numpy as np
import mediapipe as mp
import os
import sys
from config import Config

class SuppressOutput:
    def __enter__(self):
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        
        # Open devnull
        self._devnull = open(os.devnull, 'w')
        
        # Redirect Python streams
        sys.stdout = self._devnull
        sys.stderr = self._devnull

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore Python streams
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr
        
        # Close devnull
        if self._devnull:
            self._devnull.close()

class VisionEngine:
    def __init__(self):
        try:
            # 1. Face Mesh & Pose 초기화 (로그 숨김)
            with SuppressOutput():
                # 어떤 버전에서도 solutions를 찾을 수 있게 강제 지정
                self.mp_face_mesh = mp.solutions.face_mesh
                self.mp_pose = mp.solutions.pose
                
                self.face_mesh = self.mp_face_mesh.FaceMesh(
                    max_num_faces=1,
                    refine_landmarks=True,
                    min_detection_confidence=0.5
                )
                
                self.pose = self.mp_pose.Pose(
                    min_detection_confidence=0.5
                )
            print("[DEBUG] MediaPipe 로딩 완료!")
        except Exception as e:
            print(f"[ERROR] 비전 엔진 초기화 실패: {e}")

    def analyze_frame(self, frame):
        if frame is None: return 0, False, False, False, None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 1. Pose (자세)
        pose_res = self.pose.process(rgb)
        score = 0
        if pose_res.pose_landmarks: score = 10
            
        # 2. Face (얼굴)
        face_res = self.face_mesh.process(rgb)
        is_drowsy = False
        lms = None
        if face_res.multi_face_landmarks:
            lms = face_res.multi_face_landmarks[0]
            
        return score, is_drowsy, False, False, lms
        
    def calculate_ear(self, landmarks, indices):
        try:
            # 안전하게 landmark 리스트 확인
            top = np.array([landmarks[indices[1]].x, landmarks[indices[1]].y])
            bottom = np.array([landmarks[indices[5]].x, landmarks[indices[5]].y])
            v_dist = np.linalg.norm(top - bottom)
            return v_dist * 10 
        except Exception:
            return 0.3

    def analyze_frame(self, frame):
        if frame is None:
            return 0, False, False, False, None
            
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 1. Pose Analysis (Turtle Neck)
        pose_results = self.pose.process(rgb)
        posture_score = 0
        
        if pose_results.pose_landmarks:
            landmarks = pose_results.pose_landmarks.landmark
            # Enum을 통해 명시적으로 좌표 참조
            nose = landmarks[self.mp_pose.PoseLandmark.NOSE.value]
            shoulder_l = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
            shoulder_r = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
            
            shoulder_center_x = (shoulder_l.x + shoulder_r.x) / 2
            shoulder_center_y = (shoulder_l.y + shoulder_r.y) / 2
            
            forward_distance = abs(nose.x - shoulder_center_x)
            vertical_diff = shoulder_center_y - nose.y
            
            # Heuristic Score 계산
            posture_score = (forward_distance * 2.0) + (0.15 - vertical_diff)
            # Config에 해당 값이 없는 경우 0으로 처리
            posture_score -= getattr(Config, 'POSTURE_OFFSET_Y', 0) 

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

            # 눈 감음 감지 (EAR 계산)
            l_h = get_dist(159, 145)
            l_w = get_dist(33, 133)
            ear_l = l_h / l_w if l_w > 0 else 0

            r_h = get_dist(386, 374)
            r_w = get_dist(362, 263)
            ear_r = r_h / r_w if r_w > 0 else 0
            
            avg_ear = (ear_l + ear_r) / 2.0
            
            if avg_ear < getattr(Config, 'EAR_THRESHOLD', 0.2):
                is_drowsy = True
                is_eye_closed = True
            
            # 웃음 감지 (입 가로 대비 세로 비율)
            mouth_w = abs(lms[61].x - lms[291].x)
            mouth_h = abs(lms[13].y - lms[14].y)
            if mouth_w > 0 and (mouth_h / mouth_w) < 0.3:
                is_smiling = True

        return posture_score, is_drowsy, is_smiling, is_eye_closed, face_landmarks_draw

    def check_action_movement(self, frame):
        if frame is None: return False
        
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pose_results = self.pose.process(rgb)
        
        if not pose_results.pose_landmarks:
            return True # 자리 비움으로 간주
            
        landmarks = pose_results.pose_landmarks.landmark
        
        # 1. 일어서기 체크 (어깨 위치가 화면 상단에 가까움)
        mid_shoulder_y = (landmarks[11].y + landmarks[12].y) / 2
        if mid_shoulder_y < 0.2: 
            return True
            
        # 2. 기지개 체크 (손목이 어깨보다 높음)
        if landmarks[15].y < landmarks[11].y or landmarks[16].y < landmarks[12].y:
            return True

        return False