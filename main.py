import cv2
import mediapipe as mp
import pyautogui
import math
import time
import numpy as np
from screeninfo import get_monitors

# ---------------- CONFIG ----------------
CAM_W, CAM_H = 640, 480
INFERENCE_SKIP = 1       # run mediapipe every frame for better detection
SMOOTHING = 0.5         # mouse smoothing (0.0 - 1.0)
CLICK_DIST = 0.05
SCROLL_SPEED = 25        # scroll speed
BORDER_MARGIN = 0.15      # 10% border margin (adjust: 0.05-0.15)
CHECK_TIME = 2            # time to check hand detection in seconds
CLOSE_TIME = 3            # time to hold thumb down to close program
CONTROL_MONITOR_INDEX = 1  # monitor index for mouse control
# ----------------------------------------

mp_hands = None
mp_drawing = None
hands = None
use_legacy = False
prev_scroll_y = None # to track thumb down time
prev_x, prev_y = 0, 0
clicking = False
double_clicking = False
frame_count = 0
prev_time = time.time()
mouse_initialized = False
hands_detected = False
prev_scroll_y = None
hands_checked = False
remaining_close = 0
remaining_check = 0
show_check = False

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.001  # Minimal pause for faster response

# Test PyAutoGUI functionality
print("Testing PyAutoGUI...")
try:
    current_pos = pyautogui.position()
    print(f"Current mouse position: {current_pos}")
    print(f"Screen size: {pyautogui.size()}")
    print("PyAutoGUI is working!")
except Exception as e:
    print(f"PyAutoGUI error: {e}")
    print("Mouse control may not work properly")

# Try camera index 1 first, fallback to 0
cap = cv2.VideoCapture(1)
if not cap.isOpened():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open camera")
        exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)

screen_w, screen_h = pyautogui.size()

# Initialize MediaPipe Hand Tracking
print("Initializing MediaPipe...")

monitors = get_monitors()
monitor = monitors[CONTROL_MONITOR_INDEX]

MON_X, MON_Y = monitor.x, monitor.y
MON_W, MON_H = monitor.width, monitor.height


try:
    # Try to import and initialize MediaPipe solutions
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    print("MediaPipe solutions imported successfully")
    
    # Initialize hands with error handling
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        model_complexity=0,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    use_legacy = True
    print("MediaPipe Hands initialized successfully!")
    
except AttributeError as e:
    print(f"MediaPipe solutions not available: {e}")
    print("Please install: pip install mediapipe==0.10.0")
except Exception as e:
    print(f"MediaPipe initialization error: {e}")
    print("Trying alternative approach...")
    
if not hands:
    print("ERROR: MediaPipe hand tracking not available")
    print("Please install MediaPipe: pip install mediapipe==0.10.0")
    exit(1)

# Test MediaPipe with a sample frame
print("Testing MediaPipe with camera...")
test_success, test_frame = cap.read()
if test_success:
    try:
        test_rgb = cv2.cvtColor(test_frame, cv2.COLOR_BGR2RGB)
        test_result = hands.process(test_rgb)
        print("MediaPipe processing test: SUCCESS")
    except Exception as e:
        print(f"MediaPipe processing test failed: {e}")
        print("Continuing anyway...")
else:
    print("Warning: Could not capture test frame")


while True:
    success, frame = cap.read()
    if not success:
        print("Error: Failed to read from camera")
        break

    frame = cv2.flip(frame, 1)
    frame_count += 1

    # Process every frame for better detection
    if hands:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        try:
            result = hands.process(rgb)
            
            # Debug output every 2 seconds
            # if frame_count % 60 == 0:
            #     if result and result.multi_hand_landmarks:
            #         print(f"✓ Hand detected at frame {frame_count}")
            #     else:
            #         print(f"✗ No hand detected at frame {frame_count}")
            
            hands_detected = bool(result and result.multi_hand_landmarks) # Check if hands are detected
            
        except Exception as e:
            print(f"MediaPipe error at frame {frame_count}: {e}")
            result = None
            hands_detected = False
            
        # Count time for hands detected
        if hands_detected:
            if hands_detected_time is None:
                hands_detected_time = time.time()
                remaining_check = CHECK_TIME
                show_check = True
            elif not hands_checked:
                elapsed_time = time.time() - hands_detected_time
                remaining_check = max(0, CHECK_TIME - elapsed_time)
                if elapsed_time >= CHECK_TIME:
                    hands_checked = True
                    show_check = False
        else:
            hands_detected_time = None
            hands_checked = False
            show_check = False
            remaining_check = 0
        
        if hands_detected and result and result.multi_hand_landmarks and hands_checked:
            hand = result.multi_hand_landmarks[0]
            
            # Get index finger tip (landmark 8) and thumb tip (landmark 4)
            wrist = hand.landmark[0]
            index_tip = hand.landmark[8]
            thumb_tip = hand.landmark[4]
            middle_tip = hand.landmark[12]
            ring_tip = hand.landmark[16]
            pinky_tip = hand.landmark[20]
            middle_finger_mcp = hand.landmark[9]

            # Clamp hand coords to the camera safe zone, then map to screen
            cam_x = np.clip(middle_finger_mcp.x, BORDER_MARGIN, 1 - BORDER_MARGIN)
            cam_y = np.clip(middle_finger_mcp.y, BORDER_MARGIN, 1 - BORDER_MARGIN)
            norm_x = (cam_x - BORDER_MARGIN) / (1 - 2 * BORDER_MARGIN)
            norm_y = (cam_y - BORDER_MARGIN) / (1 - 2 * BORDER_MARGIN)
            target_x = int(MON_X + norm_x * MON_W)
            target_y = int(MON_Y + norm_y * MON_H)

            # Draw hand landmarks if drawing utils available
            if mp_drawing:
                mp_drawing.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)

            # Smooth mouse movement
            if not mouse_initialized:
                curr_x, curr_y = target_x, target_y
                mouse_initialized = True
                print(f"Mouse control initialized at: ({curr_x}, {curr_y})")
            else:
                curr_x = int(prev_x + (target_x - prev_x) * SMOOTHING)
                curr_y = int(prev_y + (target_y - prev_y) * SMOOTHING)

            # Move mouse
            try:
                if index_tip.y < thumb_tip.y and middle_tip.y < thumb_tip.y and ring_tip.y < thumb_tip.y and pinky_tip.y < thumb_tip.y:  # Only move if fingers are down
                    pyautogui.moveTo(curr_x, curr_y, duration=0)
                    prev_x, prev_y = curr_x, curr_y
            except Exception as e:
                print(f"Mouse movement error: {e}")
            
            # Add border constraint (margin from edges)
            border_left = int(MON_X + MON_W * BORDER_MARGIN)
            border_right = int(MON_X + MON_W * (1 - BORDER_MARGIN))
            border_top = int(MON_Y + MON_H * BORDER_MARGIN)
            border_bottom = int(MON_Y + MON_H * (1 - BORDER_MARGIN))
            
            # Draw border on frame for visualization
            cv2.rectangle(frame, (int(BORDER_MARGIN * CAM_W), int(BORDER_MARGIN * CAM_H)), 
                        (int(CAM_W * (1 - BORDER_MARGIN)), int(CAM_H * (1 - BORDER_MARGIN))),(0, 255, 0), 2)
                
            index_finger_mcp = hand.landmark[5]

            index_raised = index_tip.y < thumb_tip.y
            other_fingers_down_ex_index = middle_tip.y > middle_finger_mcp.y and ring_tip.y > middle_finger_mcp.y and pinky_tip.y > middle_finger_mcp.y
            
            if index_raised and other_fingers_down_ex_index:
                pyautogui.scroll(-SCROLL_SPEED)  # Scroll down

            index_middle_raised = index_tip.y < thumb_tip.y and middle_tip.y < thumb_tip.y
            other_fingers_down_ex_index_middle = ring_tip.y > middle_finger_mcp.y and pinky_tip.y > middle_finger_mcp.y
            
            if index_middle_raised and other_fingers_down_ex_index_middle:  # Check if middle finger is also raised
                pyautogui.scroll(SCROLL_SPEED)  # Scroll up
                
            # Check for click gesture
            dis = math.sqrt((index_tip.x - thumb_tip.x) ** 2 + (index_tip.y - thumb_tip.y) ** 2)
            if dis < CLICK_DIST:
                if not clicking:
                    try:
                        pyautogui.click()
                        print("Click!")
                        clicking = True
                    except Exception as e:
                        print(f"Click error: {e}")
            else:
                clicking = False
                
            # Check for double click gesture
            dis = math.sqrt((thumb_tip.x - middle_tip.x) ** 2 + (thumb_tip.y - middle_tip.y) ** 2)
            if dis < CLICK_DIST:
                if not double_clicking:
                    try:
                        pyautogui.doubleClick()
                        print("Double Click!")
                        double_clicking = True
                    except Exception as e:
                        print(f"Double Click error: {e}")
            else:
                double_clicking = False
                
            # if thumb is below wrist more than 2 seconds, close program
            if thumb_tip.y > wrist.y:
                if prev_scroll_y is None:
                    prev_scroll_y = time.time()
                else:
                    elapsed = time.time() - prev_scroll_y
                    remaining_close = max(0, CLOSE_TIME - elapsed)
                    print(f"Thumb down countdown: {remaining_close:.1f}s")
                    if elapsed > CLOSE_TIME:
                        print("Thumb down detected for 5 seconds - exiting program")
                        break
            else:
                prev_scroll_y = None
        else:
            hands_detected = False
            prev_scroll_y = None
            hands_checked = False

    # FPS display
    curr_time = time.time()
    time_diff = curr_time - prev_time
    fps = int(1 / time_diff) if time_diff > 0 else 0
    prev_time = curr_time
    
    # Display status information
    cv2.putText(frame, f"FPS: {fps}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(frame, f"Hands: {'YES' if hands_detected else 'NO'}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if hands_detected else (0, 0, 255), 2)
    cv2.putText(frame, f"Mouse: {'Active' if mouse_initialized else 'Waiting'}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if mouse_initialized else (0, 255, 255), 2)
    cv2.putText(frame, f"MediaPipe: {'OK' if hands and use_legacy else 'ERROR'}", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if hands and use_legacy else (0, 0, 255), 2)
    cv2.putText(frame, f"Frame: {frame_count}", (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, f"Check: {remaining_check:.1f}s" if show_check else "Check: N/A", (10, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if show_check else (255, 255, 255), 2)
    cv2.putText(frame, f"Coutndown: {remaining_close:.1f}s" if prev_scroll_y else "Countdown: N/A", (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if prev_scroll_y else (255, 255, 255), 2)
    
    # show the frame
    cv2.imshow("Hand Mouse (High FPS)", frame)
    if cv2.waitKey(1) & 0xFF == 27:  # ESC key
        break

print("Cleaning up...")
cap.release()
cv2.destroyAllWindows()
print("Done!")
