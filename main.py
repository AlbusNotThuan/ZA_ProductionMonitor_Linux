import os
import time
import subprocess
import threading
from datetime import datetime
import sys

# Import the necessary modules from your previous code
from flask import Flask, jsonify, render_template, request, redirect, url_for
from scanner import listen_to_scanner
from webapp import app as webapp
from utils import load_config, modify_config

CONFIG_FILE = 'config.yaml'
LAST_MODIFIED = None
flask_process = None  # Track Flask process
scanner_process = None  # Track scanner process


# Function to monitor the config file for changes
def monitor_config():
    global LAST_MODIFIED
    while True:
        # Check if the config file has been modified
        try:
            file_mod_time = os.path.getmtime(CONFIG_FILE)
            if LAST_MODIFIED is None:
                LAST_MODIFIED = file_mod_time
            elif file_mod_time != LAST_MODIFIED:
                print(f"Config file modified at {datetime.now()}. Restarting services...")
                LAST_MODIFIED = file_mod_time
                restart_services()  # Restart services when config changes
        except Exception as e:
            print(f"Error while checking config file: {e}")
        time.sleep(1)  # Check every 1 second


# Function to restart both services (Flask and barcode scanner)
def restart_services():
    global flask_process, scanner_process

    # Stop the running processes if they exist
    if flask_process:
        print("Stopping Flask WebApp...")
        flask_process.terminate()  # Terminate the Flask process
        flask_process = None  # Reset the flask_process variable
    if scanner_process:
        print("Stopping Barcode Scanner Service...")
        scanner_process.terminate()  # Terminate the scanner process
        scanner_process = None  # Reset the scanner_process variable

    # Restart the barcode scanner service
    print("Restarting Barcode Scanner Service...")
    scanner_process = subprocess.Popen([sys.executable, 'scanner.py'])

    # Restart Flask web application
    print("Restarting Flask WebApp...")
    flask_process = subprocess.Popen([sys.executable, 'webapp.py'])

    print("Services restarted successfully.")


# Run Flask web app
def run_flask():
    print("Starting Flask Web Application...")
    webapp.run(debug=True, host="0.0.0.0", port=5000)


# Run barcode scanner service
def run_scanner():
    print("Starting Barcode Scanner Service...")
    listen_to_scanner()


def main():
    global flask_process, scanner_process

    # Start the config monitor in a separate thread
    threading.Thread(target=monitor_config, daemon=True).start()

    # Start subprocesses from the main thread
    scanner_process = subprocess.Popen([sys.executable, 'scanner.py'])
    flask_process = subprocess.Popen([sys.executable, 'webapp.py'])

    try:
        # Keep the main thread alive to ensure services are running
        while True:
            time.sleep(1)  # Keep main thread alive

    except KeyboardInterrupt:
        print("Shutting down services...")
        flask_process.terminate()
        scanner_process.terminate()


if __name__ == "__main__":
    main()
