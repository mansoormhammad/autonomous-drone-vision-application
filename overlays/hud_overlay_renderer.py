# screen_drawings_final_14.py
import cv2

class Draw:
    def __init__(self):
        # Define common drawing parameters
        self.put_text_x = 40 
        self.put_text_y = 40 
        self.plus_color = (0, 255, 0)  # Green color
        self.plus_thickness = 2
        self.plus_length = 10  # Length for the central plus sign

    def draw_screen_markings(self, frame, center_x, center_y):
        # Draw central plus sign

        # i am about add two lines in the screen responsive to any widht and height
        # two lines from top to bottom to equally devide the screen into three equal parts
        # and two lines from left to right to equally devide the screen into three equal parts

        cv2.line(
            frame,
            (int(frame.shape[1]/3), 0),
            (int(frame.shape[1]/3), frame.shape[0]),
            (255,255, 255),
            1,
        )   
        cv2.line(
            frame,
            (int(2*frame.shape[1]/3), 0),
            (int(2*frame.shape[1]/3), frame.shape[0]),
            (255, 255, 255),
            1,
        )                   
        cv2.line(
            frame,
            (0, int(frame.shape[0]/3)),
            (frame.shape[1], int(frame.shape[0]/3)),
            (255, 255, 255),
            1,
        )           
        cv2.line(
            frame,
            (0, int(2*frame.shape[0]/3)),
            (frame.shape[1], int(2*frame.shape[0]/3)),
            (255, 255, 255),
            1,
        )       

        cv2.line(
            frame,
            (center_x - self.plus_length, center_y),
            (center_x + self.plus_length, center_y),
            self.plus_color,
            self.plus_thickness,
        )
        cv2.line(
            frame,
            (center_x, center_y - self.plus_length),
            (center_x, center_y + self.plus_length),
            self.plus_color,
            self.plus_thickness,
        )
        
        # Draw vertical lines at ±30 from center
        cv2.line(
            frame,
            (center_x + 30, center_y - 20),
            (center_x + 30, center_y + 20),
            self.plus_color,
            self.plus_thickness,
        )
        cv2.line(
            frame,
            (center_x - 30, center_y - 20),
            (center_x - 30, center_y + 20),
            self.plus_color,
            self.plus_thickness,
        )
        
        # RETURN THE MODIFIED FRAME
        return frame  # ← ADD THIS LINE

        # # Draw vertical lines at ±200 from center
        # cv2.line(
        #     frame,
        #     (center_x + 200, center_y - 100),
        #     (center_x + 200, center_y + 100),
        #     self.plus_color,
        #     self.plus_thickness,
        # )
        # cv2.putText(frame, "-200", (center_x - 200 - self.put_text_y - 20, center_y),
        #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        # cv2.line(
        #     frame,
        #     (center_x - 200, center_y - 100),
        #     (center_x - 200, center_y + 100),
        #     self.plus_color,
        #     self.plus_thickness,
        # )
        # cv2.putText(frame, "+200", (center_x + 200 + self.put_text_y - 20, center_y),
        #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        

    
        # Draw vertical lines at ±30 from center
        # cv2.line(
        #     frame,
        #     (center_x + 30, center_y - 20),
        #     (center_x + 30, center_y + 20),
        #     self.plus_color,
        #     self.plus_thickness,
        # )
     
        # cv2.line(
        #     frame,
        #     (center_x - 30, center_y - 20),
        #     (center_x - 30, center_y + 20),
        #     self.plus_color,
        #     self.plus_thickness,
        # )


    def draw_button(self, frame):
        # Example implementation of drawing a button in the top-right corner
        button_w, button_h = 100, 50
        button_x = frame.shape[1] - button_w - 20
        button_y = 20
        cv2.rectangle(frame, (button_x, button_y), (button_x + button_w, button_y + button_h), (255, 0, 0), -1)
        cv2.putText(frame, "Button", (button_x + 10, button_y + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        return frame
