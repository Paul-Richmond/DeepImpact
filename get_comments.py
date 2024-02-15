import argparse
from utils.io import load_config_yaml, export_output


def get_comments(run_args):
    config = load_config_yaml(run_args.config)
    url = config['target_url']
    config_site = config['site']

    scraper = config["handler"](url, config_site)
    df = scraper.scrape()
    export_output(args.output, df)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Configuration file", required=True)
    parser.add_argument("-o", "--output", help="Output file", required=True)
    args = parser.parse_args()

    get_comments(args)
