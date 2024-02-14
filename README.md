# DeepImpact
In this project we are trying to use computational/deep learning 
methods to gauge the societal impact of fundamental science discoveries.
The proof of concept is described in [[1]](#1).

At this early stage, DeepImpact only scrapes data from BBC News articles which
have closed comments. 

# Install
I'm assuming that you have Anaconda installed on your Mac machine, if not 
you can download it from [here](https://docs.conda.io/projects/conda/en/stable/). 
After cloning this repository with

`git clone https://github.com/Paul-Richmond/DeepImpact.git`, 

change directory into the repository and then use:

`conda env create -n DeepImpact --file environment.yml`

to create a new conda environment called *DeepImpact* with all the 
necessary dependencies. Activate the environment with

`conda activate DeepImpact`

# Configure
The user can alter the example file in configs/config.yaml. 
This file contains several dictionaries whose action controls
- `target_url` specifies the BBC News article to load and scrape from
- `site` contains three sub-dictionaries
    - `bbc_site` contains the html selectors used in site automation
    - `data_selectors` contains the html selectors of the comments data we want to extract
    - `df_columns` specifies the column names for the Pandas DataFrame 
- `ChromeOptions` contains a list of Chrome browser settings 
- `WebDriverWait` contains the arguments to initialise a Selenium WebDriverWait object
 

# Run
The current script needs two arguments to run; `-c` and `-o`. 
These are respectively the filepath to the YAML configuration file 
and to where the outfile file will be created. For example

`python3 BBC_scraper.py -c "./configs/config.yaml" -o "./out.csv"`

# References
- [1] White, C.D., Phillips, A. and Sajonia-Coburgo-Gotha, B. (2022) ‘Retrospectively evidencing research impact using online data mining’. Research for All, 6 (1), 7, 1–17. DOI: https://doi.org/10.14324/RFA.06.1.07.
