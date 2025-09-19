import cv2
import numpy as np
import requests
import imutils
import time

def detect_colors_with_live_hsv(use_esp32_cam=True, esp32_url='URL'):
    if use_esp32_cam:
        print(f"Connecting to ESP32-CAM at: {esp32_url}")
        try:
            response = requests.get(esp32_url, timeout=5)
            if response.status_code != 200:
                print("Error: Could not connect to ESP32-CAM stream")
                return
        except requests.exceptions.RequestException:
            print("Error: Could not reach ESP32-CAM. Check IP address and network connection.")
            return
    else:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not access local camera")
            return


    color_ranges = {
        'healthy_green': ([40, 40, 40], [90, 255, 255]),
        'pale_green': ([35, 30, 80], [50, 120, 200]),
        'chlorotic_yellow': ([25, 50, 50], [40, 255, 255]),
        'necrotic_brown': ([5, 10, 10], [20, 180, 120])
    }

    zoom_factor = 1.0
    zoom_step = 0.2
    pan_x, pan_y = 0, 0
    pan_step = 20
    
    print("="*80)
    print("MOSS STRESS DETECTION WITH LIVE HSV VALUES")
    print("="*80)
    print("Controls:")
    print("  '+' or '=' : Zoom in")
    print("  '-' or '_' : Zoom out")
    print("  'r' : Reset zoom and pan")
    print("  Arrow keys : Pan when zoomed in")
    print("  'q' : Quit")
    print("="*80)
    print()

    frame_count = 0
    last_print_time = time.time()
    print_interval = 1.0  # Print HSV values every 1 second

    while True:
        if use_esp32_cam:
            try:
                img_resp = requests.get(esp32_url)
                img_arr = np.array(bytearray(img_resp.content), dtype=np.uint8)
                frame = cv2.imdecode(img_arr, -1)
                frame = imutils.resize(frame, width=640)
            except Exception as e:
                print("Failed to grab frame:", e)
                continue
        else:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                break

        # Apply digital zoom
        if zoom_factor > 1.0:
            h, w = frame.shape[:2]
            crop_w = int(w / zoom_factor)
            crop_h = int(h / zoom_factor)
            center_x = w // 2 + pan_x
            center_y = h // 2 + pan_y
            x1 = max(0, min(center_x - crop_w // 2, w - crop_w))
            y1 = max(0, min(center_y - crop_h // 2, h - crop_h))
            x2 = x1 + crop_w
            y2 = y1 + crop_h
            cropped = frame[y1:y2, x1:x2]
            frame = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        total_pixels = frame.shape[0] * frame.shape[1]
        stress_pixels = {key: 0 for key in color_ranges}
        detected_hsv_values = {key: [] for key in color_ranges}

        for color_name, (lower, upper) in color_ranges.items():
            lower = np.array(lower)
            upper = np.array(upper)
            mask = cv2.inRange(hsv, lower, upper)

            count = cv2.countNonZero(mask)
            stress_pixels[color_name] = count

            # Extract actual HSV values from detected regions
            if count > 0:
                hsv_masked = cv2.bitwise_and(hsv, hsv, mask=mask)
                non_zero_pixels = hsv_masked[mask > 0]
                if len(non_zero_pixels) > 0:
                    # Sample some pixels to get representative HSV values
                    sample_size = min(50, len(non_zero_pixels))
                    sampled_pixels = non_zero_pixels[::len(non_zero_pixels)//sample_size]
                    detected_hsv_values[color_name] = sampled_pixels.tolist()

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                if cv2.contourArea(contour) > 500:
                    x, y, w, h = cv2.boundingRect(contour)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(frame, color_name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Print live HSV values every interval
        current_time = time.time()
        if current_time - last_print_time >= print_interval:
            print(f"\n[FRAME {frame_count}] LIVE HSV VALUES - {time.strftime('%H:%M:%S')}")
            print("-" * 80)
            
            for color_name in color_ranges:
                pixel_count = stress_pixels[color_name]
                percentage = (pixel_count / total_pixels) * 100
                
                print(f"{color_name.upper()}:")
                print(f"  Pixels detected: {pixel_count} ({percentage:.2f}%)")
                
                if detected_hsv_values[color_name]:
                    hsv_array = np.array(detected_hsv_values[color_name])
                    mean_hsv = np.mean(hsv_array, axis=0)
                    std_hsv = np.std(hsv_array, axis=0)
                    min_hsv = np.min(hsv_array, axis=0)
                    max_hsv = np.max(hsv_array, axis=0)
                    
                    print(f"  Mean HSV: H={mean_hsv[0]:.1f}, S={mean_hsv[1]:.1f}, V={mean_hsv[2]:.1f}")
                    print(f"  Std Dev:  H={std_hsv[0]:.1f}, S={std_hsv[1]:.1f}, V={std_hsv[2]:.1f}")
                    print(f"  Range:    H={min_hsv[0]}-{max_hsv[0]}, S={min_hsv[1]}-{max_hsv[1]}, V={min_hsv[2]}-{max_hsv[2]}")
                else:
                    print("  No pixels detected in this range")
                print()
            
            last_print_time = current_time

        zoom_text = f"Zoom: {zoom_factor:.1f}x"
        cv2.putText(frame, zoom_text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imshow('Moss Stress Detection with Live HSV', frame)

        frame_count += 1
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key in [ord('+'), ord('=')]:
            zoom_factor = min(zoom_factor + zoom_step, 5.0)
        elif key in [ord('-'), ord('_')]:
            zoom_factor = max(zoom_factor - zoom_step, 1.0)
            if zoom_factor == 1.0:
                pan_x, pan_y = 0, 0
        elif key == ord('r'):
            zoom_factor = 1.0
            pan_x, pan_y = 0, 0
        elif key == 82:  # Up arrow
            pan_y = max(pan_y - pan_step, -100)
        elif key == 84:  # Down arrow
            pan_y = min(pan_y + pan_step, 100)
        elif key == 81:  # Left arrow
            pan_x = max(pan_x - pan_step, -100)
        elif key == 83:  # Right arrow
            pan_x = min(pan_x + pan_step, 100)

    if not use_esp32_cam:
        cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    detect_colors_with_live_hsv(use_esp32_cam=True, esp32_url='http://.jpg')