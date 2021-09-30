# DANSAR
 Data Applications Notebooks with SAR
 
 [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.5542151.svg)](https://doi.org/10.5281/zenodo.5542151)


## Google Colab Usage

To view the Google Colab Notebooks, click the "Open in Colab" button <img width="105" alt="Screen Shot 2021-09-23 at 2 39 58 PM" src="https://user-images.githubusercontent.com/69326547/134588404-d47e30d0-33dd-42bb-803d-2a6d2a965fb0.png"> for each example's *.ipynb file above. These links are replacing the web page URL "github.com" with the string "colab.research.google.com" to launch Google Colab Notebooks. 

No account is necessary to view the notebooks. However, a Google Account login is required to execute and upload data to the notebooks. 

## MyBinder Usage

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/anniepeacock/DANSAR/main)

MyBinder turns a Github repository into a collection of interactive notebooks. 
From MyBinder's (https://mybinder.org) Python tutorial, the MyBinder link is using BinderHub (the backend of Binder) is launching the interactive notebooks by:
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
UAVSAR data in presentations and/or publications with UAVSAR data courtesy NASA/JPL-Caltech. UAVSAR data policy is governed by JPL's data policy shown here: http://www.jpl.nasa.gov/imagepolicy

