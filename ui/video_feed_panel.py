


import cv2
import time
import numpy as np
import wx

# Import AirSimairsim_capture
try:
    from utils.airsim_capture import AirSimCapture
except ImportError:
    # Fallback if not in utils
    try:
        from __main_last import AirSimCapture
    except ImportError:
        print("Warning: AirSimCapture not found. Using dummy class.")
        # Define a dummy class
        class AirSimCapture:
            def __init__(self, client):
                self.client = client
                self.latest_processed_frame = None
                self.running = False

class VideoPanel(wx.Panel):
    def __init__(self, parent, airsim_capture, vehicle, image_processor, size=(1280, 720)):
        super().__init__(parent)
        self.vehicle = vehicle
        self.image_processor = image_processor
        self.airsim_capture = airsim_capture
        self.video_size = size
        self.last_frame = None
        
        # Setup video display
        self.video_bitmap = wx.Bitmap(*self.video_size)
        self.video_ctrl = wx.StaticBitmap(self, wx.ID_ANY, self.video_bitmap)
        
        # Bind mouse events
        self.video_ctrl.Bind(wx.EVT_LEFT_DOWN, self.on_mouse_down)
        self.video_ctrl.Bind(wx.EVT_RIGHT_DOWN, self.on_mouse_down)
        self.video_ctrl.Bind(wx.EVT_MIDDLE_DOWN, self.on_mouse_down)
        self.video_ctrl.Bind(wx.EVT_MOTION, self.on_mouse_move)
        self.video_ctrl.Bind(wx.EVT_LEFT_UP, self.on_mouse_up)
        self.video_ctrl.Bind(wx.EVT_RIGHT_UP, self.on_mouse_up)
        self.video_ctrl.Bind(wx.EVT_MIDDLE_UP, self.on_mouse_up)
        
        # Bind keyboard events to the panel itself (not the static bitmap)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_press)
        self.Bind(wx.EVT_SET_FOCUS, self.on_focus)
        self.Bind(wx.EVT_KILL_FOCUS, self.on_blur)
        
        # Make sure the panel can accept focus
        self.SetWindowStyleFlag(wx.WANTS_CHARS)
        
        self.frame_update_count = 0
        self.last_fps_update = time.time()
        
        # Set dark background
        self.SetBackgroundColour(wx.Colour(30, 30, 40))
        
        # Create a sizer for the video
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.video_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)
        
        # Setup timer for updating video
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update_video, self.timer)
        self.timer.Start(33)  # ~30 FPS update rate
        
        # Set focus to receive keyboard events
        self.SetFocus()


    THREAT_KEY_MAP = {
        49: '1',  # 1
        50: '2',  # 2
        51: '3',  # 3
        52: '4',  # 4
        53: '5',  # 5 - Clear all
    }

    def on_focus(self, event):
        print("VideoPanel gained keyboard focus")
        event.Skip()

    def on_blur(self, event):
        print("VideoPanel lost keyboard focus")
        event.Skip()

    def on_mouse_down(self, event):
        """Handle mouse button down"""
        # Get click position
        pos = event.GetPosition()
        screen_x, screen_y = pos.x, pos.y
        
        # Get the position of our video control
        video_pos = self.video_ctrl.GetPosition()
        
        # Calculate click position relative to top-left of video control
        relative_x = screen_x - video_pos.x
        relative_y = screen_y - video_pos.y
        
        # Determine which mouse button was clicked
        button = ""
        if event.LeftDown() or event.GetEventType() == wx.EVT_LEFT_DOWN.typeId:
            button = "LEFT"
        elif event.RightDown() or event.GetEventType() == wx.EVT_RIGHT_DOWN.typeId:
            button = "RIGHT"
        elif event.MiddleDown() or event.GetEventType() == wx.EVT_MIDDLE_DOWN.typeId:
            button = "MIDDLE"
        
        # Convert to image coordinates
        img_x, img_y = self.screen_to_image_coords(relative_x, relative_y)
        
        if img_x is not None and img_y is not None:
            # print(f"Mouse {button}-DOWN at image coordinates: ({img_x}, {img_y})")
            
            # Pass to ImageProcessor's master mouse callback
            if self.image_processor and hasattr(self.image_processor, 'master_mouse_callback'):
                self.image_processor.master_mouse_callback("LEFT_DOWN", img_x, img_y, button)
        
        event.Skip()

    def on_mouse_move(self, event):
        """Handle mouse movement (for ROI drawing)"""
        if event.Dragging() and (event.LeftIsDown() or event.RightIsDown() or event.MiddleIsDown()):
            # Get current position
            pos = event.GetPosition()
            screen_x, screen_y = pos.x, pos.y
            
            # Get the position of our video control
            video_pos = self.video_ctrl.GetPosition()
            
            # Calculate click position relative to top-left of video control
            relative_x = screen_x - video_pos.x
            relative_y = screen_y - video_pos.y
            
            # Convert to image coordinates
            img_x, img_y = self.screen_to_image_coords(relative_x, relative_y)
            
            if img_x is not None and img_y is not None:
                # Pass to ImageProcessor's master mouse callback
                if self.image_processor and hasattr(self.image_processor, 'master_mouse_callback'):
                    self.image_processor.master_mouse_callback("MOUSE_MOVE", img_x, img_y, "mouse_move")
        
        event.Skip()

    def on_mouse_up(self, event):
        """Handle mouse button release"""
        # Get click position
        pos = event.GetPosition()
        screen_x, screen_y = pos.x, pos.y
        
        # Get the position of our video control
        video_pos = self.video_ctrl.GetPosition()
        
        # Calculate click position relative to top-left of video control
        relative_x = screen_x - video_pos.x
        relative_y = screen_y - video_pos.y
        
        # Determine which mouse button was clicked
        button = ""
        if event.LeftUp() or event.GetEventType() == wx.EVT_LEFT_UP.typeId:
            button = "LEFT"
        elif event.RightUp() or event.GetEventType() == wx.EVT_RIGHT_UP.typeId:
            button = "RIGHT"
        elif event.MiddleUp() or event.GetEventType() == wx.EVT_MIDDLE_UP.typeId:
            button = "MIDDLE"
        
        # Convert to image coordinates
        img_x, img_y = self.screen_to_image_coords(relative_x, relative_y)
        
        if img_x is not None and img_y is not None:
            # print(f"Mouse {button}-UP at image coordinates: ({img_x}, {img_y})")
            
            # Pass to ImageProcessor's master mouse callback
            if self.image_processor and hasattr(self.image_processor, 'master_mouse_callback'):
                self.image_processor.master_mouse_callback("LEFT_UP", img_x, img_y, button)
        
        event.Skip()



    def on_key_press(self, event):
        keycode = event.GetKeyCode()
        
        if keycode in self.THREAT_KEY_MAP:
            print(f"Threat key: {self.THREAT_KEY_MAP[keycode]}")
            
            # Convert to the actual character code
            char_code = ord(self.THREAT_KEY_MAP[keycode])
            
            if self.image_processor and hasattr(self.image_processor.threat, 'handle_key'):
                self.image_processor.threat.handle_key(char_code)
            
            event.Skip(False)  # Prevent default
            return
        
        event.Skip()

    # def on_key_press(self, event):
    #     """Handle keyboard shortcuts"""
    #     keycode = event.GetKeyCode()
        
    #     # List of threat control keys
    #     threat_keys = [49, 50, 51, 52, 53, 54, 55]  # 1-7
        
    #     if keycode in threat_keys:
    #         print(f"Threat control key pressed: {keycode} ('{chr(keycode)}')")
            
    #         # Pass to ImageProcessor
    #         if self.image_processor and hasattr(self.image_processor, 'handle_key'):
    #             self.image_processor.handle_key(keycode)
            
    #         # IMPORTANT: Don't let the key go to default processing
    #         event.Skip(False)
    #         return
        
    #     # For other keys, allow normal processing
    #     event.Skip()

    def screen_to_image_coords(self, screen_x, screen_y):
        """Convert screen coordinates to image coordinates"""
        if self.last_frame is None:
            return None, None
        
        h, w = self.last_frame.shape[:2]
        
        # Get video control size
        ctrl_width = self.video_ctrl.GetSize().width
        ctrl_height = self.video_ctrl.GetSize().height
        
        # Calculate scaling factors
        scale_x = w / ctrl_width if ctrl_width > 0 else 1.0
        scale_y = h / ctrl_height if ctrl_height > 0 else 1.0
        
        # Convert to image coordinates
        img_x = int(screen_x * scale_x)
        img_y = int(screen_y * scale_y)
        
        # Ensure coordinates are within frame bounds
        img_x = max(0, min(img_x, w - 1))
        img_y = max(0, min(img_y, h - 1))
        
        return img_x, img_y

    # def update_video(self, event):
    #     """Display video with proper scaling and mouse coordinate conversion"""
    #     if not self.airsim_capture or not isinstance(self.airsim_capture, AirSimCapture):
    #         self.show_no_signal()
    #         return
        
    #     frame = self.airsim_capture.latest_processed_frame
        
    #     if frame is None:
    #         self.show_no_signal()
    #         return
        
    #     try:
    #         # Store frame for mouse coordinate conversion
    #         self.last_frame = frame.copy()
            
    #         # Convert to RGB for wxPython
    #         if len(frame.shape) == 3 and frame.shape[2] == 3:
    #             rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    #         else:
    #             rgb_frame = frame
            
    #         h, w = rgb_frame.shape[:2]
            
    #         # Get current control size
    #         ctrl_size = self.video_ctrl.GetSize()
    #         ctrl_width = ctrl_size.width
    #         ctrl_height = ctrl_size.height
            
    #         # Resize to fit control while maintaining aspect ratio
    #         if ctrl_width > 0 and ctrl_height > 0:
    #             # Calculate scaling to fit control
    #             width_ratio = ctrl_width / w
    #             height_ratio = ctrl_height / h
    #             scale = min(width_ratio, height_ratio)
                
    #             new_w = int(w * scale)
    #             new_h = int(h * scale)
                
    #             # Resize image
    #             resized = cv2.resize(rgb_frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                
    #             # Create wxImage
    #             wx_image = wx.Image(new_w, new_h, resized.tobytes())
                
    #             # Scale to exact control size
    #             wx_image = wx_image.Scale(ctrl_width, ctrl_height, wx.IMAGE_QUALITY_HIGH)
    #         else:
    #             # Fallback to original size
    #             wx_image = wx.Image(w, h, rgb_frame.tobytes())
            
    #         # Create and set bitmap
    #         self.video_bitmap = wx.Bitmap(wx_image)
    #         self.video_ctrl.SetBitmap(self.video_bitmap)
    #         self.video_ctrl.Refresh()
            
    #     except Exception as e:
    #         print(f"Error displaying frame: {e}")
    #         self.show_no_signal()


    def update_video(self, event):
        """Display video with proper scaling - works for BOTH AirSim and Real Drone"""
        if not self.airsim_capture:  # Changed from airsim_airsim_capture to airsim_capture
            self.show_no_signal()
            return
        
        # Get frame - works for both AirSimairsim_capture and RealDroneairsim_capture
        if hasattr(self.airsim_capture, 'latest_processed_frame'):
            # For AirSimairsim_capture and RealDroneairsim_capture (both have this)
            frame = self.airsim_capture.latest_processed_frame
        else:
            # Fallback for any airsim_capture object
            frame = self.airsim_capture.get_frame()
        
        if frame is None:
            self.show_no_signal()
            return
        
        try:
            # Store frame for mouse coordinate conversion
            self.last_frame = frame.copy()
            
            # Convert to RGB for wxPython
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                # Already BGR or RGB? Check by assuming BGR (OpenCV default)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            elif len(frame.shape) == 3 and frame.shape[2] == 4:
                # RGBA to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
            elif len(frame.shape) == 2:
                # Grayscale to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            else:
                rgb_frame = frame
            
            h, w = rgb_frame.shape[:2]
            
            # Get current control size
            if hasattr(self, 'video_ctrl'):
                ctrl_size = self.video_ctrl.GetSize()
                ctrl_width = ctrl_size.width
                ctrl_height = ctrl_size.height
                
                # Resize to fit control while maintaining aspect ratio
                if ctrl_width > 0 and ctrl_height > 0:
                    # Calculate scaling to fit control
                    width_ratio = ctrl_width / w
                    height_ratio = ctrl_height / h
                    scale = min(width_ratio, height_ratio)
                    
                    new_w = int(w * scale)
                    new_h = int(h * scale)
                    
                    # Resize image
                    resized = cv2.resize(rgb_frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                    
                    # Create wxImage
                    wx_image = wx.Image(new_w, new_h, resized.tobytes())
                    
                    # Scale to exact control size
                    wx_image = wx_image.Scale(ctrl_width, ctrl_height, wx.IMAGE_QUALITY_HIGH)
                else:
                    # Fallback to original size
                    wx_image = wx.Image(w, h, rgb_frame.tobytes())
                
                # Create and set bitmap
                self.video_bitmap = wx.Bitmap(wx_image)
                self.video_ctrl.SetBitmap(self.video_bitmap)
                self.video_ctrl.Refresh()
                
            elif hasattr(self, 'bitmap'):
                # For VideoPanel that paints directly (like my previous examples)
                # Create wxImage from frame
                wx_image = wx.Image(w, h, rgb_frame.tobytes())
                
                # Scale to fit panel if needed
                panel_size = self.GetSize()
                if panel_size.width > 0 and panel_size.height > 0:
                    width_ratio = panel_size.width / w
                    height_ratio = panel_size.height / h
                    scale = min(width_ratio, height_ratio)
                    
                    new_w = int(w * scale)
                    new_h = int(h * scale)
                    wx_image = wx_image.Scale(new_w, new_h, wx.IMAGE_QUALITY_HIGH)
                
                # Update bitmap
                self.bitmap = wx.Bitmap(wx_image)
                self.Refresh()
                
            else:
                print("Warning: No display control found")
                
        except Exception as e:
            print(f"Error displaying frame: {e}")
            import traceback
            traceback.print_exc()
            self.show_no_signal()
    def on_paint(self, event):
        """Paint the video frame"""
        dc = wx.PaintDC(self)
        
        if self.bitmap is not None and self.bitmap.IsOk():
            # Get panel size
            panel_width, panel_height = self.GetSize()
            
            # Get bitmap size
            bitmap_width = self.bitmap.GetWidth()
            bitmap_height = self.bitmap.GetHeight()
            
            # Center the bitmap
            x = (panel_width - bitmap_width) // 2
            y = (panel_height - bitmap_height) // 2
            
            # Draw the bitmap
            dc.DrawBitmap(self.bitmap, x, y, True)
        else:
            # Draw placeholder
            dc.SetTextForeground(wx.WHITE)
            dc.DrawText("No video", 50, 50)

    def add_fps_overlay(self, frame):
        """Add FPS counter overlay to the frame - placeholder"""
        pass

    def show_no_signal(self):
        """Display 'No Signal' message"""
        try:
            # Get background color
            bg_color = self.GetBackgroundColour()
            
            # Create background with the panel's background color
            ctrl_size = self.video_ctrl.GetSize()
            if ctrl_size.width <= 0 or ctrl_size.height <= 0:
                ctrl_size = wx.Size(self.video_size[0], self.video_size[1])
            
            background = wx.Image(ctrl_size.width, ctrl_size.height)
            background.SetData(bytes([bg_color.red, bg_color.green, bg_color.blue]) * 
                            (ctrl_size.width * ctrl_size.height))
            
            # Create a wxDC for drawing text
            bitmap = wx.Bitmap(background)
            dc = wx.MemoryDC()
            dc.SelectObject(bitmap)
            
            # Set font and colors
            font = wx.Font(24, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
            dc.SetFont(font)
            dc.SetTextForeground(wx.Colour(255, 0, 0))  # Red text
            
            # Main text
            text = "NO VIDEO SIGNAL"
            text_width, text_height = dc.GetTextExtent(text)
            text_x = (ctrl_size.width - text_width) // 2
            text_y = (ctrl_size.height - text_height) // 2 - 30
            
            # Draw main text
            dc.DrawText(text, text_x, text_y)
            
            # Subtext
            sub_font = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
            dc.SetFont(sub_font)
            dc.SetTextForeground(wx.Colour(255, 255, 255))  # White text
            
            subtext = "Click 'RECONNECT VIDEO' button"
            subtext_width, subtext_height = dc.GetTextExtent(subtext)
            subtext_x = (ctrl_size.width - subtext_width) // 2
            subtext_y = text_y + text_height + 20
            
            # Draw subtext
            dc.DrawText(subtext, subtext_x, subtext_y)
            
            # Add a red border rectangle (optional)
            border_margin = 20
            dc.SetPen(wx.Pen(wx.Colour(255, 0, 0), 3))
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.DrawRectangle(border_margin, border_margin, 
                            ctrl_size.width - 2*border_margin, 
                            ctrl_size.height - 2*border_margin)
            
            # Clean up
            dc.SelectObject(wx.NullBitmap)
            
            # Set the bitmap
            self.video_bitmap = bitmap
            self.video_ctrl.SetBitmap(self.video_bitmap)
            self.video_ctrl.Refresh()
            
        except Exception as e:
            print(f"Error showing no signal: {e}")
            # Fallback to simple black background
            black_frame = np.zeros((self.video_size[1], self.video_size[0], 3), dtype=np.uint8)
            rgb_frame = cv2.cvtColor(black_frame, cv2.COLOR_BGR2RGB)
            wx_image = wx.Image(self.video_size[0], self.video_size[1], rgb_frame.tobytes())
            self.video_bitmap = wx.Bitmap(wx_image)
            self.video_ctrl.SetBitmap(self.video_bitmap)
            self.Refresh()
