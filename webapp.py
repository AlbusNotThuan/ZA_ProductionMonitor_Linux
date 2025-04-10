from flask import Flask, jsonify, render_template, request, redirect, url_for, session
import json
import os
import time
import pandas as pd
import csv
from datetime import datetime
from utils import load_config, modify_config

config = load_config()

app = Flask(__name__)
# app.secret_key = "your_secret_key"  # Secret key for session management

# File to read the logged data
# LOG_FILE = "barcode_scans.json"
FOLDER_PATH = "data/"
FILE_PATH = f"{FOLDER_PATH}{datetime.now().strftime('%Y-%m-%d')}_{config.name}.csv"
TARGET = config.target
LINE_NAME = config.name  # Default line name
RESET_SCRIPT_ACTIVE = True  # Track reset script status
print(f"File path: {FILE_PATH}")

# Route to serve the main web page
@app.route("/")
def index():
    return render_template("index.html", target=TARGET, line_name=LINE_NAME)

# Function to preprocess data
def preprocess_data():
    processed_data = []
    if os.path.exists(FILE_PATH) and os.path.getsize(FILE_PATH) > 0:
        with open(FILE_PATH, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                processed_data.append(row)

    if not processed_data:
        return [0, 0]

    percentage = round(len(processed_data) / TARGET * 100, 2) if TARGET > 0 else 0
    print(preprocess_data)
    return [len(processed_data), percentage]


# Route to fetch the processed scanned data dynamically
@app.route("/data")
def get_data():
    processed_data = preprocess_data()  # Preprocess the data before sending
    return jsonify({
        "count": processed_data[0],
        "percentage": processed_data[1],
        "line_name": LINE_NAME,
        "target": TARGET
    })

# Route for admin panel (no login required)
@app.route("/admin", methods=["GET", "POST"])
def admin():
    global TARGET, LINE_NAME
    if request.method == "POST":
        if "target" in request.form:
            try:
                TARGET = int(request.form["target"])
                modify_config("target", TARGET)
            except ValueError:
                return "Invalid target value", 400
        if "line_name" in request.form:
            LINE_NAME = request.form["line_name"]
            modify_config("name", LINE_NAME)
        return redirect(url_for("admin"))
    return render_template("admin.html", 
                         target=TARGET, 
                         line_name=LINE_NAME)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)