import serial

# Open serial ports (adjust to your actual port names)
in_port = serial.Serial('/dev/ttyACM0', 9600)
out_port = serial.Serial('/dev/ttyUSB1', 9600)

try:
    while True:
        if in_port.in_waiting:
            data = in_port.read(in_port.in_waiting)
            out_port.write(data)
except KeyboardInterrupt:
    print("Stopped by user.")
finally:
    in_port.close()
    out_port.close()