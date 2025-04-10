import serial
import time
import csv
import pandas as pd
from datetime import datetime
from utils import load_config, check_csv_exists, check_folder_exists

FOLDER_PATH = "data/"
config = load_config()

# Adjust the serial port and baud rate according to your scanner's settings
ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)  # Update with your actual serial port

def isUniqueEntry(filepath, data):
    df = pd.read_csv(filepath,  sep=',')
    # df.astype(str)
    processed_data = str(data.strip().replace('"', '').replace("'", ""))

    if processed_data in df['Barcode'].astype(str).unique().tolist():
        print(f"'{processed_data}' already exists in the 'Barcode' column.")
        return False  # Data already exists in the DataFrame
    else:
        print(f"{processed_data} is unique in the 'Barcode' column.")
        return True  # Data is unique in the DataFrame


def append_to_csv(filepath, data):
    row = [config.name, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), str(data.strip().replace('"', '').replace("'", ""))]
    with open(filepath, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(row)

def listen_to_scanner():
    barcode = ''

    # Folder and File creatation
    check_folder_exists(FOLDER_PATH)
    current_date = datetime.now().strftime('%Y-%m-%d')
    csv_file_name = f"{FOLDER_PATH}{config.name}_{current_date}.csv"
    check_csv_exists(csv_file_name, config.header)

    while True:
        # Read data from the barcode scanner
        data = ser.read()  # Read one byte at a time

        if data:
            barcode += data.decode('utf-8')  # Append to the barcode string

            # If you detect a newline (end of scan), process the barcode
            if data == b'\r':  # You may need to check for `\n` or `\r\n` depending on your scanner
                print(f"Scanned Barcode: {barcode}")
                if isUniqueEntry(csv_file_name, barcode):
                    append_to_csv(csv_file_name, barcode)
                else:
                    print("Entry is not Unique. Please scan another code")
                
                barcode = ''  # Reset barcode after processing

        time.sleep(0.1)  # Avoid busy-waiting

if __name__ == "__main__":
    listen_to_scanner()
