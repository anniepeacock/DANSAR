# SAR Exploration Notebooks

## Google Colab Usage

To view the Google Colab Notebooks, click the "Open in Colab" button <img width="105" alt="Screen Shot 2021-09-23 at 2 39 58 PM" src="https://user-images.githubusercontent.com/69326547/134588404-d47e30d0-33dd-42bb-803d-2a6d2a965fb0.png">for each example. These are links replacing the web page URL "github.com" with the string "colab.research.google.com". 

No account is necessary to view the notebooks. However, a Google Account login is required logging to execute and upload data to the notebooks. 

* Data_Import.ipynb Link: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/sar_notebooks/blob/master/SAR_Notebooks/Data_Import.ipynb)
* Fire.ipynb Link: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/sar_notebooks/blob/master/SAR_Notebooks/Fire.ipynb)

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
