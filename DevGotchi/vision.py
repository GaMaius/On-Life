import cv2
import mediapipe as mp
import numpy as np
import time

class VisionSystem:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # EAR 임계값 (사용자에 맞게 조정 필요)
        self.EYE_AR_THRESH = 0.25
        self.CLOSED_EYE_FRAME = 20  # 이 프레임 이상 눈 감으면 졸음 판정
        self.counter = 0
        
    def calculate_ear(self, eye_points, landmarks):
        # 눈의 수직 거리 (p2-p6, p3-p5) / 수평 거리 (p1-p4) 계산
        # landmarks는 정규화된 좌표이므로 실제 픽셀 좌표 변환 필요 없음 (비율이므로)
        p2_p6 = np.linalg.norm(np.array(landmarks[eye_points[1]]) - np.array(landmarks[eye_points[5]]))
        p3_p5 = np.linalg.norm(np.array(landmarks[eye_points[2]]) - np.array(landmarks[eye_points[4]]))
        p1_p4 = np.linalg.norm(np.array(landmarks[eye_points[0]]) - np.array(landmarks[eye_points[3]]))
        return (p2_p6 + p3_p5) / (2.0 * p1_p4)

    def process_frame(self, frame):
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        status = {
            "has_face": False,
            "is_drowsy": False,
            "bad_posture": False,
            "hp_decay": 0  # HP 감소량
        }

        if results.multi_face_landmarks:
            status["has_face"] = True
            mesh_points = np.array([np.multiply([p.x, p.y], [w, h]).astype(int) for p in results.multi_face_landmarks[0].landmark])
            
            # 1. 졸음 감지 (왼쪽눈: 33,160,158,133,153,144 / 오른쪽눈: 362,385,387,263,373,380)
            # MediaPipe FaceMesh 인덱스 기준 (간소화된 포인트)
            left_eye_idxs = [33, 160, 158, 133, 153, 144]
            right_eye_idxs = [362, 385, 387, 263, 373, 380]
            
            # *실제 구현 시에는 랜드마크 좌표를 가져오는 로직 상세 구현 필요 (여기선 개념 코드)*
            # ear_left = self.calculate_ear(left_eye_idxs, mesh_points) ...
            
            # (약식) 눈꺼풀 랜드마크 사이 거리로 단순 판별
            left_eye_top = mesh_points[159]
            left_eye_bottom = mesh_points[145]
            eye_open_dist = np.linalg.norm(left_eye_top - left_eye_bottom)
            
            if eye_open_dist < 6.0: # 눈 거리가 너무 가까우면 감은 것으로 간주
                self.counter += 1
            else:
                self.counter = 0

            if self.counter >= self.CLOSED_EYE_FRAME:
                status["is_drowsy"] = True
                status["hp_decay"] += 2  # 졸면 HP 크게 감소

            # 2. 자세(거북목) 판정
            # 코(1)와 어깨(Pose가 더 정확하지만 FaceMesh로 추정 시)
            # 화면 하단으로 얼굴이 너무 내려가거나(구부정), 앞으로 쏠림(얼굴 크기 커짐)
            nose_y = mesh_points[1][1]
            if nose_y > h * 0.7: # 화면 아래쪽 30% 영역에 코가 있으면 구부정한 것
                status["bad_posture"] = True
                status["hp_decay"] += 1

        return status, frame