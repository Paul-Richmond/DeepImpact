import yaml
import pandas as pd


def load_config_yaml(filepath):
    with open(filepath, 'r') as f:
        parameters = yaml.load(f, Loader=yaml.FullLoader)
    return parameters


def export_output(filepath, data):
    data.to_csv(filepath, index=False)
