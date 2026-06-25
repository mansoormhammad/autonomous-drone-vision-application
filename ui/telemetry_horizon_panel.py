import wx
import math
import random
import time
class HorizonDisplay(wx.Panel):
    """Enhanced Mission Planner-style horizon display"""
    def __init__(self, parent, vehicle , movement_obj, size=(-1, 350)):
        super().__init__(parent)
        self.vehicle = vehicle
        self.movement_obj = movement_obj
       
        self.SetBackgroundColour(wx.Colour(30, 30, 40))
        # Telemetry values (defaults)
        self.airspeed = None
        self.altitude = 0
        self.battery_percent = 0
        self.distance = 0
        self.home_lat = None
        self.home_lon = None
        self.home_alt = None
        self.launch_location = None
        self.count = 0
        self.mavlink_count = 0

       
        self.master = None
        self.per_mavcount = 0
                
        # Signal strength initialization
        self.signal_strength = 0  # Default starting value
        
        # Attitude tracking
        self.current_yaw = 0
        self.last_heading = 0
        self.current_roll = 0
        self.current_pitch = 0
        
        # Main sizer
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # # Title with modern styling
        # title = wx.StaticText(self, label="HORIZON", style=wx.ALIGN_CENTER)
        # title_font = wx.Font(14, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        # title.SetFont(title_font)
        # title.SetForegroundColour(wx.Colour(100, 200, 255))
        # main_sizer.Add(title, 0, wx.ALL | wx.EXPAND, 1)
        
        # Create the horizon display area
        self.horizon_canvas = wx.Panel(self)
        self.horizon_canvas.SetBackgroundColour(wx.Colour(15, 20, 30))
        self.horizon_canvas.SetMinSize((450, 300))
        self.horizon_canvas.Bind(wx.EVT_PAINT, self.draw_horizon)
        main_sizer.Add(self.horizon_canvas, 1, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(main_sizer)
        
        # Detect connection type
        
        # Update timer
        self.update_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update_horizon, self.update_timer)
        self.update_timer.Start(100)  # 10 Hz update



    def draw_bottom_telemetry(self, dc, width, height):
        """Draw larger icon-based telemetry at left and right edges"""

        edge_margin = 40
        bottom_margin = 30
        icon_spacing = 70
        top_margin = 0

        # Altitude
        try:
            self.altitude = self.vehicle.location.global_relative_frame.alt
            self.altitude = f'{self.altitude:.1f}'
        except:
            self.altitude = 0
                
        
       
        try:
            self.battery_percent , battery_Amp , battery_volt , self.airspeed = self.movement_obj.battery_info()
            self.battery_percent = float(self.battery_percent)
        except:
            self.battery_percent = float(100)
        

        try:
            self.airspeed = float(f"{round(self.airspeed , 1) * 3.6:.1f}")
        except TypeError:
            self.airspeed = 0

    
        
        if self.launch_location is not None:
            self.distance = int(self.movement_obj.get_distance_from_launch(self.launch_location)) 
        else:
            self.distance = 0
            if self.count == 15:
                try:
                    self.launch_location = self.movement_obj.launchLocation()
                    self.count = 0
                except:
                    pass
            self.count += 1


        # Left group (Battery and Altitude)
        left_items = [
            {
                "icon": "battery",
                "value": self.battery_percent,
                "unit": " %",
                "color": self.get_battery_color(),
                "x": (edge_margin -20) + icon_spacing//2,
                "y": height - bottom_margin
            },
            {
                "icon": "altitude", 
                "value": self.altitude,
                "unit": "m",
                "color": wx.Colour(100, 200, 255),
                "x": (edge_margin -15) + icon_spacing + icon_spacing//2,
                "y": height - bottom_margin
            }
        ]
        
        # Right group (Distance and Speed)
        right_items = [
            {
                "icon": "distance",
                "value": self.distance,
                "unit": "m",
                "color": wx.Colour(255, 200, 100),
                "x": width - edge_margin - icon_spacing - icon_spacing//2,
                "y": height - bottom_margin
            },
            {
                "icon": "speed",
                "value": self.airspeed,
                "unit": "km/h",
                "color": wx.Colour(100, 255, 150),
                "x": width - (edge_margin -10) - icon_spacing//2,
                "y": height - bottom_margin
            }
        ]

        # top group (signal)
        top_items = [
            {
                "icon": "antena",
                "value": self.battery_percent,
                "unit": "%",
                "color": self.get_battery_color(),
                "x": width - (90),
                "y": top_margin
            }
        ]


        
        # Draw left items
        for item in left_items:
            self.draw_telemetry_item(dc, item)
        
        # Draw right items
        for item in right_items:
            self.draw_telemetry_item(dc, item)

        for item in top_items:
            self.draw_telemetry_item(dc, item)


    # ===== SIGNAL STRENGTH FUNCTIONS - UPDATED DESIGN =====

    def signal(self):
        # Determine status based on signal strength AND vehicle state
        if self.signal_strength <= 1:
            status = "DISCONNECTED"
            status_color = wx.Colour(255, 50 , 0)
            bar_color = wx.Colour(60, 65, 80)  # Gray for disconnected
        elif self.signal_strength >= 90:
            status = "EXCELLENT"
            status_color = wx.Colour(0, 255, 0)
            bar_color = wx.Colour(0, 255, 0)
        elif self.signal_strength >= 70:
            status = "GOOD"
            status_color = wx.Colour(100, 255, 100)
            bar_color = wx.Colour(100, 255, 100)
        elif self.signal_strength >= 40:
            status = "FAIR"
            status_color = wx.Colour(255, 255, 0)
            bar_color = wx.Colour(255, 255, 0)
        elif self.signal_strength >= 20:
            status = "POOR"
            status_color = wx.Colour(255, 165, 0)
            bar_color = wx.Colour(255, 165, 0)
        else:
            status = "BAD"
            status_color = wx.Colour(255, 50, 50)
            bar_color = wx.Colour(255, 50, 50)
        
        return status , status_color , bar_color


    def draw_telemetry_item(self, dc, item):
        """Draw a single larger telemetry item with icon and value"""
        x, y = item["x"], item["y"]
        icon_color = item["color"]
        
        if item['icon'] != 'antena':
            # Draw subtle background circle
            dc.SetPen(wx.Pen(wx.Colour(40, 45, 60, 180), 1))
            dc.SetBrush(wx.Brush(wx.Colour(25, 30, 40, 180)))
        
            # Set icon drawing properties
            dc.SetPen(wx.Pen(icon_color, 2))
            dc.SetBrush(wx.Brush(icon_color))
        
        if item["icon"] == "battery":
            battery_width = 22
            battery_height = 14
            
            if item["value"] < 20:
                fill_color = wx.Colour(255, 50, 50)
                outline_color = wx.Colour(255, 100, 100)
            elif item["value"] < 30:
                fill_color = wx.Colour(255, 150, 50)
                outline_color = wx.Colour(255, 180, 50)
            else:
                fill_color = wx.Colour(50, 255, 50)
                outline_color = wx.Colour(100, 255, 100)
            
            # Draw battery body (outline) with 2 pixel margin
            dc.SetPen(wx.Pen(outline_color, 2))
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.DrawRoundedRectangle(x - battery_width//2 + 1, y - battery_height//2 - 5 + 1,
                                battery_width - 1, battery_height - 1, 2)
            
            # Draw battery tip (positive terminal)
            dc.SetBrush(wx.Brush(outline_color))
            dc.DrawRectangle(x + battery_width//2, y - 3 - 5, 3, 6)
            
            # Calculate fill width
            fillable_width = 18
            fill_pixels = int(fillable_width * (item["value"] / 100))
            fill_pixels = max(1, fill_pixels)
            
            # Draw battery fill
            dc.SetBrush(wx.Brush(fill_color))
            dc.SetPen(wx.TRANSPARENT_PEN)
            fill_start_x = x - battery_width//2 + 2
            fill_y = y - battery_height//2 - 5 + 2
            fill_height = battery_height - 4
            dc.DrawRectangle(fill_start_x, fill_y, fill_pixels, fill_height)
            
            if item["value"] < 5:
                dc.SetPen(wx.Pen(wx.Colour(255, 255, 255), 1))
                dc.DrawLine(x - 4, y - 7, x + 4, y + 1)
                dc.DrawLine(x - 4, y + 1, x + 4, y - 7)
            
        elif item["icon"] == "altitude":
            left_mountain = [
                wx.Point(x - 10, y + 2 - 5),
                wx.Point(x - 6, y - 4 - 5),
                wx.Point(x - 2, y + 2 - 5)
            ]
            dc.DrawPolygon(left_mountain)
            
            right_mountain = [
                wx.Point(x, y + 2 - 5),
                wx.Point(x + 4, y - 6 - 5),
                wx.Point(x + 8, y + 2 - 5)
            ]
            dc.DrawPolygon(right_mountain)
            
            dc.DrawLine(x - 10, y + 2 - 5, x + 8, y + 2 - 5)
            
        elif item["icon"] == "distance":
            roof_points = [
                wx.Point(x - 8, y - 2 - 5),
                wx.Point(x, y - 8 - 5),
                wx.Point(x + 8, y - 2 - 5)
            ]
            dc.DrawPolygon(roof_points)
            
            dc.DrawRectangle(x - 6, y - 2 - 5, 12, 8)
            
            dc.SetBrush(wx.Brush(wx.Colour(25, 30, 40, 180)))
            dc.DrawRectangle(x - 2, y + 2 - 5, 4, 4)
            
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            
        elif item["icon"] == "speed":
            dc.SetPen(wx.Pen(icon_color, 2))
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.DrawCircle(x, y - 5, 8)
            
            speed_ratio = min(item["value"] / 100, 1.0)
            angle = math.radians(135 + speed_ratio * 180)
            end_x = x + 6 * math.cos(angle)
            end_y = y - 5 + 6 * math.sin(angle)
            dc.DrawLine(x, y - 5, int(end_x), int(end_y))
            
            dc.SetBrush(wx.Brush(icon_color))
            dc.DrawCircle(x, y - 5, 2)


        elif item['icon'] == 'antena':
            box_width = 80
            status , status_color , bar_color = self.signal()

            # Draw background box
            dc.SetPen(wx.Pen(wx.Colour(40, 45, 60), 1))
            dc.SetBrush(wx.Brush(wx.Colour(25, 30, 40, 220)))

            # Draw STATUS as title (centered at top)
            dc.SetTextForeground(status_color)
            dc.SetFont(wx.Font(8, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

            status_width, status_height = dc.GetTextExtent(status)
            status_x = x + (box_width - status_width) // 2
            dc.DrawText(status, status_x, y + 6)

            # Signal bars (5 bars total) - positioned below status
            bar_count = 5
            bar_width = 7
            bar_spacing = 3
            total_bars_width = (bar_count * bar_width) + ((bar_count - 1) * bar_spacing)
            bar_start_x = x + (box_width - total_bars_width) // 2
            bar_start_y = y + 30


            # Calculate how many bars should be lit
            if status == 'EXCELLENT':
                bars_to_light = 5
            elif status == 'GOOD':
                bars_to_light = 4
            elif status == 'FAIR':
                bars_to_light = 3
            elif status == 'POOR':
                bars_to_light = 2
            elif status == 'BAD':
                bars_to_light = 1
            else:
                bars_to_light = 0
            
            bars_to_light = min(bar_count, max(0, bars_to_light))

            for i in range(bar_count):
                bar_x = bar_start_x + i * (bar_width + bar_spacing)
                
                # Bar height increases with bar number (1-5)
                bar_height = 6 + i * 5
                
                # Determine if this bar should be lit
                if i < bars_to_light:
                    # Use the status color for lit bars
                    current_bar_color = bar_color
                else:
                    # Unlit bar
                    current_bar_color = wx.Colour(60, 65, 80)
                
                # Draw bar (vertical bars)
                dc.SetPen(wx.Pen(current_bar_color, 1))
                dc.SetBrush(wx.Brush(current_bar_color))
                dc.DrawRectangle(bar_x, bar_start_y + (20 - bar_height), bar_width, bar_height)

        
        # Draw value text below icon
        value_text = f"{item['value']}{item['unit']}"
        
        if item["icon"] == "battery":
            if item["value"] < 20:
                text_color = wx.Colour(255, 50, 50)
            elif item["value"] < 30:
                text_color = wx.Colour(255, 150, 50)
            else:
                text_color = wx.Colour(50, 255, 50)
        else:
            text_color = icon_color
        

        if item['icon'] != 'antena':
            dc.SetTextForeground(text_color)
            dc.SetFont(wx.Font(11, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            
            text_width, text_height = dc.GetTextExtent(value_text)
            text_x = x - text_width // 2
            text_y = y + 8
            
            dc.SetBrush(wx.Brush(wx.Colour(20, 20, 20, 180)))
            dc.SetPen(wx.TRANSPARENT_PEN)
            
            dc.DrawText(value_text, text_x, text_y)



    def draw_horizon(self, event):
        """Draw enhanced artificial horizon"""
        dc = wx.PaintDC(self.horizon_canvas)
        width, height = self.horizon_canvas.GetSize()
        
        # Clear background
        dc.SetBrush(wx.Brush(wx.Colour(15, 20, 30)))
        dc.SetPen(wx.Pen(wx.Colour(15, 20, 30)))
        dc.DrawRectangle(0, 0, width, height)
        
        # Center point
        center_x = int(width // 2)
        center_y = int(height // 2)
        
        # Enhanced sky gradient
        for i in range(center_y):
            blue = 180 - int(i * 100 / center_y)
            green = 110 - int(i * 60 / center_y)
            sky_brush = wx.Brush(wx.Colour(70, green, blue))
            dc.SetBrush(sky_brush)
            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.DrawRectangle(0, i, width, 1)
        
        # Enhanced ground gradient
        for i in range(center_y, height):
            offset = i - center_y
            red = 120 + int(offset * 30 / (height - center_y))
            brown = 80 + int(offset * 40 / (height - center_y))
            ground_brush = wx.Brush(wx.Colour(red, brown, 50))
            dc.SetBrush(ground_brush)
            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.DrawRectangle(0, i, width, 1)
        
        # Horizon line
        pitch = self.current_pitch
        roll = self.current_roll
        pitch_offset = min(max(pitch * 2, -50), 50)
        horizon_y = int(center_y + pitch_offset)
        
        dc.SetPen(wx.Pen(wx.Colour(255, 255, 255), 3))
        
        if abs(roll) < 1:
            dc.DrawLine(0, horizon_y, width, horizon_y)
        else:
            angle_rad = math.radians(roll)
            dx = width // 2 * math.tan(angle_rad)
            x1 = 0
            y1 = int(horizon_y - dx)
            x2 = width
            y2 = int(horizon_y + dx)
            dc.DrawLine(x1, y1, x2, y2)
        
        
        # Enhanced aircraft symbol
        self.draw_aircraft_symbol(dc, center_x, center_y)
        
        # Draw pitch ladder
        self.draw_pitch_ladder(dc, center_x, center_y, pitch, roll, width, height)
        
        # Draw yaw arc
        yaw_angle = self.current_yaw
        display_yaw = max(-30, min(30, yaw_angle))
        self.draw_yaw_arc(dc, width, height, center_x, horizon_y, display_yaw, roll)
        
        # Draw telemetry boxes
        self.draw_bottom_telemetry(dc, width, height)



    def draw_aircraft_symbol(self, dc, x, y):
        """Draw enhanced aircraft symbol"""
        # Main circle
        dc.SetPen(wx.Pen(wx.Colour(255, 255, 255), 2))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.DrawCircle(x, y, 12)
        
        # Center dot
        dc.SetBrush(wx.Brush(wx.Colour(255, 100, 100)))
        dc.DrawCircle(x, y, 3)
        
        # Wings
        wing_length = 40
        dc.SetPen(wx.Pen(wx.Colour(255, 255, 255), 3))
        dc.DrawLine(x - wing_length, y, x + wing_length, y)
        
        # Tail
        dc.DrawLine(x, y - 25, x, y + 15)
        
        # Wing tips
        dc.SetPen(wx.Pen(wx.Colour(255, 100, 100), 2))
        for tip_x in [x - wing_length, x + wing_length]:
            dc.DrawLine(tip_x, y - 5, tip_x, y + 5)

    def update_horizon(self, event):
        """Update horizon display with vehicle data"""    
        
        try:
            if not self.vehicle:
                # Use simulated data...
                # Simulate some pitch movement for testing
                self.current_pitch = 0
                self.current_roll = 0
                pass
            else:
                if hasattr(self.vehicle, 'attitude'):
                    self.current_pitch = math.degrees(self.vehicle.attitude.pitch)
                
               
                if hasattr(self.vehicle, 'attitude'):
                    self.current_roll = math.degrees(self.vehicle.attitude.roll)
               
                
                if hasattr(self.vehicle, 'heading'):
                    current_heading = self.vehicle.heading % 360
                    
                    if self.last_heading != 0:
                        diff = current_heading - self.last_heading
                        
                        if diff > 180:
                            diff -= 360
                        elif diff < -180:
                            diff += 360
                        
                        if abs(diff) > 1.0:
                            self.current_yaw = diff * 0.8
                        else:
                            if abs(self.current_yaw) > 0.5:
                                return_rate = 2.0
                                if self.current_yaw > 0:
                                    self.current_yaw = max(0, self.current_yaw - return_rate)
                                else:
                                    self.current_yaw = min(0, self.current_yaw + return_rate)
                            else:
                                self.current_yaw = 0
                        
                        self.current_yaw = max(-30, min(30, self.current_yaw))
                    
                    self.last_heading = current_heading
            
            # Update signal strength
            self.update_signal_strength()
            
            self.horizon_canvas.Refresh()
            
        except Exception as e:
            print(f"Horizon update error: {e}")
            # Use simulated values on error
            self.current_pitch = math.sin(time.time() * 0.3) * 10
            self.current_roll = math.cos(time.time() * 0.4) * 15


    # Other existing methods remain the same...
    def draw_pitch_ladder(self, dc, center_x, center_y, pitch, roll, width, height):
        """Draw FIXED pitch ladder"""
        center_y = int(center_y)
        dc.SetPen(wx.Pen(wx.Colour(220, 220, 220), 1))
        dc.SetTextForeground(wx.Colour(220, 220, 220))
        dc.SetFont(wx.Font(9, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        
        for angle in range(-30, 31, 10):
            if angle == 0:
                continue
            
            y_offset = angle * 4
            
            if abs(roll) > 1:
                x_offset = y_offset * math.tan(math.radians(roll))
                y_rotated = int(center_y + y_offset * math.cos(math.radians(roll)))
                x_rotated = int(center_x + x_offset)
            else:
                y_rotated = int(center_y + y_offset)
                x_rotated = int(center_x)
            
            line_length = 50 if abs(angle) % 20 == 0 else 40
            
            dc.SetPen(wx.Pen(wx.Colour(220, 220, 220), 2 if abs(angle) % 20 == 0 else 1))
            dc.DrawLine(int(x_rotated - line_length//2), y_rotated, 
                    int(x_rotated + line_length//2), y_rotated)
            
            text = f"{abs(angle)}°"
            text_width, text_height = dc.GetTextExtent(text)
            
            if angle > 0:
                text = f"{-abs(angle)}°"
                text_x = x_rotated - text_width - 5
                text_y = y_rotated - text_height//2
            else:
                text_x = x_rotated + line_length//2 + 5
                text_y = y_rotated - text_height//2
            
            dc.SetBrush(wx.Brush(wx.Colour(20, 20, 20, 150)))
            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.DrawRectangle(text_x - 2, text_y - 1, text_width + 4, text_height + 2)
            
            dc.SetTextForeground(wx.Colour(220, 220, 220))
            dc.DrawText(text, text_x, text_y)

    def draw_yaw_arc(self, dc, width, height, center_x, horizon_y, yaw_angle, roll):
        """Draw enhanced yaw arc indicator"""
        arc_radius = width // 3
        arc_center_x = int(center_x)
        arc_center_y = int(horizon_y - arc_radius)
        
        dc.SetPen(wx.Pen(wx.Colour(40, 45, 60), 3))
        dc.SetBrush(wx.Brush(wx.Colour(25, 30, 40, 200)))
        dc.DrawCircle(arc_center_x, arc_center_y, arc_radius)
        
        dc.SetPen(wx.Pen(wx.Colour(150, 150, 200), 2))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        
        points = []
        num_points = 36
        for i in range(num_points + 1):
            angle = math.pi * (i / num_points)
            x = arc_center_x + arc_radius * math.cos(angle)
            y = arc_center_y + arc_radius * math.sin(angle)
            points.append(wx.Point(int(x), int(y)))
        dc.DrawLines(points)
        
        dc.SetPen(wx.Pen(wx.Colour(180, 180, 220), 1))
        dc.SetTextForeground(wx.Colour(220, 220, 255))
        dc.SetFont(wx.Font(9, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        
        key_numbers = [-30, -20, -10, 0, 10, 20, 30]
        for angle in key_numbers:
            circle_angle = math.pi * (1 - (angle + 30) / 60)
            
            tick_length = 12
            x1 = arc_center_x + arc_radius * math.cos(circle_angle)
            y1 = arc_center_y + arc_radius * math.sin(circle_angle)
            x2 = arc_center_x + (arc_radius - tick_length) * math.cos(circle_angle)
            y2 = arc_center_y + (arc_radius - tick_length) * math.sin(circle_angle)
            dc.DrawLine(int(x1), int(y1), int(x2), int(y2))
            
            text_radius = arc_radius + 15
            x_text = arc_center_x + text_radius * math.cos(circle_angle)
            y_text = arc_center_y + text_radius * math.sin(circle_angle)
            
            if angle == 0:
                deg_text = f"{yaw_angle:+.0f}°"
                color = wx.Colour(100, 255, 100)
                font = wx.Font(10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
            elif angle > 0:
                deg_text = f"+{angle}°"
                color = wx.Colour(180, 180, 255)
                font = wx.Font(9, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
            else:
                deg_text = f"{angle}°"
                color = wx.Colour(180, 180, 255)
                font = wx.Font(9, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
            
            dc.SetTextForeground(color)
            dc.SetFont(font)
            text_width, text_height = dc.GetTextExtent(deg_text)
            dc.DrawText(deg_text, int(x_text - text_width//2), int(y_text - text_height//2))
        
        circle_angle = math.pi * (1 - (yaw_angle + 30) / 60)
        indicator_length = arc_radius - 8
        
        dc.SetPen(wx.Pen(wx.Colour(255, 50, 50), 3))
        x_end = arc_center_x + indicator_length * math.cos(circle_angle)
        y_end = arc_center_y + indicator_length * math.sin(circle_angle)
        dc.DrawLine(arc_center_x, arc_center_y, int(x_end), int(y_end))
        
        dc.SetBrush(wx.Brush(wx.Colour(255, 50, 50)))
        arrow_size = 10
        
        dir_x = math.cos(circle_angle)
        dir_y = math.sin(circle_angle)
        
        perp_x = -dir_y
        perp_y = dir_x
        
        base_half = 4
        
        left_x = x_end + base_half * perp_x
        left_y = y_end + base_half * perp_y
        
        right_x = x_end - base_half * perp_x
        right_y = y_end - base_half * perp_y
        
        tip_x = x_end + arrow_size * dir_x
        tip_y = y_end + arrow_size * dir_y
        
        points = [
            wx.Point(int(left_x), int(left_y)),
            wx.Point(int(tip_x), int(tip_y)),
            wx.Point(int(right_x), int(right_y))
        ]
        
        dc.DrawPolygon(points)
        
        dc.SetBrush(wx.Brush(wx.Colour(80, 80, 100)))
        dc.DrawCircle(arc_center_x, arc_center_y, 6)

    def get_battery_color(self):
        """Return battery outline color based on percentage"""
        if self.battery_percent < 20:
            return wx.Colour(255, 100, 100)
        elif self.battery_percent < 30:
            return wx.Colour(255, 180, 50)
        else:
            return wx.Colour(100, 255, 100)



    def update_signal_strength(self):
        """Update signal strength with smoothing"""
        try:
            self.master = self.vehicle._master
            # Calculate packet reception percentage
            packets_rcvd_percentage = 100
            if (self.master.mav_count + self.master.mav_loss) != 0:
                packets_rcvd_percentage = (100.0 * self.master.mav_count) / (self.master.mav_count + self.master.mav_loss)

            # Check if mav_count has changed since last time
            if self.per_mavcount == self.master.mav_count:
                # No new packets received since last check
                self.mavlink_count += 1
                
                # After 3 consecutive checks with no new packets, signal is lost
                if self.mavlink_count > 3:
                    self.signal_strength = -1
                    # Reset counters
                    self.master.mav_count = 0
                    self.per_mavcount = 0
                    self.mavlink_count = 0
            else:
                # New packets received
                self.signal_strength = packets_rcvd_percentage
                self.per_mavcount = self.master.mav_count
                self.mavlink_count = 0  # Reset counter since we received packets
                

        except Exception as e:
            self.signal_strength = 0  # Medium on error

