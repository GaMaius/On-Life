import os
import sys
import contextlib

# Utility to suppress C-level stdout/stderr
@contextlib.contextmanager
def suppress_stderr():
    with open(os.devnull, "w") as devnull:
        old_stderr = sys.stderr
        old_stdout = sys.stdout
        sys.stderr = devnull
        sys.stdout = devnull # MediaPipe dumps to stdout mostly
        try:
            yield
        finally:
            sys.stderr = old_stderr
            sys.stdout = old_stdout

print("Starting checks...")

try:
    print("Importing MediaPipe (silenced)...")
    with suppress_stderr():
        import mediapipe as mp
    print("Imported.")

    print("Initializing VisionEngine components (silenced)...")
    with suppress_stderr():
        mp_face_mesh = mp.solutions.face_mesh
        face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )
        
        mp_pose = mp.solutions.pose
        pose = mp_pose.Pose(
            min_detection_confidence=0.5
        )
    print("Initialization success!")

except Exception as e:
    # Restore stdout to print error
    sys.stdout = sys.__stdout__
    print(f"FAILED with error: {e}")

print("Done.")
