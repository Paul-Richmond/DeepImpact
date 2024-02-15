import yaml
import pandas as pd


# The cls_loader and get_loader functions are slight modifications
# to those found in https://matthewpburruss.com/post/yaml/
def cls_loader(loader, node):
    """A loader for classes."""
    params = loader.construct_mapping(node)  # get node mappings
    module = __import__(params["module"], fromlist=[params["name"]])  # load Python module
    return getattr(module, params["name"])  # get class from module


def get_loader():
    """Return a yaml loader."""
    loader = yaml.SafeLoader
    loader.add_constructor("!Cls", cls_loader)
    return loader


def load_config_yaml(filepath):
    with open(filepath, 'r') as f:
        parameters = yaml.load(f, Loader=get_loader())
    return parameters


def export_output(filepath, data):
    data.to_csv(filepath, index=False)
