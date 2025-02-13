import argparse
import yaml


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help=f"""YAML file with urls and configs.""", required=True)
    parser.add_argument("-o", "--output", help="Output folder", required=True)
    args = parser.parse_args()

    with open(args.file, 'r') as f:
        url_dicts = yaml.safe_load(f)

