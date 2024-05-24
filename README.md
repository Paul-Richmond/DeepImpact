# DeepImpact
In this project we are trying to use computational/deep learning 
methods to gauge the societal impact of fundamental science discoveries.
The proof of concept is described in [[1]](#1).

At this early stage, DeepImpact only scrapes data from a small number of websites.
These are;
1) www.bbc.co.uk
2) www.theguardian.com
3) www.dailymail.co.uk

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

# Run
The current script needs two arguments to run; `-u` and `-o`. 
These are respectively the webpage url and the filename of the output 
file that will be created. For example

`python3 get_comments.py -u "https://www.bbc.co.uk/news/science-environment-68172162" -o "bbc.json"`

# References
- [1] White, C.D., Phillips, A. and Sajonia-Coburgo-Gotha, B. (2022) ‘Retrospectively evidencing research impact using online data mining’. Research for All, 6 (1), 7, 1–17. DOI: https://doi.org/10.14324/RFA.06.1.07.
