# _threat_classification.py
import cv2
import pygame
import time
import threading
import numpy as np
from collections import defaultdict

class ThreatClassifier:
    def __init__(self, class_names):
        self.class_names = class_names
        self.class_counts = defaultdict(int)
        self.red_zone_counts = defaultdict(int)
        self.yellow_zone_counts = defaultdict(int)
        self.green_zone_counts = defaultdict(int)
        self.id_class_map = {}
        self.id_zone_map = {}
        self.counting_enabled = False
        self.alert_sound_enabled = False
        self.roi_active = False
        self.alert_sound = None
        self.last_alert_time = 0.0
        self.load_alert_sound("iginew.mp3")
        
        # Nested ROI system
        self.roi_selection_mode = False
        self.roi_drawing_stage = 0  # 0: not drawing, 1: drawing outer, 2: drawing inner
        self.outer_rect = None      # Outer rectangle (Green zone outside this)
        self.inner_rect = None      # Inner rectangle (Red zone inside this, Yellow between outer and inner)
        self.current_roi = None
        
        # Alert priorities
        self.ZONE_PRIORITY = {
            'red': 3,
            'yellow': 2,
            'green': 1
        }
        
        # Zone colors
        self.ZONE_COLORS = {
            'green': (0, 255, 0),    # Green
            'yellow': (0, 255, 255), # Yellow
            'red': (0, 0, 255)       # Red
        }
        
        # Alert messages
        self.ALERT_MESSAGES = {
            'green': "🟢 GREEN ZONE: Object Detected!",
            'yellow': "🟡 YELLOW ZONE: Object Detected!",
            'red': "🔴 RED ZONE: Object Detected!"
        }

    def load_alert_sound(self, path):
        pygame.mixer.init()
        try:
            self.alert_sound = pygame.mixer.Sound(path)
        except Exception as e:
            print(f"⚠️ Could not load sound {path}: {e}")
            self.alert_sound = None

    def play_alert_nonblocking(self):
        if self.alert_sound_enabled and self.alert_sound and not pygame.mixer.get_busy():
            threading.Thread(target=self.alert_sound.play, daemon=True).start()

    def check_zone_membership(self, x, y, frame_width, frame_height):
        """Check which zone a point belongs to (nested zones)"""
        if not self.outer_rect:
            return None
            
        ox1, oy1, ox2, oy2 = self.outer_rect
        
        # First check if point is inside outer rectangle
        if not (ox1 <= x <= ox2 and oy1 <= y <= oy2):
            return 'green'  # Outside outer rectangle = Green zone
        
        # If we have inner rectangle, check further
        if self.inner_rect:
            ix1, iy1, ix2, iy2 = self.inner_rect
            # Check if point is inside inner rectangle
            if ix1 <= x <= ix2 and iy1 <= y <= iy2:
                return 'red'  # Inside inner rectangle = Red zone
            else:
                return 'yellow'  # Between outer and inner rectangles = Yellow zone
        else:
            # Only outer rectangle defined, everything inside is Yellow (temporary)
            return 'yellow'
        
        return None

    def filter_boxes_by_zones(self, boxes, frame_width, frame_height):
        """Filter boxes and assign them to zones"""
        if boxes is None:
            return {'red': [], 'yellow': [], 'green': []}
            
        zone_boxes = {
            'red': [],
            'yellow': [],
            'green': []
        }
        
        for box in boxes:
            try:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                
                # Check which zone the object's center is in
                zone = self.check_zone_membership(cx, cy, frame_width, frame_height)
                if zone:
                    zone_boxes[zone].append(box)
            except Exception:
                continue
                
        return zone_boxes
    
    def draw_zones(self, frame):
        """Draw the nested zones on the frame"""
        h, w = frame.shape[:2]
        
        # print(f"Drawing zones: outer={self.outer_rect}, inner={self.inner_rect}, stage={self.roi_drawing_stage}")
        
        # Create a copy for transparency
        overlay = frame.copy()
        
        # Draw green zone (outside outer rectangle)
        if self.outer_rect:
            ox1, oy1, ox2, oy2 = self.outer_rect
            
            # Draw semi-transparent green for outside area
            green_mask = np.zeros((h, w, 3), dtype=np.uint8)
            green_mask[:] = (0, 100, 0)  # Dark green
            
            # Create mask for outer rectangle area (to exclude it from green zone)
            green_mask[oy1:oy2, ox1:ox2] = (0, 0, 0)  # Clear inside outer rectangle
            
            # Apply green overlay
            frame = cv2.addWeighted(frame, 0.9, green_mask, 0.1, 0)
            
            # Draw outer rectangle border
            if self.inner_rect:
                border_color = (0, 255, 0)  # Green for outer when both defined
                label = "Green Zone"
            else:
                border_color = (0, 255, 255)  # Yellow for outer when only outer defined
                label = "Yellow Zone"
                
            cv2.rectangle(frame, (ox1, oy1), (ox2, oy2), border_color, 2)
            cv2.putText(frame, label, (ox1 + 5, oy1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, border_color, 2)
        
        # Draw yellow zone (between outer and inner rectangles) and red zone (inside inner)
        if self.outer_rect and self.inner_rect:
            ox1, oy1, ox2, oy2 = self.outer_rect
            ix1, iy1, ix2, iy2 = self.inner_rect
            
            # print(f"Drawing inner red zone: ({ix1},{iy1})-({ix2},{iy2})")

            
            # Draw semi-transparent yellow for area between rectangles
            yellow_mask = np.zeros((h, w, 3), dtype=np.uint8)
            yellow_mask[:] = (0, 100, 100)  # Dark yellow
            
            # Clear inner rectangle area from yellow mask
            yellow_mask[iy1:iy2, ix1:ix2] = (0, 0, 0)
            # Also clear outside outer rectangle
            yellow_mask[0:oy1, :] = (0, 0, 0)
            yellow_mask[oy2:h, :] = (0, 0, 0)
            yellow_mask[:, 0:ox1] = (0, 0, 0)
            yellow_mask[:, ox2:w] = (0, 0, 0)
            
            # Apply yellow overlay
            frame = cv2.addWeighted(frame, 0.9, yellow_mask, 0.1, 0)
            
            # Draw inner rectangle border (red)
            cv2.rectangle(frame, (ix1, iy1), (ix2, iy2), (0, 0, 255), 2)
            cv2.putText(frame, "Red Zone", (ix1 + 5, iy1 + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            # Add labels for zones
            cv2.putText(frame, "Yellow Zone", ((ox1 + ix1)//2, (oy1 + iy1)//2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # Draw current ROI being selected (for feedback while dragging)
        if self.current_roi and self.roi_drawing_stage > 0:
            x1, y1, x2, y2 = self.current_roi
            if self.roi_drawing_stage == 1:
                color = (0, 255, 255)  # Yellow for outer rectangle
                label = "Drawing OUTER Rectangle"
            else:  # stage == 2
                color = (0, 0, 255)    # Red for inner rectangle
                label = "Drawing INNER Rectangle"
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1 + 5, y1 - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return frame
    
    

    # def draw_zones(self, frame):
    #     """Draw the nested zones on the frame"""
    #     h, w = frame.shape[:2]
        
    #     # Create a copy for transparency
    #     overlay = frame.copy()
        
    #     # Draw green zone (outside outer rectangle)
    #     if self.outer_rect:
    #         # Draw semi-transparent green for outside area
    #         green_mask = np.zeros((h, w, 3), dtype=np.uint8)
    #         green_mask[:] = (0, 100, 0)  # Dark green
            
    #         # Create mask for outer rectangle area (to exclude it from green zone)
    #         ox1, oy1, ox2, oy2 = self.outer_rect
    #         green_mask[oy1:oy2, ox1:ox2] = (0, 0, 0)  # Clear inside outer rectangle
            
    #         # Apply green overlay
    #         # frame = cv2.addWeighted(frame, 0.8, green_mask, 0.2, 0) # for more overlay 
    #         frame = cv2.addWeighted(frame, 0.9, green_mask, 0.1, 0)  # for less overlay
    #         # is the above overlay for only green color or for all colors ? answer is for all colors but we have created mask for green color only so it will effect only green color area so how to make it small overlay also for yellow and red zone ? ansoer is by creating separate masks for yellow and red zones # are there in my code below mask for it or not ? yes there is mask for yellow zone below but not for red zone because red zone is inside inner rectangle so no need to create mask for it so whata value shoul di use for yellow to make very small overlay ? answer is 0.7 and 0.3    
    #         # Draw outer rectangle border (yellow if only outer, green if both defined)
    #         if self.inner_rect:
    #             border_color = (0, 255, 0)  # Green for outer when both defined
    #             label = "Green Zone"
    #         else:
    #             border_color = (0, 255, 255)  # Yellow for outer when only outer defined
    #             label = "Yellow Zone)"
                
    #         cv2.rectangle(frame, (ox1, oy1), (ox2, oy2), border_color, 2)
    #         cv2.putText(frame, label, (ox1 + 5, oy1 - 10),
    #                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, border_color, 2)
        
    #     # Draw yellow zone (between outer and inner rectangles) and red zone (inside inner)
    #     if self.outer_rect and self.inner_rect:
    #         ox1, oy1, ox2, oy2 = self.outer_rect
    #         ix1, iy1, ix2, iy2 = self.inner_rect
            
    #         # Draw semi-transparent yellow for area between rectangles
    #         yellow_mask = np.zeros((h, w, 3), dtype=np.uint8)
    #         yellow_mask[:] = (0, 100, 100)  # Dark yellow
            
    #         # Clear inner rectangle area from yellow mask
    #         yellow_mask[iy1:iy2, ix1:ix2] = (0, 0, 0)
    #         # Also clear outside outer rectangle
    #         yellow_mask[0:oy1, :] = (0, 0, 0)
    #         yellow_mask[oy2:h, :] = (0, 0, 0)
    #         yellow_mask[:, 0:ox1] = (0, 0, 0)
    #         yellow_mask[:, ox2:w] = (0, 0, 0)
            
    #         # Apply yellow overlay
    #         # frame = cv2.addWeighted(frame, 0.8, yellow_mask, 0.2, 0) # for more overlay
    #         frame = cv2.addWeighted(frame, 0.9, yellow_mask, 0.1, 0) # for less overlay
            
    #         # Draw inner rectangle border (red)
    #         cv2.rectangle(frame, (ix1, iy1), (ix2, iy2), (0, 0, 255), 2)
    #         cv2.putText(frame, "Red Zone", (ix1 + 5, iy1 + 30),
    #                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
    #         # Add labels for zones
    #         cv2.putText(frame, "Yellow Zone", ((ox1 + ix1)//2, (oy1 + iy1)//2),
    #                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
    #     # Draw current ROI being selected
    #     if self.current_roi and self.roi_drawing_stage > 0:
    #         x1, y1, x2, y2 = self.current_roi
    #         if self.roi_drawing_stage == 1:
    #             color = (0, 255, 255)  # Yellow for outer rectangle
    #             label = "Drawing OUTER Rectangle"
    #         else:  # stage == 2
    #             color = (0, 0, 255)    # Red for inner rectangle
    #             label = "Drawing INNER Rectangle"
            
    #         cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    #         cv2.putText(frame, label, (x1 + 5, y1 - 30),
    #                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
    #     return frame

    def update_counts(self, zone_boxes):
        """Update counts for each zone"""
        if not self.counting_enabled:
            return
            
        for zone in ['red', 'yellow', 'green']:
            zone_count_dict = getattr(self, f"{zone}_zone_counts")
            
            for box in zone_boxes[zone]:
                try:
                    track_id = int(box.id.item())
                    class_id = int(box.cls.item())
                except Exception:
                    continue
                
                class_name = self.class_names.get(class_id, f"cls_{class_id}")
                obj_key = f"{track_id}_{class_name}"
                
                # If object already counted in a higher priority zone, skip
                if obj_key in self.id_zone_map:
                    previous_zone = self.id_zone_map[obj_key]
                    if self.ZONE_PRIORITY.get(previous_zone, 0) >= self.ZONE_PRIORITY.get(zone, 0):
                        continue
                    else:
                        # Remove from previous zone count
                        prev_zone_dict = getattr(self, f"{previous_zone}_zone_counts")
                        if prev_zone_dict.get(class_name, 0) > 0:
                            prev_zone_dict[class_name] -= 1
                
                # Add to current zone
                self.id_zone_map[obj_key] = zone
                zone_count_dict[class_name] = zone_count_dict.get(class_name, 0) + 1

    def get_highest_priority_zone_with_objects(self, zone_boxes):
        """Get the highest priority zone that has objects"""
        for zone in ['red', 'yellow', 'green']:
            if zone_boxes[zone]:
                return zone
        return None

    def draw_alert_message(self, frame, zone):
        """Draw alert message for the highest priority zone"""
        if not zone:
            return frame
            
        h, w = frame.shape[:2]
        alert_text = self.ALERT_MESSAGES[zone]
        
        # Calculate text size and position
        (tw, th), _ = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
        
        # Create semi-transparent background with zone color
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (tw + 30, th + 30), 
                     self.ZONE_COLORS[zone], -1)
        frame = cv2.addWeighted(overlay, 1, frame, 1, 0) # so if i want transparency to be little low i
        # Draw text (top-left corner)
        cv2.putText(frame, alert_text, (20, th + 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        return frame

    def draw_blinking_alert(self, frame, zone):
        """Draw blinking alert at bottom-center"""
        if not zone or int(time.time() * 2) % 2 != 0:
            return frame
            
        h, w = frame.shape[:2]
        zone_text = zone.upper()
        alert_text = f"{zone_text} ZONE: Object Detected!"
        
        # Get text size
        (tw, th), _ = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)
        x = (w - tw) // 2
        y = h - 80  # Higher up to avoid overlapping with info panel
        
        # Draw text with zone color
        cv2.putText(frame, alert_text, (x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, self.ZONE_COLORS[zone], 3)
        
        return frame

    def draw_info_panel(self, frame):
        """Draw the information panel with counts for each zone"""
        h, w = frame.shape[:2]
        
        # Create info texts
        info_texts = [
            f"ALERT SOUND: {'ON' if self.alert_sound_enabled else 'OFF'}",
            f"COUNTING: {'ON' if self.counting_enabled else 'OFF'}",
            f"ROI MODE: {'ON' if self.roi_selection_mode else 'OFF'}"
        ]
        
        # Add zone counts if counting is enabled
        if self.counting_enabled:
            info_texts.append("")
            info_texts.append("=== ZONE COUNTS ===")
            
            # Red zone counts (inner rectangle)
            if self.red_zone_counts:
                info_texts.append("RED ZONE :")
                for cls, cnt in sorted(self.red_zone_counts.items()):
                    info_texts.append(f"  {cls}: {cnt}")
            
            # Yellow zone counts (between rectangles)
            if self.yellow_zone_counts:
                info_texts.append("YELLOW ZONE :")
                for cls, cnt in sorted(self.yellow_zone_counts.items()):
                    info_texts.append(f"  {cls}: {cnt}")
            
            # Green zone counts (outside outer rectangle)
            if self.green_zone_counts:
                info_texts.append("GREEN ZONE :")
                for cls, cnt in sorted(self.green_zone_counts.items()):
                    info_texts.append(f"  {cls}: {cnt}")
        
        # Calculate panel size
        max_width = 0
        total_height = 0
        line_heights = []
        
        for text in info_texts:
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            max_width = max(max_width, tw)
            line_heights.append(th)
            total_height += th + 5
        
        # Draw semi-transparent background
        if info_texts:
            overlay = frame.copy()
            cv2.rectangle(
                overlay,
                (w - max_width - 40, h - total_height - 20),
                (w - 10, h - 10),
                (0, 0, 0),
                -1
            )
            frame = cv2.addWeighted(overlay, 0.4, frame, 0.6, 0)
        
        # Draw text lines (bottom-right aligned)
        y_offset = h - 20
        for text, line_height in zip(reversed(info_texts), reversed(line_heights)):
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.putText(frame, text, (w - tw - 20, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset -= (line_height + 5)
        
        return frame

    def update(self, frame, boxes):
        h, w = frame.shape[:2]
        
        # Filter boxes by zones
        zone_boxes = self.filter_boxes_by_zones(boxes, w, h)
        
        # Update counts for each zone
        self.update_counts(zone_boxes)
        
        # Check if any objects detected
        objects_detected = any(len(zone_boxes[zone]) > 0 for zone in ['red', 'yellow', 'green'])
        
        # Get highest priority zone with objects
        highest_priority_zone = self.get_highest_priority_zone_with_objects(zone_boxes)
        
        # Draw zones
        frame = self.draw_zones(frame)
        
        # Handle alert sound (only for highest priority zone)
        if self.alert_sound_enabled and highest_priority_zone:
            now = time.time()
            if now - self.last_alert_time > 1.0:
                self.play_alert_nonblocking()
                self.last_alert_time = now
        
        # # Draw alert message for highest priority zone
        if highest_priority_zone:
        #     frame = self.draw_alert_message(frame, highest_priority_zone)
            frame = self.draw_blinking_alert(frame, highest_priority_zone)
        
        # Draw info panel
        frame = self.draw_info_panel(frame)
        1
        return frame
    
    # In your _threat_classification.py, update the mouse_callback method:
    def mouse_callback(self, event_type, x, y, button):
        """Handle mouse events from wxPython VideoPanel"""
        if not getattr(self, "roi_selection_mode", False):
            return
        
        print(f"ThreatClassifier mouse: event={event_type}, x={x}, y={y}, button={button}, stage={self.roi_drawing_stage}")
        
        if "DOWN" in event_type and button == "LEFT":
            if self.roi_drawing_stage == 0:
                self.roi_drawing_stage = 1  # Start with outer rectangle
            self.ix, self.iy = x, y
            self.drawing = True
            print(f"  Start drawing at ({self.ix}, {self.iy}) - stage {self.roi_drawing_stage}")

        elif "MOVE" in event_type and getattr(self, "drawing", False):
            self.current_roi = (self.ix, self.iy, x, y)
            print(f"  Drawing rectangle to ({x}, {y})")

        elif "UP" in event_type and button == "LEFT":
            if not getattr(self, "drawing", False):
                return
                
            self.drawing = False
            final_roi = (self.ix, self.iy, x, y)
            
            # Sort coordinates
            x1, y1, x2, y2 = final_roi
            x1, x2 = sorted([x1, x2])
            y1, y2 = sorted([y1, y2])
            final_roi = (x1, y1, x2, y2)
            
            print(f"  Final rectangle: {final_roi} at stage {self.roi_drawing_stage}")
            
            # Check if inner rectangle is inside outer
            if self.roi_drawing_stage == 2 and self.outer_rect:
                ox1, oy1, ox2, oy2 = self.outer_rect
                if not (ox1 < x1 < ox2 and oy1 < y1 < oy2 and 
                        ox1 < x2 < ox2 and oy1 < y2 < oy2):
                    print("⚠️ Inner rectangle must be completely inside outer rectangle!")
                    self.roi_drawing_stage = 2  # Stay in inner rectangle stage
                    self.current_roi = None
                    return
            
            # Assign to appropriate rectangle
            if self.roi_drawing_stage == 1:  # Outer rectangle
                self.outer_rect = final_roi
                print(f"✅ OUTER Rectangle selected: {self.outer_rect}")
                print("   ↪ Outside this rectangle = GREEN ZONE")
                print("   ↪ Inside this rectangle = Will be YELLOW/RED after drawing inner rectangle")
                self.roi_drawing_stage = 2  # Move to drawing inner rectangle
                
            elif self.roi_drawing_stage == 2:  # Inner rectangle
                self.inner_rect = final_roi
                print(f"✅ INNER Rectangle selected: {self.inner_rect}")
                print("   ↪ Inside this rectangle = RED ZONE")
                print("   ↪ Between rectangles = YELLOW ZONE")
                print("   ↪ Outside outer rectangle = GREEN ZONE")
                self.roi_drawing_stage = 0
                self.roi_active = True
            
            self.current_roi = None

    # def mouse_callback(self, event , x, y, button):
    #     if not getattr(self, "roi_selection_mode", False):
    #         return
            
    #     if "LEFT" == button:
    #         if self.roi_drawing_stage == 0:
    #             self.roi_drawing_stage = 1  # Start with outer rectangle
    #         self.ix, self.iy = x, y
    #         self.drawing = True

    #     elif "mouse_move" == button and getattr(self, "drawing", False):
    #         self.current_roi = (self.ix, self.iy, x, y)

    #     elif "LEFT" == button:
    #         self.drawing = False
    #         final_roi = (self.ix, self.iy, x, y)
            
    #         # Sort coordinates to ensure x1 < x2 and y1 < y2
    #         x1, y1, x2, y2 = final_roi
    #         x1, x2 = sorted([x1, x2])
    #         y1, y2 = sorted([y1, y2])
    #         final_roi = (x1, y1, x2, y2)
            
    #         # Check if inner rectangle is completely inside outer rectangle
    #         if self.roi_drawing_stage == 2 and self.outer_rect:
    #             ox1, oy1, ox2, oy2 = self.outer_rect
    #             if not (ox1 < x1 < ox2 and oy1 < y1 < oy2 and 
    #                     ox1 < x2 < ox2 and oy1 < y2 < oy2):
    #                 print("⚠️ Inner rectangle must be completely inside outer rectangle!")
    #                 self.roi_drawing_stage = 2  # Stay in inner rectangle drawing stage
    #                 self.current_roi = None
    #                 return
            
    #         # Assign to appropriate rectangle based on drawing stage
    #         if self.roi_drawing_stage == 1:  # Outer rectangle
    #             self.outer_rect = final_roi
    #             print(f"✅ OUTER Rectangle selected: {self.outer_rect}")
    #             print("   ↪ Outside this rectangle = GREEN ZONE")
    #             print("   ↪ Inside this rectangle = Will be YELLOW/RED after drawing inner rectangle")
    #             self.roi_drawing_stage = 2  # Move to drawing inner rectangle
                
    #         elif self.roi_drawing_stage == 2:  # Inner rectangle
    #             self.inner_rect = final_roi
    #             print(f"✅ INNER Rectangle selected: {self.inner_rect}")
    #             print("   ↪ Inside this rectangle = RED ZONE")
    #             print("   ↪ Between rectangles = YELLOW ZONE")
    #             print("   ↪ Outside outer rectangle = GREEN ZONE")
    #             self.roi_drawing_stage = 0
    #             self.roi_active = True
            
    #         self.current_roi = None

    # def handle_key(self, key):
    #     """
    #     Handle keyboard inputs for toggling modes.
    #     This matches your old OpenCV version's key handling.
    #     """
    #     if key == ord('1'):
    #         self.roi_selection_mode = not getattr(self, "roi_selection_mode", False)
    #         if self.roi_selection_mode:
    #             self.roi_drawing_stage = 1  # Start with outer rectangle
    #             print("🎯 Nested ROI Mode ACTIVATED")
    #             print("   Step 1: Draw OUTER rectangle (outside = Green)")
    #             print("   Step 2: Draw INNER rectangle (inside = Red, between = Yellow)")
    #         else:
    #             self.roi_drawing_stage = 0
    #         state = "ON" if self.roi_selection_mode else "OFF"
    #         print(f"🟨 Nested ROI Selection Mode {state}")

    #     elif key == ord('2'):
    #         self.counting_enabled = not self.counting_enabled
    #         print(f"Counting {'ENABLED' if self.counting_enabled else 'DISABLED'}")

    #     elif key == ord('3'):
    #         self.alert_sound_enabled = not self.alert_sound_enabled
    #         print(f"Alert Sound {'ENABLED' if self.alert_sound_enabled else 'DISABLED'}")

    #     elif key == ord('4'):
    #         self.red_zone_counts = defaultdict(int)
    #         self.yellow_zone_counts = defaultdict(int)
    #         self.green_zone_counts = defaultdict(int)
    #         self.id_zone_map.clear()
    #         print("🧮 All zone counters reset")

    #     elif key == ord('c'):
    #         self.outer_rect = None
    #         self.inner_rect = None
    #         self.roi_active = False
    #         self.roi_drawing_stage = 0
    #         self.red_zone_counts = defaultdict(int)
    #         self.yellow_zone_counts = defaultdict(int)
    #         self.green_zone_counts = defaultdict(int)
    #         self.id_zone_map.clear()
    #         print("🧹 All zones cleared and counters reset")
            
    #     elif key == ord('o'):
    #         # Clear only outer rectangle
    #         self.outer_rect = None
    #         self.inner_rect = None  # Inner also needs to be cleared
    #         self.roi_drawing_stage = 1 if self.roi_selection_mode else 0
    #         print("🧹 OUTER rectangle cleared (inner also cleared)")
            
    #     elif key == ord('i'):
    #         # Clear only inner rectangle
    #         self.inner_rect = None
    #         print("🧹 INNER rectangle cleared")
    #         print("   ↪ Inside outer rectangle is now YELLOW ZONE")
            
    #     else:
    #         print(f"Key '{chr(key) if 32 <= key <= 126 else key}' not mapped to threat controls")

# In your _threat_classification.py, update handle_key method:

    def handle_key(self, key):
        """
        Handle keyboard inputs for toggling modes.
        Handle both uppercase and lowercase.
        """
        # Convert to lowercase for letter keys
        if 65 <= key <= 90:  # Uppercase A-Z
            key = key + 32  # Convert to lowercase
        
        print(f"ThreatClassifier.handle_key called with key={key} (char='{chr(key) if 32 <= key <= 126 else key}')")
        
        if key == ord('1'):
            self.roi_selection_mode = not getattr(self, "roi_selection_mode", False)
            if self.roi_selection_mode:
                self.roi_drawing_stage = 1  # Start with outer rectangle
                print("🎯 Nested ROI Mode ACTIVATED")
                print("   Step 1: Draw OUTER rectangle (outside = Green)")
                print("   Step 2: Draw INNER rectangle (inside = Red, between = Yellow)")
            else:
                self.roi_drawing_stage = 0
            state = "ON" if self.roi_selection_mode else "OFF"
            print(f"🟨 Nested ROI Selection Mode {state}")

        elif key == ord('2'):
            self.counting_enabled = not self.counting_enabled
            print(f"Counting {'ENABLED' if self.counting_enabled else 'DISABLED'}")

        elif key == ord('3'):
            self.alert_sound_enabled = not self.alert_sound_enabled
            print(f"Alert Sound {'ENABLED' if self.alert_sound_enabled else 'DISABLED'}")

        elif key == ord('4'):
            self.red_zone_counts = defaultdict(int)
            self.yellow_zone_counts = defaultdict(int)
            self.green_zone_counts = defaultdict(int)
            self.id_zone_map.clear()
            print("🧮 All zone counters reset")

        elif key == ord('5'):
            print(f"CLEAR ALL ZONES called! Current outer={self.outer_rect}, inner={self.inner_rect}")
            self.outer_rect = None
            self.inner_rect = None
            self.roi_active = False
            self.roi_drawing_stage = 0
            self.red_zone_counts = defaultdict(int)
            self.yellow_zone_counts = defaultdict(int)
            self.green_zone_counts = defaultdict(int)
            self.id_zone_map.clear()
            print("🧹 All zones cleared and counters reset")
            print(f"After clear: outer={self.outer_rect}, inner={self.inner_rect}")
                
        elif key == ord('6'):
            # Clear only outer rectangle
            print(f"CLEAR OUTER called! Current outer={self.outer_rect}")
            self.outer_rect = None
            self.inner_rect = None  # Inner also needs to be cleared
            self.roi_drawing_stage = 1 if self.roi_selection_mode else 0
            print("🧹 OUTER rectangle cleared (inner also cleared)")
            print(f"After clear: outer={self.outer_rect}, inner={self.inner_rect}")
                
        elif key == ord('7'):
            # Clear only inner rectangle
            print(f"CLEAR INNER called! Current inner={self.inner_rect}")
            self.inner_rect = None
            print("🧹 INNER rectangle cleared")
            print("   ↪ Inside outer rectangle is now YELLOW ZONE")
            print(f"After clear: inner={self.inner_rect}")
                
        else:
            print(f"Key '{chr(key) if 32 <= key <= 126 else key}' not mapped to threat controls")

# # _threat_classification.py
# import cv2
# import pygame
# import time
# import threading
# import numpy as np
# from collections import defaultdict

# class ThreatClassifier:
#     def __init__(self, class_names):
#         self.class_names = class_names
#         self.class_counts = defaultdict(int)
#         self.red_zone_counts = defaultdict(int)
#         self.yellow_zone_counts = defaultdict(int)
#         self.green_zone_counts = defaultdict(int)
#         self.id_class_map = {}
#         self.id_zone_map = {}
#         self.counting_enabled = False
#         self.alert_sound_enabled = False
#         self.roi_active = False
#         self.alert_sound = None
#         self.last_alert_time = 0.0
#         self.load_alert_sound("iginew.mp3")
        
#         # Multi-zone ROI system
#         self.roi_selection_mode = False
#         self.roi_drawing_stage = 0  # 0: not drawing, 1: drawing green, 2: drawing yellow, 3: drawing red
#         self.green_zone = None  # Outer zone (Green)
#         self.yellow_zone = None  # Middle zone (Yellow)
#         self.red_zone = None    # Inner zone (Red)
#         self.current_roi = None
        
#         # Alert priorities
#         self.ZONE_PRIORITY = {
#             'red': 3,
#             'yellow': 2,
#             'green': 1
#         }
        
#         # Zone colors
#         self.ZONE_COLORS = {
#             'green': (0, 255, 0),    # Green
#             'yellow': (0, 255, 255), # Yellow
#             'red': (0, 0, 255)       # Red
#         }
        
#         # Alert messages
#         self.ALERT_MESSAGES = {
#             'green': "🟢 GREEN ZONE: Object Detected!",
#             'yellow': "🟡 YELLOW ZONE: Object Detected!",
#             'red': "🔴 RED ZONE: Object Detected!"
#         }

#     def load_alert_sound(self, path):
#         pygame.mixer.init()
#         try:
#             self.alert_sound = pygame.mixer.Sound(path)
#         except Exception as e:
#             print(f"⚠️ Could not load sound {path}: {e}")
#             self.alert_sound = None

#     def play_alert_nonblocking(self):
#         if self.alert_sound_enabled and self.alert_sound and not pygame.mixer.get_busy():
#             threading.Thread(target=self.alert_sound.play, daemon=True).start()

#     def check_zone_membership(self, x, y):
#         """Check which zone a point belongs to"""
#         if not self.red_zone or not self.yellow_zone or not self.green_zone:
#             return None
            
#         x1_g, y1_g, x2_g, y2_g = self.green_zone
#         x1_y, y1_y, x2_y, y2_y = self.yellow_zone
#         x1_r, y1_r, x2_r, y2_r = self.red_zone
        
#         # Check if point is in red zone (innermost)
#         if x1_r <= x <= x2_r and y1_r <= y <= y2_r:
#             return 'red'
#         # Check if point is in yellow zone
#         elif x1_y <= x <= x2_y and y1_y <= y <= y2_y:
#             return 'yellow'
#         # Check if point is in green zone
#         elif x1_g <= x <= x2_g and y1_g <= y <= y2_g:
#             return 'green'
#         return None

#     def filter_boxes_by_zones(self, boxes):
#         """Filter boxes and assign them to zones"""
#         if boxes is None:
#             return {'red': [], 'yellow': [], 'green': []}
            
#         zone_boxes = {
#             'red': [],
#             'yellow': [],
#             'green': []
#         }
        
#         for box in boxes:
#             try:
#                 x1, y1, x2, y2 = map(int, box.xyxy[0])
#                 cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                
#                 # Check which zone the object is in
#                 zone = self.check_zone_membership(cx, cy)
#                 if zone:
#                     zone_boxes[zone].append(box)
#             except Exception:
#                 continue
                
#         return zone_boxes

#     def draw_zones(self, frame):
#         """Draw all three zones on the frame"""
#         # Draw green zone (outermost)
#         if self.green_zone:
#             x1, y1, x2, y2 = self.green_zone
#             cv2.rectangle(frame, (x1, y1), (x2, y2), self.ZONE_COLORS['green'], 2)
#             cv2.putText(frame, "GREEN ZONE", (x1 + 5, y1 - 10),
#                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.ZONE_COLORS['green'], 2)
        
#         # Draw yellow zone (middle)
#         if self.yellow_zone:
#             x1, y1, x2, y2 = self.yellow_zone
#             cv2.rectangle(frame, (x1, y1), (x2, y2), self.ZONE_COLORS['yellow'], 2)
#             cv2.putText(frame, "YELLOW ZONE", (x1 + 5, y1 - 10),
#                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.ZONE_COLORS['yellow'], 2)
        
#         # Draw red zone (innermost)
#         if self.red_zone:
#             x1, y1, x2, y2 = self.red_zone
#             cv2.rectangle(frame, (x1, y1), (x2, y2), self.ZONE_COLORS['red'], 2)
#             cv2.putText(frame, "RED ZONE", (x1 + 5, y1 - 10),
#                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.ZONE_COLORS['red'], 2)
        
#         # Draw current ROI being selected
#         if self.current_roi and self.roi_drawing_stage > 0:
#             x1, y1, x2, y2 = self.current_roi
#             colors = [self.ZONE_COLORS['green'], self.ZONE_COLORS['yellow'], self.ZONE_COLORS['red']]
#             stage_labels = ["Drawing GREEN Zone", "Drawing YELLOW Zone", "Drawing RED Zone"]
#             color = colors[self.roi_drawing_stage - 1]
#             label = stage_labels[self.roi_drawing_stage - 1]
            
#             cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
#             cv2.putText(frame, label, (x1 + 5, y1 - 30),
#                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
#         return frame

#     def update_counts(self, zone_boxes):
#         """Update counts for each zone"""
#         if not self.counting_enabled:
#             return
            
#         for zone in ['red', 'yellow', 'green']:
#             zone_count_dict = getattr(self, f"{zone}_zone_counts")
            
#             for box in zone_boxes[zone]:
#                 try:
#                     track_id = int(box.id.item())
#                     class_id = int(box.cls.item())
#                 except Exception:
#                     continue
                
#                 class_name = self.class_names.get(class_id, f"cls_{class_id}")
#                 obj_key = f"{track_id}_{class_name}"
                
#                 # If object already counted in a higher priority zone, skip
#                 if obj_key in self.id_zone_map:
#                     previous_zone = self.id_zone_map[obj_key]
#                     if self.ZONE_PRIORITY.get(previous_zone, 0) >= self.ZONE_PRIORITY.get(zone, 0):
#                         continue
#                     else:
#                         # Remove from previous zone count
#                         prev_zone_dict = getattr(self, f"{previous_zone}_zone_counts")
#                         prev_zone_dict[class_name] = max(0, prev_zone_dict.get(class_name, 0) - 1)
                
#                 # Add to current zone
#                 self.id_zone_map[obj_key] = zone
#                 zone_count_dict[class_name] = zone_count_dict.get(class_name, 0) + 1

#     def get_highest_priority_zone_with_objects(self, zone_boxes):
#         """Get the highest priority zone that has objects"""
#         for zone in ['red', 'yellow', 'green']:
#             if zone_boxes[zone]:
#                 return zone
#         return None

#     def draw_alert_message(self, frame, zone):
#         """Draw alert message for the highest priority zone"""
#         if not zone:
#             return frame
            
#         h, w = frame.shape[:2]
#         alert_text = self.ALERT_MESSAGES[zone]
        
#         # Calculate text size and position
#         (tw, th), _ = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
        
#         # Create semi-transparent background
#         overlay = frame.copy()
#         cv2.rectangle(overlay, (w - tw - 30, 10), (w - 10, th + 30), 
#                      self.ZONE_COLORS[zone], -1)
#         frame = cv2.addWeighted(overlay, 0.3, frame, 0.7, 0)
        
#         # Draw text
#         cv2.putText(frame, alert_text, (w - tw - 15, th + 20),
#                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
#         return frame

#     def draw_blinking_alert(self, frame, zone):
#         """Draw blinking alert at bottom-center"""
#         if not zone or int(time.time() * 2) % 2 != 0:
#             return frame
            
#         h, w = frame.shape[:2]
#         zone_text = zone.upper()
#         alert_text = f"{zone_text} ZONE: Object Detected!"
        
#         # Get text size
#         (tw, th), _ = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)
#         x = (w - tw) // 2
#         y = h - 40
        
#         # Draw text with zone color
#         cv2.putText(frame, alert_text, (x, y),
#                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, self.ZONE_COLORS[zone], 3)
        
#         return frame

#     def draw_info_panel(self, frame):
#         """Draw the information panel with counts for each zone"""
#         h, w = frame.shape[:2]
        
#         # Create info texts
#         info_texts = [
#             f"ALERT SOUND: {'ON' if self.alert_sound_enabled else 'OFF'}",
#             f"COUNTING: {'ON' if self.counting_enabled else 'OFF'}",
#             f"ROI MODE: {'ON' if self.roi_selection_mode else 'OFF'}"
#         ]
        
#         # Add zone counts
#         if self.counting_enabled:
#             info_texts.append("")
#             info_texts.append("=== ZONE COUNTS ===")
            
#             # Red zone counts
#             if self.red_zone_counts:
#                 info_texts.append("🔴 RED ZONE:")
#                 for cls, cnt in self.red_zone_counts.items():
#                     info_texts.append(f"  {cls}: {cnt}")
            
#             # Yellow zone counts
#             if self.yellow_zone_counts:
#                 info_texts.append("🟡 YELLOW ZONE:")
#                 for cls, cnt in self.yellow_zone_counts.items():
#                     info_texts.append(f"  {cls}: {cnt}")
            
#             # Green zone counts
#             if self.green_zone_counts:
#                 info_texts.append("🟢 GREEN ZONE:")
#                 for cls, cnt in self.green_zone_counts.items():
#                     info_texts.append(f"  {cls}: {cnt}")
        
#         # Calculate panel size
#         max_width = 0
#         total_height = 0
#         line_heights = []
        
#         for text in info_texts:
#             (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
#             max_width = max(max_width, tw)
#             line_heights.append(th)
#             total_height += th + 5
        
#         # Draw semi-transparent background
#         if info_texts:
#             overlay = frame.copy()
#             cv2.rectangle(
#                 overlay,
#                 (w - max_width - 40, h - total_height - 20),
#                 (w - 10, h - 10),
#                 (0, 0, 0),
#                 -1
#             )
#             frame = cv2.addWeighted(overlay, 0.4, frame, 0.6, 0)
        
#         # Draw text lines (bottom-right aligned)
#         y_offset = h - 20
#         for text, line_height in zip(reversed(info_texts), reversed(line_heights)):
#             (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
#             cv2.putText(frame, text, (w - tw - 20, y_offset),
#                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
#             y_offset -= (line_height + 5)
        
#         return frame

#     def update(self, frame, boxes):
#         # Filter boxes by zones
#         zone_boxes = self.filter_boxes_by_zones(boxes)
        
#         # Update counts for each zone
#         self.update_counts(zone_boxes)
        
#         # Check if any objects detected
#         objects_detected = any(len(zone_boxes[zone]) > 0 for zone in ['red', 'yellow', 'green'])
        
#         # Get highest priority zone with objects
#         highest_priority_zone = self.get_highest_priority_zone_with_objects(zone_boxes)
        
#         # Draw zones
#         frame = self.draw_zones(frame)
        
#         # Handle alert sound (only for highest priority zone)
#         if self.alert_sound_enabled and highest_priority_zone:
#             now = time.time()
#             if now - self.last_alert_time > 1.0:
#                 self.play_alert_nonblocking()
#                 self.last_alert_time = now
        
#         # Draw alert message for highest priority zone
#         if highest_priority_zone:
#             frame = self.draw_alert_message(frame, highest_priority_zone)
#             frame = self.draw_blinking_alert(frame, highest_priority_zone)
        
#         # Draw info panel
#         frame = self.draw_info_panel(frame)
        
#         return frame

#     def mouse_callback(self, event, x, y, flags, param):
#         if not getattr(self, "roi_selection_mode", False):
#             return
            
#         if event == cv2.EVENT_LBUTTONDOWN:
#             if self.roi_drawing_stage == 0:
#                 self.roi_drawing_stage = 1  # Start with green zone
#             self.ix, self.iy = x, y
#             self.drawing = True

#         elif event == cv2.EVENT_MOUSEMOVE and getattr(self, "drawing", False):
#             self.current_roi = (self.ix, self.iy, x, y)

#         elif event == cv2.EVENT_LBUTTONUP:
#             self.drawing = False
#             final_roi = (self.ix, self.iy, x, y)
            
#             # Sort coordinates to ensure x1 < x2 and y1 < y2
#             x1, y1, x2, y2 = final_roi
#             x1, x2 = sorted([x1, x2])
#             y1, y2 = sorted([y1, y2])
#             final_roi = (x1, y1, x2, y2)
            
#             # Assign to appropriate zone based on drawing stage
#             if self.roi_drawing_stage == 1:  # Green zone (outermost)
#                 self.green_zone = final_roi
#                 print(f"✅ GREEN Zone selected: {self.green_zone}")
#                 self.roi_drawing_stage = 2
                
#             elif self.roi_drawing_stage == 2:  # Yellow zone (middle)
#                 self.yellow_zone = final_roi
#                 print(f"✅ YELLOW Zone selected: {self.yellow_zone}")
#                 self.roi_drawing_stage = 3
                
#             elif self.roi_drawing_stage == 3:  # Red zone (innermost)
#                 self.red_zone = final_roi
#                 print(f"✅ RED Zone selected: {self.red_zone}")
#                 self.roi_drawing_stage = 0
#                 self.roi_active = True
            
#             self.current_roi = None

#     def handle_key(self, key):
#         """
#         Handle keyboard inputs for toggling modes.
#         """
#         if key == ord('1'):
#             self.roi_selection_mode = not getattr(self, "roi_selection_mode", False)
#             if self.roi_selection_mode:
#                 self.roi_drawing_stage = 1  # Start with green zone
#             else:
#                 self.roi_drawing_stage = 0
#             state = "ON" if self.roi_selection_mode else "OFF"
#             print(f"🟨 Multi-Zone ROI Selection Mode {state}")

#         elif key == ord('2'):
#             self.counting_enabled = not self.counting_enabled
#             print(f"Counting {'ENABLED' if self.counting_enabled else 'DISABLED'}")

#         elif key == ord('3'):
#             self.alert_sound_enabled = not self.alert_sound_enabled
#             print(f"Alert Sound {'ENABLED' if self.alert_sound_enabled else 'DISABLED'}")

#         elif key == ord('4'):
#             self.class_counts = defaultdict(int)
#             self.red_zone_counts = defaultdict(int)
#             self.yellow_zone_counts = defaultdict(int)
#             self.green_zone_counts = defaultdict(int)
#             self.id_zone_map.clear()
#             print("🧮 All zone counters reset")

#         elif key == ord('c'):
#             self.red_zone = None
#             self.yellow_zone = None
#             self.green_zone = None
#             self.roi_active = False
#             self.roi_drawing_stage = 0
#             self.red_zone_counts = defaultdict(int)
#             self.yellow_zone_counts = defaultdict(int)
#             self.green_zone_counts = defaultdict(int)
#             self.id_zone_map.clear()
#             print("🧹 All zones cleared and counters reset")
            
#         elif key == ord('g'):
#             # Clear only green zone
#             self.green_zone = None
#             print("🧹 GREEN zone cleared")
            
#         elif key == ord('y'):
#             # Clear only yellow zone
#             self.yellow_zone = None
#             print("🧹 YELLOW zone cleared")
            
#         elif key == ord('r'):
#             # Clear only red zone
#             self.red_zone = None
#             print("🧹 RED zone cleared")