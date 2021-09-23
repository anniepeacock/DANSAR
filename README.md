# SAR Exploration Notebooks

## Google Colab Usage

* Data Import: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/sar_notebooks/blob/master/SAR_Notebooks/Data_Import.ipynb)
* Fire: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/sar_notebooks/blob/master/SAR_Notebooks/Fire.ipynb)

To view the Google Colab Notebooks, click the "Open in Colab" button for each example. No account is necessary to view the notebooks. However, logging into a Google Account is required to run the notebooks and make code changes.

To view a jupyter notebook file on github as a Google Colab notebook, delete all characters of the web page URL through “github.com” and replace the deleted characters with the string “colab.research.google.com”.

## MyBinder Usage

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/anniepeacock/sar_notebooks/main)

MyBinder turns a Github repository into a collection of interactive notebooks. 
From MyBinder's (https://mybinder.org) Python tutorial:
When you click on the MyBinder link, BinderHub (the backend of Binder) is:
* Fetching your repo from GitHub
* Analysing the contents
* Creating a Docker file based on your repo
* Launching that Docker image in the Cloud
* Connecting you to it via your browser

This may take several minutes to load.

## Jupyter Notebook Usage 

1. Download repository
2. Open the terminal
3. Change the working directory of the terminal session to the downloaded repository.
4. Create a virtual environment using conda via:

conda create --name sar_notebooks python=3.7

5. Make sure to hit y to confirm that the listed packages can be downloaded for this environment.
6. Activate the virtual environment:

conda activate sar_noteboooks

7. Install requirements:

pip install -r requirements.txt

8. Create a new jupyter kernel:

python -m ipykernel install --user --name sar_notebooks

## Acknowledgements

Copyright  (c) 2021  California  Institute  of Technology (“Caltech”). U.S. Government sponsorship acknowledged. 

All  rights  reserved. 
