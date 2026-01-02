# Hand Mouse Controller

Hand-tracking mouse controller powered by MediaPipe, OpenCV, and PyAutoGUI. The script maps your hand motion to the mouse cursor and provides gesture-based clicks, scrolling, and an exit gesture.

## How it works
- Captures frames from your webcam (tries index 1, falls back to 0).
- Uses MediaPipe Hands to track a single hand and detect key landmarks.
- Maps the middle-finger MCP position to screen coordinates with a safe border margin.
- Smooths mouse motion and sends cursor updates via PyAutoGUI.
- Recognizes simple pinch and finger-raise gestures for click, double-click, scroll, and exit.

## Requirements
- Python 3.8+
- Webcam
- Packages: `opencv-python`, `mediapipe==0.10.0`, `pyautogui`, `numpy`, `screeninfo`.

Install dependencies:

```bash
pip install opencv-python mediapipe==0.10.0 pyautogui numpy screeninfo
```

## Running
From the project folder:

```bash
python main.py
```

If the first camera index fails, the script automatically tries the next one.

## Default controls
- Cursor: Move your hand; the middle-finger MCP drives the cursor inside a bordered safe zone.
- Click: Pinch index finger to thumb when they are close (`CLICK_DIST`).
- Double-click: Pinch middle finger to thumb.
- Scroll down: Raise only the index finger (other fingers down past their MCPs).
- Scroll up: Raise index + middle fingers (ring and pinky down past their MCPs).
- Exit: Hold thumb below the wrist for `CLOSE_TIME` seconds.
- ESC: Closes the OpenCV window and ends the program.

## On-screen HUD
- FPS, Hands (detection state), Mouse (active/waiting), MediaPipe status, Frame counter.
- Check: countdown for initial detection window (`CHECK_TIME`).
- Countdown: thumb-down exit timer (`CLOSE_TIME`).

## Configuration (edit in main.py)
| Name | Description | Default |
| --- | --- | --- |
| `CAM_W`, `CAM_H` | Camera capture resolution | 640, 480 |
| `INFERENCE_SKIP` | Frames to skip between MediaPipe runs (kept at 1 = every frame) | 1 |
| `SMOOTHING` | Cursor smoothing factor (0.0-1.0) | 0.5 |
| `CLICK_DIST` | Normalized distance threshold for pinch detection | 0.05 |
| `SCROLL_SPEED` | Scroll delta passed to PyAutoGUI | 25 |
| `BORDER_MARGIN` | Normalized border margin to avoid edge jitter | 0.15 |
| `CHECK_TIME` | Seconds a hand must stay detected before enabling control | 2 |
| `CLOSE_TIME` | Seconds thumb must stay below wrist to exit | 3 |
| `CONTROL_MONITOR_INDEX` | Monitor index used for cursor mapping (`screeninfo`) | 1 |

Adjust these values in [main.py](main.py) to tune detection sensitivity, borders, and gestures.

Behavior notes:
- Controls activate only after continuous detection for `CHECK_TIME`; set it to 0 for immediate activation if desired.
- Exit gesture fires after `CLOSE_TIME` with thumb below wrist.
- `BORDER_MARGIN` and `SMOOTHING` influence cursor stability; tweak to reduce edge jitter or lag.

## Notes and troubleshooting
- PyAutoGUI failsafe is disabled to prevent sudden corners from halting execution; keep this in mind when testing.
- Multi-monitor setups: `CONTROL_MONITOR_INDEX` uses the ordering from `screeninfo.get_monitors()`.
- If MediaPipe fails to import, ensure you installed `mediapipe==0.10.0` and that your Python matches its supported versions.
- If the window is slow, reduce resolution or `SMOOTHING`, or disable drawing of landmarks.
- On permission-restricted systems, camera access may need OS approval.

Optional virtualenv setup:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt  # or the packages listed above
```
