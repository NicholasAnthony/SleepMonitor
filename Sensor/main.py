from PiicoDev_VEML6030 import PiicoDev_VEML6030
from PiicoDev_TMP117 import PiicoDev_TMP117
from machine import Pin, ADC, reset
import network
import socket
import time
import struct
from PiicoDev_MAX17048 import PiicoDev_MAX17048  # New custom module
from PiicoDev_Unified import create_unified_i2c  # Updated to match your filename

# Initialize Sensors using defaults from PiicoDev_Unified.py (GP8 SDA, GP9 SCL)
soundSensor = ADC(27)
tempSensor = PiicoDev_TMP117()  # Defaults to I2C0, GP8 SDA, GP9 SCL, addr 0x48
lightSensor = PiicoDev_VEML6030()  # Defaults to I2C0, GP8 SDA, GP9 SCL, addr 0x10
battery_monitor = PiicoDev_MAX17048()  # Defaults to I2C0, GP8 SDA, GP9 SCL, addr 0x36

# LED for status indication
led = Pin("LED", Pin.OUT)

# Optional: Verify I2C devices
i2c = create_unified_i2c()
print("Scanning I2C bus...")
i2c.scan()  # Should print: ['0x10', '0x36', '0x48']

def connect_to_ap():
    max_ap_attempts = 3
    ap_attempt = 0
    while ap_attempt < max_ap_attempts:
        wlan = network.WLAN(network.STA_IF)
        if wlan.active():
            wlan.disconnect()
            wlan.active(False)
        wlan.active(True)
        wlan.connect('SLEEPAP1', 'sleep123')  # For SLEEPCLIENT1

        max_wait = 10
        while max_wait > 0:
            status = wlan.status()
            if status >= 3:
                break
            max_wait -= 1
            print('waiting for AP connection...')
            time.sleep(1)

        if wlan.status() != 3:
            ap_attempt += 1
            print(f'Failed to connect to AP, attempt {ap_attempt}/{max_ap_attempts}')
            time.sleep(5)
        else:
            print('Connected to AP')
            status = wlan.ifconfig()
            print('IP = ' + status[0])
            return wlan
    print('Failed to connect to AP after multiple attempts, restarting...')
    reset()

def connect_to_server(wlan):
    addr = socket.getaddrinfo('192.168.4.1', 80)[0][-1]
    max_server_attempts = 5
    server_attempt = 0
    retry_delay = 1
    while server_attempt < max_server_attempts:
        try:
            s = socket.socket()
            s.connect(addr)
            print('Connected to server')
            return s
        except OSError as e:
            print(f'Server connection failed, attempt {server_attempt + 1}/{max_server_attempts}', e)
            if s:
                s.close()
            server_attempt += 1
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 30)
    print('Failed to connect to server after multiple attempts')
    return None

def get_battery_percentage():
    try:
        return battery_monitor.cell_percent
    except Exception as e:
        print(f"Error reading battery: {e}")
        return None

def transmit_data(s):
    try:
        volt_conv = 3.3 / (65535)
        volt = soundSensor.read_u16() * volt_conv
        sound = (volt * 50) - 6
        light = lightSensor.read()
        temp = tempSensor.readTempC()
        battery = get_battery_percentage()

        if all(x is not None for x in [temp, light, sound, battery]):
            data = struct.pack('!ffff', float(temp), float(light), float(sound), float(battery))
            s.send(data)
            
            ack = s.recv(1024)
            print('ACK Received:', ack.decode())
        else:
            print('Sensor read error')
            time.sleep(1)

        time.sleep(1)
    except Exception as e:
        print('Error in data transmission:', e)
        return False
    return True

# For SLEEPCLIENT2, change this in connect_to_ap():
# wlan.connect('SLEEPAP2', 'sleep456')

while True:
    try:
        wlan = connect_to_ap()
        s = connect_to_server(wlan)
        if s is None:
            continue

        while True:
            if not transmit_data(s):
                print('Disconnecting due to transmission error')
                break
            
    except Exception as e:
        print('An unexpected error occurred:', e)
    
    finally:
        if 's' in locals() and s:
            s.close()
        if wlan:
            wlan.disconnect()
            wlan.active(False)