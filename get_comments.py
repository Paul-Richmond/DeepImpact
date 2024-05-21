import argparse
from utils.io import load_config_yaml, export_output

CONFIG_DICT = {"dailymail": "./configs/dailymail.yaml",
               "theguardian": "./configs/guardian.yaml",
               "bbc": "./configs/bbc.yaml"}


def get_comments(run_args):
    url = run_args.url
    config_file = CONFIG_DICT[url.split(".")[1]]  # grab the string immediately after https://www. in the url
    config = load_config_yaml(config_file)
    config_site = config['site']

    scraper = config["handler"](url, config_site)
    df = scraper.scrape()
    export_output(run_args.output, df)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", help=f"""Website url to scrape comments from.
                                            Should start with 'https://www.'""", required=True)
    parser.add_argument("-o", "--output", help="Output filename", required=True)
    args = parser.parse_args()

    get_comments(args)
