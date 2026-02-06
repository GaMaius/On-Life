import cv2
import numpy as np
import mediapipe as mp
import os
import sys
import time

class SuppressOutput:
    def __enter__(self):
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self._devnull = open(os.devnull, 'w')
        sys.stdout = self._devnull
        sys.stderr = self._devnull

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr
        if self._devnull:
            self._devnull.close()

class VisionEngine:
    def __init__(self):
        self.pose = None
        self.mp_pose = None
        
        try:
            # MediaPipe Init (Removed SuppressOutput for debug)
            self.mp_pose = mp.solutions.pose
            self.face_mesh = mp.solutions.face_mesh.FaceMesh(
                max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.5
            )
            self.pose = self.mp_pose.Pose(min_detection_confidence=0.5)
            
            # --- 자세 보정 및 상태 관리 변수 ---
            self.base_posture_score = 0
            self.bad_posture_start_time = None
            print("[DEBUG] 시각화 지원 비전 엔진 로딩 완료!")
        except Exception as e:
            print(f"[ERROR] 비전 엔진 초기화 실패: {e}")
            import traceback
            traceback.print_exc()
            self.pose = None

    def calibrate_base_posture(self, frame):
        """현재 주인님의 자세를 '바른 자세(0점)'로 설정합니다."""
        if frame is None: return
        score, _, _, _, _ = self.analyze_frame(frame, is_calibrating=True)
        self.base_posture_score = score
        print(f"[SYSTEM] 자세 보정 완료! 기준 점수: {self.base_posture_score:.2f}")

    def analyze_frame(self, frame, is_calibrating=False):
        print("[DEBUG] Analyzing frame...")
        if frame is None:
            return 0, False, False, False, None
            
        h, w, _ = frame.shape
        # [DEBUG] 그리기 테스트: 프레임 좌측 상단에 빨간 원 강제 표시
        cv2.circle(frame, (30, 30), 10, (0, 0, 255), -1) 
        
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        if self.pose is None or self.face_mesh is None:
            return 0, False, False, False, None

        # 1. Pose Analysis (자세 분석 및 시각화)
        pose_results = self.pose.process(rgb)
        posture_score = 0
        
        if pose_results.pose_landmarks:
            print("[DEBUG] 사람 감지됨!") # 너무 자주 찍히면 주석 처리
            lms = pose_results.pose_landmarks.landmark
            nose = lms[self.mp_pose.PoseLandmark.NOSE.value]
            sh_l = lms[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
            sh_r = lms[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
            
            # 어깨 중심점
            sh_x = (sh_l.x + sh_r.x) / 2
            sh_y = (sh_l.y + sh_r.y) / 2
            
            # [수정] 복합 로직: (1) 중앙 정렬 여부 + (2) 고개 숙임(거북목) 감지
            
            # [수정] 3분할 로직 (Left / Center / Right)
            # 화면을 정확히 3등분하여 가운데(33%~66%)만 바른 자세로 인정
            
            safe_min_x, safe_max_x = 0.33, 0.66
            is_centered = (safe_min_x <= nose.x <= safe_max_x)
            
            # 2. Y축 고개 숙임 확인 (기존 유지)
            current_vertical_diff = sh_y - nose.y
            diff_from_base = self.base_posture_score - current_vertical_diff
            
            if is_calibrating:
                return current_vertical_diff, False, False, False, None

            # 판정 로직
            is_bad_posture = False
            status_text = "Good"
            
            # (1) 좌우 기울임/이동 판정
            if nose.x < safe_min_x:
                is_bad_posture = True
                status_text = "Bad: Leaning Left (<<)"
            elif nose.x > safe_max_x:
                is_bad_posture = True
                status_text = "Bad: Leaning Right (>>)"
                
            # (2) 고개 숙임 판정 (절대위치 or 상대위치)
            elif nose.y > 0.85:
                is_bad_posture = True
                status_text = "Bad: Too Low"
            elif diff_from_base > 0.05:
                is_bad_posture = True
                status_text = "Bad: Head Down"
            
            posture_score = 50.0 if is_bad_posture else 5.0

            # --- [시각화: 3분할 가이드라인] ---
            h_h, w_w = frame.shape[:2]
            
            # 3등분 선 그리기 (흰색 점선 느낌으로)
            x1 = int(0.33 * w_w)
            x2 = int(0.66 * w_w)
            
            # 상태에 따른 색상
            status_color = (0, 0, 255) if is_bad_posture else (0, 255, 0)
            
            # 중앙 Safe Zone 표시 (박스 대신 양쪽 경계선 강조)
            cv2.line(frame, (x1, 0), (x1, h_h), (255, 255, 0), 2)
            cv2.line(frame, (x2, 0), (x2, h_h), (255, 255, 0), 2)
            
            # 상단 영역 이름 표시
            cv2.putText(frame, "LEFT", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
            cv2.putText(frame, "CENTER (SAFE)", (x1 + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            cv2.putText(frame, "RIGHT", (x2 + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)

            # 코 & 어깨 점
            nx, ny = int(nose.x * w_w), int(nose.y * h_h)
            cv2.circle(frame, (nx, ny), 8, status_color, -1)
            
            # 디버깅 정보 표시
            cv2.putText(frame, status_text, (x1 + 10, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
            
            # 지속 시간 경고
            if is_bad_posture:
                if self.bad_posture_start_time is None:
                    self.bad_posture_start_time = time.time()
                elapsed = int(time.time() - self.bad_posture_start_time)
                cv2.putText(frame, f"Warn: {elapsed}s", (x1 + 10, 90), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                self.bad_posture_start_time = None
 
        else:
            print("[DEBUG] 사람 미감지") 
            posture_score = 50.0 
            cv2.putText(frame, "No User", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)

        return posture_score, False, False, False, None