import yaml
import csv
import os

# Helper class for dot notation config access
class ConfigObject:
    def __init__(self, dictionary):
        for key, value in dictionary.items():
            if isinstance(value, dict):
                setattr(self, key, ConfigObject(value))
            else:
                setattr(self, key, value)

# Read YAML and convert to ConfigObject
def load_config():
    with open('config.yaml', 'r') as file:
        data = yaml.safe_load(file)
    return ConfigObject(data)

def modify_config(key, value):
    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    config[f'{key}'] = value

    with open('config.yaml', 'w') as file:
        yaml.dump(config, file, default_flow_style=False)

# Ensure the folder exists
def check_folder_exists(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

# Create CSV file if not exists
def check_csv_exists(csv_path, headers):
    if not os.path.isfile(csv_path):
        with open(csv_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(headers)