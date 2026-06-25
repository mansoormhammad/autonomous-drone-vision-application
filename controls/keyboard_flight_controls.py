import time 
from pynput import keyboard
import threading 
from pymavlink import mavutil
from dronekit import connect, VehicleMode
import math 

class wasd:
    def __init__(self, vehicle):
        self.vehicle = vehicle 
        self.key_permit = False
        self.key_permit_count = 0
        self.pitch_rate = 10  # Pitch rate in degrees per second
        self.pitch_duration = 0.2  # Duration for pitch command in seconds


        self.vehicle = vehicle 
        self.step = 5  # Step size for angle adjustments
        # self.client = client  # Store the AirSim client instance
        self.key_permit = False
        self.key_permit_count = 0

        # self.vehicle.send_mavlink(msg)
        # self.vehicle.flush()
        
        # Stop after short duration
        time.sleep(self.pitch_duration)
        self.stop_pitch()


    def nose_up(self):
        """Pitch nose up slightly"""
        print("Nose UP")
        # Send pitch up command
        msg = self.vehicle.message_factory.set_attitude_target_encode(
            0,  # time_boot_ms
            0,  # target system
            0,  # target component
            0b00000100,  # type mask: only pitch rate enabled
            [0, 0, 0, 0],  # q attitude (not used)
            0,  # body roll rate
            # math.radians(-self.pitch_rate),  # body pitch rate (negative for nose up)
            math.radians(-100),  # body pitch rate (negative for nose up)
            0,  # body yaw rate
            0   # thrust
        )


    def nose_down(self):
        """Pitch nose down slightly"""
        print("Nose DOWN")
        # Send pitch down command
        msg = self.vehicle.message_factory.set_attitude_target_encode(
            0,  # time_boot_ms
            0,  # target system
            0,  # target component
            0b00000100,  # type mask: only pitch rate enabled
            [0, 0, 0, 0],  # q attitude (not used)
            0,  # body roll rate
            math.radians(100),  # body pitch rate (positive for nose down)
            0,  # body yaw rate
            0   # thrust
        )
        self.vehicle.send_mavlink(msg)
        self.vehicle.flush()
        
        # Stop after short duration
        time.sleep(self.pitch_duration)
        self.stop_pitch()

    def stop_pitch(self):
        """Stop all pitch movement"""
        msg = self.vehicle.message_factory.set_attitude_target_encode(
            0,  # time_boot_ms
            0,  # target system
            0,  # target component
            0b00000100,  # type mask: only pitch rate enabled
            [0, 0, 0, 0],  # q attitude
            0,  # body roll rate
            0,  # body pitch rate (zero to stop)
            0,  # body yaw rate
            0   # thrust
        )
        self.vehicle.send_mavlink(msg)
        self.vehicle.flush()


    




    def mode_to_guided(self):
            if self.vehicle.mode.name != "GUIDED":
                print("Switching to GUIDED mode...")
                self.vehicle.mode = VehicleMode("GUIDED")
                
                time.sleep(1)

    def adjust_move(self, vx,vy, vz,yaw_rate):

        yaw_rate = math.radians(yaw_rate)

        msg = self.vehicle.message_factory.set_position_target_local_ned_encode(
            0, 0, 0,
            mavutil.mavlink.MAV_FRAME_BODY_NED,
            0b0000011111000110,  # Enable velocity + yaw (disable pos/accel/yaw_rate)
            0, 0, 0,
            vx,vy, vz,
            0, 0, 0,
            0, yaw_rate  # Use yaw, ignore yaw rate
        )
        self.vehicle.send_mavlink(msg)
        self.vehicle.flush()

    # Function to handle key presses
    def on_press(self, key):
        try:
            if key.char == 'k':  # Toggle key permit
                if self.key_permit_count % 2 == 0: 
                    self.key_permit = True 
                    self.key_permit_count += 1 
                    print("Keyboard controls ENABLED")
                else: 
                    self.key_permit = False
                    self.key_permit_count += 1 
                    print("Keyboard controls DISABLED")
            
            if self.key_permit: 
                if key.char == 'w':  # Move forward
                    threading.Thread(target=self.adjust_move, args=(15, 0, 0, 0), daemon=True).start()
                elif key.char == 'q':  # Move left
                    threading.Thread(target=self.adjust_move, args=(0, -5, 0, 0), daemon=True).start()
                elif key.char == 'e':  # Move right
                    threading.Thread(target=self.adjust_move, args=(0, 5, 0, 0), daemon=True).start()
                elif key.char == 's':  # Move backward
                    threading.Thread(target=self.adjust_move, args=(-5, 0, 0, 0), daemon=True).start()
                elif key.char == 'd':  # Yaw right
                    threading.Thread(target=self.adjust_move, args=(0, 0, 0, 10), daemon=True).start()
                elif key.char == 'a':  # Yaw left
                    threading.Thread(target=self.adjust_move, args=(0, 0, 0, -10), daemon=True).start()
                elif key.char == 'u':  # Move up
                    threading.Thread(target=self.adjust_move, args=(0, 0, -5, 0), daemon=True).start()
                elif key.char == 'b':  # Move down
                    threading.Thread(target=self.adjust_move, args=(0, 0, 5, 0), daemon=True).start()
                elif key.char == '0':  # Exit
                    exit()
                    
        except AttributeError:
            # Handle special keys like arrow keys
            if self.key_permit:
                if key == keyboard.Key.up:  # Nose up
                    print("Nose UP pressed")
                    threading.Thread(target=self.nose_up, daemon=True).start()
                elif key == keyboard.Key.down:  # Nose down
                    print("Nose DOWN pressed")
                    threading.Thread(target=self.nose_down, daemon=True).start()
            else:
                print("no permit : ",self.key_permit)



    # Main function to listen to keyboard events
    def key_main(self):
        print("Press 'w' to move forward, 'a' to move left, 'd' to move right, 's' to backward., 'u' to up., 'b' to below ., 'q' to exit.")
        with keyboard.Listener(on_press=self.on_press) as listener:
            listener.join()



if __name__ == "__main__":
    # Connect to the vehicle
    connection_string = '127.0.0.1:14550'  # Example connection string for SITL or UDP
    vehicle = connect(connection_string, wait_ready=True)

    controller = wasd(vehicle)
    controller.key_main()
