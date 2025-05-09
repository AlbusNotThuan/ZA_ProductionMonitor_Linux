from flask import Flask, jsonify, render_template, request, redirect, url_for, Response, send_from_directory
import json
import os
import time
import csv
from datetime import datetime, timedelta
import pandas as pd
from utils import load_config, modify_config

config = load_config()

app = Flask(__name__)

FOLDER_PATH = "data/"
TARGET = config.target
LINE_NAME = config.name
# Use time_segments from config, default to 1 segment if missing
TIME_SEGMENTS = getattr(config, 'time_segments', [
    {"start": "00:00", "end": "23:59", "target": TARGET}
])


def get_current_file_path():
    """Determines the current CSV file path based on date and LINE_NAME."""
    return f"{FOLDER_PATH}{datetime.now().strftime('%Y-%m-%d')}_{LINE_NAME}.csv"

@app.route("/")
def index():
    # Log the expected file path at the time of serving index.html for debugging
    print(f"Serving index.html, expecting data from: {get_current_file_path()}")
    return render_template("index.html", target=TARGET, line_name=LINE_NAME)

def preprocess_data():
    """Reads and processes data from the current CSV file."""
    current_file = get_current_file_path()
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
            _initial_file_path = get_current_file_path()
            if os.path.exists(_initial_file_path):
                last_mtime = os.path.getmtime(_initial_file_path)
            else:
                last_mtime = 0 # File might not exist yet
        except Exception as e:
            print(f"Error sending initial SSE data: {e}")
            # Client will not receive initial data, will wait for first update

        while True:
            current_file_for_stream = get_current_file_path()
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

def get_time_segments_from_config():
    """Return list of time segments from config, each as dict with start, end, target."""
    return TIME_SEGMENTS

def format_time(time_str):
    """Ensure time string is in 24-hour HH:MM format."""
    try:
        # Parse and format in 24-hour format (HH:MM)
        time_obj = datetime.strptime(time_str, "%H:%M")
        return time_obj.strftime("%H:%M")
    except ValueError:
        # Return original if parsing fails
        return time_str

def process_data_for_visual():
    """Reads and processes data from the current CSV for time series visualization using user-defined segments."""
    current_file = get_current_file_path()
    labels = []
    actual_counts = []
    target_counts = []
    segments = get_time_segments_from_config()
    
    # Prepare segment time boundaries
    segment_bounds = []
    for seg in segments:
        start = datetime.strptime(seg["start"], "%H:%M").time()
        end = datetime.strptime(seg["end"], "%H:%M").time()
        segment_bounds.append((start, end, seg["target"]))
        labels.append(f"{seg['start']}-{seg['end']}")
        actual_counts.append(0)
        target_counts.append(seg["target"])

    if os.path.exists(current_file) and os.path.getsize(current_file) > 0:
        try:
            df = pd.read_csv(current_file)
            df['Time Scanned'] = pd.to_datetime(df['Time Scanned'])
            
            # Filter for current day's data
            today = datetime.now().date()
            df = df[df['Time Scanned'].dt.date == today]
            
            for _, row in df.iterrows():
                scanned_time = row['Time Scanned'].time()
                for idx, (start, end, _) in enumerate(segment_bounds):
                    # For normal segments (e.g., 08:00-16:00)
                    if start <= end:
                        if start <= scanned_time <= end:
                            actual_counts[idx] += 1
                            break
                    # For segments spanning across midnight (e.g., 22:00-06:00)
                    else:
                        if scanned_time >= start or scanned_time <= end:
                            actual_counts[idx] += 1
                            break

        except Exception as e:
            print(f"Error processing CSV for visual: {e}")
            print(f"Current file: {current_file}")
            import traceback
            traceback.print_exc()
            
    return {
        "labels": labels,
        "actual_counts": actual_counts,
        "target_counts": target_counts,
        "line_name": LINE_NAME,
        "segments": segments
    }

@app.route("/visual")
def visual():
    initial_visual_data = process_data_for_visual()
    return render_template("visual.html", initial_data=initial_visual_data, line_name=LINE_NAME)

@app.route("/visual-stream")
def visual_stream():
    def event_stream():
        last_mtime = 0
        # Send initial data
        try:
            initial_data = process_data_for_visual()
            yield f"data: {json.dumps(initial_data)}\n\n"
            _initial_file_path = get_current_file_path()
            if os.path.exists(_initial_file_path):
                last_mtime = os.path.getmtime(_initial_file_path)
        except Exception as e:
            print(f"Error sending initial visual SSE data: {e}")

        while True:
            current_file_for_stream = get_current_file_path()
            current_mtime = 0
            if os.path.exists(current_file_for_stream):
                try:
                    current_mtime = os.path.getmtime(current_file_for_stream)
                except FileNotFoundError:
                    current_mtime = 0
            
            if current_mtime != last_mtime:
                try:
                    data = process_data_for_visual()
                    yield f"data: {json.dumps(data)}\n\n"
                    last_mtime = current_mtime
                except Exception as e:
                    print(f"Error processing or sending visual SSE update: {e}")
            
            time.sleep(0.5) # Check for file modifications
    return Response(event_stream(), mimetype="text/event-stream")

@app.route("/admin", methods=["GET", "POST"])
def admin():
    global TARGET, LINE_NAME, TIME_SEGMENTS
    if request.method == "POST":
        if "target" in request.form:
            try:
                new_target = int(request.form["target"])
                if new_target >= 0:
                    TARGET = new_target
                    modify_config("target", TARGET)
                else:
                    return "Invalid target value (must be non-negative)", 400
            except ValueError:
                return "Invalid target value (must be an integer)", 400
        if "line_name" in request.form:
            new_line_name = request.form["line_name"].strip()
            if new_line_name:
                LINE_NAME = new_line_name
                modify_config("name", LINE_NAME)
            else:
                return "Line name cannot be empty", 400
        # Handle time segments
        segments = []
        idx = 0
        while True:
            start_key = f"segment_start_{idx}"
            end_key = f"segment_end_{idx}"
            target_key = f"segment_target_{idx}"
            if all(key in request.form for key in [start_key, end_key, target_key]):
                try:
                    start = format_time(request.form[start_key])
                    end = format_time(request.form[end_key])
                    target = int(request.form[target_key])
                    if target < 0:
                        target = 0
                    segments.append({"start": start, "end": end, "target": target})
                except ValueError as e:
                    print(f"Error processing segment {idx}: {e}")
                idx += 1
            else:
                break
        if segments:
            TIME_SEGMENTS = segments
            modify_config("time_segments", TIME_SEGMENTS)
        return redirect(url_for("admin"))
    # For GET request, prepare segments to display in admin page
    return render_template("admin.html", 
                         target=TARGET, 
                         line_name=LINE_NAME,
                         time_segments=TIME_SEGMENTS)

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