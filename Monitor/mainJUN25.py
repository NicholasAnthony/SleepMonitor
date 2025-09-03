from machine import Pin, I2C, SPI, ADC
import network
import socket
import time
import os
import utime
import gc
from time import sleep
from ili9341 import Display, color565
from struct import pack, unpack
from framebuf import FrameBuffer, MONO_HLSB, RGB565 
from xglcd_font import XglcdFont

# Get total space and free space
total_space = os.statvfs('/')[0] * os.statvfs('/')[2]
free_space = os.statvfs('/')[0] * os.statvfs('/')[3]

# Convert bytes to kilobytes for readability
total_space_kb = total_space // 1024
free_space_kb = free_space // 1024

print(f"Total Space: {total_space_kb} KB")
print(f"Free Space: {free_space_kb} KB")

# Print free memory
print("Free memory at startup:", gc.mem_free())

# Create an AP
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="SLEEPAP1", password="sleep123")

# Pin layout for display
TFT_CLK_PIN = const(18)
TFT_MOSI_PIN = const(19)
TFT_MISO_PIN = const(16)
TFT_CS_PIN = const(17)
TFT_RST_PIN = const(14)
TFT_DC_PIN = const(15)

# Setup SPI and display
spiTFT = SPI(0, baudrate=40000000, sck=Pin(TFT_CLK_PIN), mosi=Pin(TFT_MOSI_PIN))
display = Display(spiTFT, dc=Pin(TFT_DC_PIN), cs=Pin(TFT_CS_PIN), rst=Pin(TFT_RST_PIN), width=320, height=240, rotation=90)

# Pin layout for buttons
BUTTON_UP = Pin(20, Pin.IN, Pin.PULL_UP)
BUTTON_DOWN = Pin(22, Pin.IN, Pin.PULL_UP)
BUTTON_ENTER = Pin(21, Pin.IN, Pin.PULL_UP)

# Colours
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
PINK = (255, 192, 203)
BROWN = (165, 42, 42)

# Font
font = XglcdFont('Unispace12x24.c', 12, 24)

# Button functions
def debounce_button(pin):
    # Simple debounce function
    time.sleep(0.01)  # Small initial delay to debounce
    while pin.value() == 0:  # Check if the button is still pressed
        time.sleep(0.01)  # Wait while the button is down
    time.sleep(0.05)  # Additional delay after release for stability

def enter_patient_id():
    patient_id = [0, 0, 0, 0]
    digit_index = 0
    
    display.clear()
    display.draw_text8x8(30, 80, "Please enter patient ID:", color565(255, 255, 255))
    
    while digit_index < 4:
        current_digit = patient_id[digit_index]
        display.draw_text8x8(30, 100 + (digit_index * 15), f"Digit {digit_index+1}: {current_digit}", color565(255, 255, 255))
        
        while True:
            if BUTTON_UP.value() == 0:
                debounce_button(BUTTON_UP)
                current_digit = (current_digit + 1) % 10
                # Update only the digit text
                display.draw_text8x8(30, 100 + (digit_index * 15), f"Digit {digit_index+1}: {current_digit}", color565(255, 255, 255))
            elif BUTTON_DOWN.value() == 0:
                debounce_button(BUTTON_DOWN)
                current_digit = (current_digit - 1) % 10
                display.draw_text8x8(30, 100 + (digit_index * 15), f"Digit {digit_index+1}: {current_digit}", color565(255, 255, 255))
            elif BUTTON_ENTER.value() == 0:
                debounce_button(BUTTON_ENTER)
                patient_id[digit_index] = current_digit
                digit_index += 1
                break
            
            time.sleep(0.01)

        if digit_index < 4:
            # Only redraw the next digit line instead of clearing everything
            display.draw_text8x8(30, 100 + (digit_index * 15), f"Digit {digit_index+1}: {patient_id[digit_index-1]}", color565(255, 255, 255))

    id_str = ''.join(map(str, patient_id))
    display.clear()
    display.draw_text8x8(30, 100, f"Patient ID entered: {id_str}", color565(255, 255, 255))
    sleep(3)
    display.clear()
    return id_str

# Image functions
def create_palette(foreground, background=0, invert=False):
    foreground = unpack('>H', pack('<H', foreground))[0]
    background = unpack('>H', pack('<H', background))[0]
    buffer_size = 4
    palette = FrameBuffer(bytearray(buffer_size), 2, 1, RGB565)
    palette.pixel(0 if invert else 1, 0, background)
    palette.pixel(1 if invert else 0, 0, foreground)
    return palette

def load_pbm(filename):
    with open(filename, 'rb') as f:
        for _ in range(2):
            f.readline()
        dimensions = f.readline().split()
        width = int(dimensions[0])
        height = int(dimensions[1])
        data = bytearray(f.read())
    return FrameBuffer(data, width, height, MONO_HLSB), width, height

# Load images as constants at startup
SMILEY_IMG, SMILEY_WIDTH, SMILEY_HEIGHT = load_pbm('smiley.pbm')
SADFACE_IMG, SADFACE_WIDTH, SADFACE_HEIGHT = load_pbm('sadface.pbm')
SLEEPICU_FB, SLEEPICU_WIDTH, SLEEPICU_HEIGHT = load_pbm('sleepICU.pbm')
SLEEPICU_PALETTE = create_palette(color565(255, 255, 255), 0, True)
SLEEPICU_BUFFER = bytearray(SLEEPICU_WIDTH * SLEEPICU_HEIGHT * 2)
SLEEPICU_RGB_FB = FrameBuffer(SLEEPICU_BUFFER, SLEEPICU_WIDTH, SLEEPICU_HEIGHT, RGB565)
SLEEPICU_RGB_FB.blit(SLEEPICU_FB, 0, 0, -1, SLEEPICU_PALETTE)
print("Free memory after loading images:", gc.mem_free())


# Function to create a unique filename
def create_unique_filename(base_name, extension):
    filename = f"{base_name}.{extension}"
    counter = 1
    while filename in os.listdir():
        filename = f"{base_name}_{counter}.{extension}"
        counter += 1
    return filename

# Startup screen function
def startup_screen():
    display.draw_sprite(SLEEPICU_BUFFER, 80, 50, SLEEPICU_WIDTH, SLEEPICU_HEIGHT)
    display.draw_text8x8(30, 200, "Waiting for connection...", color565(255, 255, 255))

# Smiley Face Function
def smiley():
    display.clear()
    palette2 = create_palette(color565(0, 204, 0), 0, True)
    placeholder = bytearray(SMILEY_WIDTH * SMILEY_HEIGHT * 2)
    placeholder_fb = FrameBuffer(placeholder, SMILEY_WIDTH, SMILEY_HEIGHT, RGB565)
    placeholder_fb.blit(SMILEY_IMG, 0, 0, -1, palette2)
    display.draw_sprite(placeholder, 100, 50, SMILEY_WIDTH, SMILEY_HEIGHT)
    display.draw_text(50, 150, "Perfect! Great Job", font, color565(255, 255, 255))
    sleep(3)
    display.clear()

# Sad Face Function with reason
def sadface(reasons):
    display.clear()
    palette3 = create_palette(color565(255, 0, 0), 0, True)
    placeholder = bytearray(SADFACE_WIDTH * SADFACE_HEIGHT * 2)
    placeholder_fb = FrameBuffer(placeholder, SADFACE_WIDTH, SADFACE_HEIGHT, RGB565)
    placeholder_fb.blit(SADFACE_IMG, 0, 0, -1, palette3)
    display.draw_sprite(placeholder, 100, 40, SADFACE_WIDTH, SADFACE_HEIGHT)

    if reasons:
        formatted_reasons = "\n".join(reasons)  # Join all reasons with new lines
        y_pos = 120
        for reason in reasons:
            display.draw_text(80, y_pos, reason, font, color565(255, 255, 255))
            y_pos += 30  # Adjust this value based on your font size
    else:
        display.draw_text(80, 150, "Unknown Issue", font, color565(255, 255, 255))
    
    sleep(4)
    display.clear()

# Format timestamp
def format_timestamp():
    t = utime.localtime()
    return "{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(t[0], t[1], t[2], t[3], t[4], t[5])

# Format remaining time
def format_remaining_time(seconds_left):
    hours = seconds_left // 3600
    minutes = (seconds_left % 3600) // 60
    seconds = seconds_left % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"



# Get the patient ID
patient_id = enter_patient_id()

# Generate CSV and start data collection
csv_filename = create_unique_filename(f"sleepICU_monitor_patientID{patient_id}", "csv")

# Print memory after enter ID
print("Free memory after patient ID:", gc.mem_free())

# Run the startup screen and wait for connection
while not ap.active():
    time.sleep(0.1)


while True:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allows to reuse address immediately
    s.bind(('', 80))  # Bind to all interfaces
    s.listen(5)
    print('Listening on', ap.ifconfig()[0], 'port 80')
    gc.collect()
    print("Free memory before startup_screen:", gc.mem_free())
    startup_screen()

    while True:  # Inner loop for handling connections
        try:
            conn, addr = s.accept()
            print('Got a connection from %s' % str(addr))
            display.draw_text8x8(235, 200, "Connected!", color565(0, 255, 0))
            sleep(2)
            display.clear()

            # Open or append to CSV file
            with open(csv_filename, "a") as csvfile:
                csvfile.write("Timestamp,Noise (dB),Light (lux),Temperature (C)\n")  # Header only if file is new
                start_time = utime.time()
                total_duration = 8 * 60 * 60
                end_time = start_time + total_duration

                sound_sum = 0
                light_sum = 0
                temp_sum = 0
                count = 0
                write_counter = 0
                write_interval = 10

                while utime.time() < end_time:
                    current_time = utime.time()
                    remaining_time = end_time - current_time
                    time_display = format_remaining_time(remaining_time)
                
                    try:
                        conn.settimeout(5)  # 5 seconds timeout
                        data = conn.recv(16)
                        if not data:  # Connection closed by client
                            print("Client disconnected, waiting for reconnection")
                            conn.close()
                            raise OSError("Connection lost")
                        elif len(data) == 4 and data == b'PING':  # Health check
                            respond_to_health_check(conn)
                        elif len(data) == 16:  # Normal data
                            temp, light, sound, battery = unpack('!ffff', data)
                            conn.send(b'ACK')  # Send acknowledgment back to the client

                            sound_sum += sound
                            light_sum += light
                            temp_sum += temp
                            count += 1
                            write_counter += 1

                            if write_counter == write_interval:
                                timestamp = format_timestamp()
                                csvfile.write(f"{timestamp},{round(sound, 2)},{round(light, 2)},{round(temp, 2)}\n")
                                csvfile.flush()
                                write_counter = 0
                                
                            if battery is not None:
                                if battery >= 75:
                                    color = GREEN
                                elif battery >= 25:
                                    color = ORANGE
                                else:
                                    color = RED
                                battery_text = f"{round(battery, 1)}%"
                            else:
                                color = RED
                                battery_text = "Error"

                            display.draw_text8x8(120, 10, f"Sensor Battery: {battery_text}", color565(*color))

                            if count == 10:
                                avg_sound = sound_sum / count
                                avg_light = light_sum / count
                                avg_temp = temp_sum / count

                                reasons = []

                                if not (20 <= avg_temp <= 24):
                                    reasons.append("Temp not 20-24C")
                                if avg_light >= 50:
                                    reasons.append("Light >= 50 Lux")
                                if avg_sound >= 60:
                                    reasons.append("Noise >= 60 dB")

                                if not reasons:  # No issues found, show smiley
                                    smiley()
                                else:
                                    sadface(reasons)

                                sound_sum = 0
                                light_sum = 0
                                temp_sum = 0
                                count = 0
                            else:
                                display.draw_text(30, 60, f"Noise = {round(sound, 1)} dB", font, color565(*YELLOW))
                                display.draw_text(30, 90, f"Light = {round(light, 1)} Lux", font, color565(*CYAN))
                                display.draw_text(30, 120, f"Temp = {round(temp, 1)} C", font, color565(*MAGENTA))
                                display.draw_text(30, 150, f"Time left: {time_display}", font, color565(255, 255, 255))

                            print(f"{round(sound, 2)} dB, {round(light, 2)} lux, {round(temp, 2)} °C")
                            sleep(1)
                        else:
                            print('Unexpected data length received')
                            conn.send(b'Error')  # Inform client of data error
                    
                    except OSError as e:
                        if e.args[0] == 110:  # Check for timeout, 110 is typically ETIMEDOUT
                            print('Client not responding, might be disconnected')
                            display.draw_text8x8(10, 200, "Disconnected from sensors...", color565(*RED))
                            conn.close()
                            raise OSError("Timeout")
                        else:
                            print('Connection error:', e)
                            conn.close()
                            break  # Break inner loop to wait for new connection

        except Exception as e:
            print(f"Unexpected error: {e}")
            if 'conn' in locals() and conn:
                conn.close()
            time.sleep(1)  # Short delay before next attempt to avoid flooding

    # Close the server socket if for some reason we exit the inner loop
    s.close()

        
message = "Data collection complete, please turn off the device"
while True:
    for i in range(len(message) * 8):
        display.draw_text(-i + 128, 30, message, font, color565(255, 255, 255))
        sleep(0.1)


