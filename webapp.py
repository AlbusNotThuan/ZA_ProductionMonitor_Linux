from flask import Flask, jsonify, render_template, request, redirect, url_for, Response, send_from_directory # Added send_from_directory
import json
import os
import time
import csv
from datetime import datetime
from utils import load_config, modify_config

config = load_config()

app = Flask(__name__)
# app.secret_key = "your_secret_key"  # Secret key for session management

FOLDER_PATH = "data/"
# FILE_PATH = f"{FOLDER_PATH}{datetime.now().strftime('%Y-%m-%d')}_{config.name}.csv" # Removed static FILE_PATH
TARGET = config.target
LINE_NAME = config.name  # Default line name
RESET_SCRIPT_ACTIVE = True  # Track reset script status
# print(f"File path: {FILE_PATH}") # Removed, or use get_dynamic_file_path for initial log

def get_dynamic_file_path():
    """Determines the current CSV file path based on date and LINE_NAME."""
    return f"{FOLDER_PATH}{datetime.now().strftime('%Y-%m-%d')}_{LINE_NAME}.csv"

@app.route("/")
def index():
    # Log the expected file path at the time of serving index.html for debugging
    print(f"Serving index.html, expecting data from: {get_dynamic_file_path()}")
    return render_template("index.html", target=TARGET, line_name=LINE_NAME)

def preprocess_data():
    """Reads and processes data from the current CSV file."""
    current_file = get_dynamic_file_path()
    processed_data_rows = []
    
    if os.path.exists(current_file):
        try:
            # Check if file is not empty to avoid errors with csv.DictReader on empty files
            if os.path.getsize(current_file) > 0:
                with open(current_file, newline='', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        processed_data_rows.append(row)
            # else: file exists but is empty, processed_data_rows remains empty
        except FileNotFoundError:
            print(f"Warning: File {current_file} disappeared before read.")
        except Exception as e:
            print(f"Error reading CSV file {current_file}: {e}")
            # Fallback to empty data on other errors

    if not processed_data_rows:
        return [0, 0]

    percentage = round(len(processed_data_rows) / TARGET * 100, 2) if TARGET > 0 else 0
    # print(preprocess_data) # Removed erroneous print statement
    return [len(processed_data_rows), percentage]


@app.route("/data")
def get_data():
    """Route to fetch the processed scanned data dynamically (can be used for initial load or fallback)."""
    count, percentage = preprocess_data()
    return jsonify({
        "count": count,
        "percentage": percentage,
        "line_name": LINE_NAME,
        "target": TARGET
    })

@app.route("/stream")
def stream():
    """Server-Sent Events endpoint to stream data updates."""
    def event_stream():
        last_mtime = 0
        # Send initial data immediately upon connection
        try:
            initial_count, initial_percentage = preprocess_data()
            initial_data = {
                "count": initial_count,
                "percentage": initial_percentage,
                "line_name": LINE_NAME,
                "target": TARGET
            }
            yield f"data: {json.dumps(initial_data)}\n\n"
            
            # Set last_mtime based on the file used for initial data
            _initial_file_path = get_dynamic_file_path()
            if os.path.exists(_initial_file_path):
                last_mtime = os.path.getmtime(_initial_file_path)
            else:
                last_mtime = 0 # File might not exist yet
        except Exception as e:
            print(f"Error sending initial SSE data: {e}")
            # Client will not receive initial data, will wait for first update

        while True:
            current_file_for_stream = get_dynamic_file_path()
            current_mtime = 0
            if os.path.exists(current_file_for_stream):
                try:
                    current_mtime = os.path.getmtime(current_file_for_stream)
                except FileNotFoundError: # File might be deleted
                    current_mtime = 0 
            
            if current_mtime != last_mtime:
                try:
                    count, percentage = preprocess_data()
                    data = {
                        "count": count,
                        "percentage": percentage,
                        "line_name": LINE_NAME,
                        "target": TARGET
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    last_mtime = current_mtime
                except Exception as e:
                    print(f"Error processing or sending SSE update: {e}")
                    # Avoid breaking the stream, wait for next check
            
            time.sleep(0.5)  # Check for file modifications every 0.5 seconds
    return Response(event_stream(), mimetype="text/event-stream")

@app.route("/admin", methods=["GET", "POST"])
def admin():
    global TARGET, LINE_NAME
    if request.method == "POST":
        if "target" in request.form:
            try:
                new_target = int(request.form["target"])
                if new_target >= 0: # Basic validation
                    TARGET = new_target
                    modify_config("target", TARGET)
                else:
                    return "Invalid target value (must be non-negative)", 400
            except ValueError:
                return "Invalid target value (must be an integer)", 400
        if "line_name" in request.form:
            new_line_name = request.form["line_name"].strip()
            if new_line_name: # Basic validation
                LINE_NAME = new_line_name
                modify_config("name", LINE_NAME)
                # Important: The file path for scanner.py and webapp.py will now differ
                # until scanner.py reloads its config or is restarted.
                # The webapp will immediately try to read from the new file name.
            else:
                return "Line name cannot be empty", 400
        return redirect(url_for("admin"))
    return render_template("admin.html", 
                         target=TARGET, 
                         line_name=LINE_NAME)

@app.route("/rawdata")
def rawdata():
    """Lists CSV files available for download."""
    if not os.path.exists(FOLDER_PATH):
        return "Data directory not found.", 404
    
    files = [f for f in os.listdir(FOLDER_PATH) if f.endswith('.csv')]
    # Sort files, perhaps by name or modification time if desired
    files.sort(reverse=True) # Example: newest first if names are date-based
    return render_template("rawdata.html", files=files, line_name=LINE_NAME)

@app.route("/download/<filename>")
def download_file(filename):
    """Serves a CSV file for download from the data directory."""
    try:
        return send_from_directory(FOLDER_PATH, filename, as_attachment=True)
    except FileNotFoundError:
        return "File not found.", 404

if __name__ == "__main__":
    # Ensure the data folder exists at startup
    if not os.path.exists(FOLDER_PATH):
        os.makedirs(FOLDER_PATH)
    app.run(debug=True, host="0.0.0.0", port=5000)