import yaml
import json


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


def export_output(filepath, url, data):
    """Export the url and data to a json file."""
    data_as_dict = data.to_dict(orient="split")
    data_as_dict.update({"url": url})
    with open(filepath, 'w') as f:
        json.dump(data_as_dict, f)
