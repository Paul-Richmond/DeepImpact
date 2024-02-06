import yaml


def load_config_yaml(filepath):
    with open(filepath, 'r') as f:
        parameters = yaml.load(f, Loader=yaml.FullLoader)
    return parameters
