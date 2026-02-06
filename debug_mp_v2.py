import os
import sys

class SuppressOutput:
    def __enter__(self):
        # Flush Python streams
        sys.stdout.flush()
        sys.stderr.flush()

        # Save original file descriptors
        self._stdout_fd = os.dup(1)
        self._stderr_fd = os.dup(2)

        # Open devnull
        self._devnull = os.open(os.devnull, os.O_RDWR)

        # Replace stdout/stderr with devnull
        os.dup2(self._devnull, 1)
        os.dup2(self._devnull, 2)

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Flush before restoring
        sys.stdout.flush()
        sys.stderr.flush()

        # Restore original file descriptors
        os.dup2(self._stdout_fd, 1)
        os.dup2(self._stderr_fd, 2)

        # Close duplicated fds and devnull
        os.close(self._stdout_fd)
        os.close(self._stderr_fd)
        os.close(self._devnull)

print("Testing FD suppression...")

try:
    print("Initializing MediaPipe with FD suppression...")
    with SuppressOutput():
        import mediapipe as mp
        # Initialize components that cause logging
        mp_face_mesh = mp.solutions.face_mesh
        face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )
        face_mesh.close()
    
    print("Initialization success! If you see this clean, it worked.")

except Exception as e:
    print(f"FAILED with error: {e}")
