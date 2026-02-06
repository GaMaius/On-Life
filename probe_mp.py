import mediapipe as mp
print(f"Mediapipe version: {getattr(mp, '__version__', 'unknown')}")
print(f"Mediapipe file: {getattr(mp, '__file__', 'unknown')}")
print(f"Mediapipe dir: {dir(mp)}")
try:
    print(f"Solutions: {mp.solutions}")
except AttributeError as e:
    print(f"Error accessing solutions: {e}")
