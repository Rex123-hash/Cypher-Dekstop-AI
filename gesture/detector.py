"""
Gesture Controller — OpenCV + MediaPipe hand tracking (Tasks API, mediapipe 0.10+).
Runs in a background thread via webcam.

Gestures:
  Open palm  → pause / dismiss overlay
  Fist       → stop / cancel current action
  Thumbs up  → confirm / yes
  Swipe left → dismiss / previous
  Swipe right→ accept / next
"""
import logging
import os
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

import numpy as np

import config

logger = logging.getLogger("nexus.gesture")

MODEL_PATH = str(Path(__file__).parent.parent / "assets" / "hand_landmarker.task")


class Gesture(str, Enum):
    OPEN_PALM   = "open_palm"
    FIST        = "fist"
    THUMBS_UP   = "thumbs_up"
    SWIPE_LEFT  = "swipe_left"
    SWIPE_RIGHT = "swipe_right"
    NONE        = "none"


class GestureDetector:
    COOLDOWN = 1.2

    def __init__(self, callback: Callable[[Gesture], None]):
        self.callback = callback
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_gesture_time = 0.0
        self._swipe_buffer: list[float] = []
        self._landmarker = None
        self._available = False

        if not os.path.exists(MODEL_PATH):
            logger.warning(
                f"Hand landmarker model not found at {MODEL_PATH}. "
                "Gesture control disabled. Run setup.bat to download it."
            )
            return

        try:
            self._available = True  # defer actual load to _run()
        except Exception as e:
            logger.warning(f"Gesture init failed: {e}. Gesture control disabled.")

    def start(self):
        if not config.GESTURE_ENABLED or not self._available:
            logger.info("Gesture control disabled.")
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Gesture detector started.")

    def stop(self):
        self._running = False

    def _run(self):
        import cv2
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode

        try:
            options = HandLandmarkerOptions(
                base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH),
                running_mode=RunningMode.VIDEO,
                num_hands=1,
                min_hand_detection_confidence=0.7,
                min_hand_presence_confidence=0.5,
                min_tracking_confidence=0.6,
            )
            self._landmarker = HandLandmarker.create_from_options(options)
        except Exception as e:
            logger.warning(f"MediaPipe init failed: {e}. Gesture control disabled.")
            return

        os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
        cap = cv2.VideoCapture(config.WEBCAM_INDEX, cv2.CAP_MSMF)
        if not cap.isOpened():
            logger.warning(f"Could not open webcam {config.WEBCAM_INDEX}.")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        cap.set(cv2.CAP_PROP_FPS, 30)

        consecutive_failures = 0
        while self._running:
            ret, frame = cap.read()
            if not ret:
                consecutive_failures += 1
                if consecutive_failures >= 30:
                    logger.warning("Webcam unavailable after 30 attempts. Gesture control disabled.")
                    break
                time.sleep(0.1)
                continue
            consecutive_failures = 0

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            timestamp_ms = int(time.monotonic() * 1000)

            try:
                result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
            except Exception as e:
                logger.debug(f"Detection error: {e}")
                continue

            gesture = Gesture.NONE
            if result.hand_landmarks:
                lm = result.hand_landmarks[0]
                gesture = self._classify(lm)
                self._track_swipe(lm)
            else:
                swipe = self._detect_swipe()
                if swipe != Gesture.NONE:
                    gesture = swipe

            if gesture != Gesture.NONE:
                now = time.time()
                if now - self._last_gesture_time > self.COOLDOWN:
                    self._last_gesture_time = now
                    logger.info(f"Gesture: {gesture.value}")
                    self.callback(gesture)

        cap.release()

    def _classify(self, lm) -> Gesture:
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]
        thumb_tip = lm[4]
        thumb_ip  = lm[3]

        fingers_up = [lm[tips[i]].y < lm[pips[i]].y for i in range(4)]
        n_up = sum(fingers_up)
        thumb_up = thumb_tip.y < thumb_ip.y

        if n_up == 0 and not thumb_up:
            return Gesture.FIST
        if n_up == 4 and thumb_up:
            return Gesture.OPEN_PALM
        if n_up == 0 and thumb_up:
            return Gesture.THUMBS_UP
        return Gesture.NONE

    def _track_swipe(self, lm):
        self._swipe_buffer.append(lm[0].x)
        if len(self._swipe_buffer) > 15:
            self._swipe_buffer.pop(0)

    def _detect_swipe(self) -> Gesture:
        if len(self._swipe_buffer) < 10:
            return Gesture.NONE
        delta = self._swipe_buffer[-1] - self._swipe_buffer[0]
        self._swipe_buffer.clear()
        if delta < -0.25:
            return Gesture.SWIPE_LEFT
        if delta > 0.25:
            return Gesture.SWIPE_RIGHT
        return Gesture.NONE
