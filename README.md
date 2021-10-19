# DANSAR
 Data Applications Notebooks with SAR 
 
DANSAR is a collection of Google Colab notebooks exploring SAR data applications. To view the notebooks, click on the *.ipynb files above. At the top of the notebook, there is an "Open in Colab" button such as this image here <img width="105" alt="Screen Shot 2021-09-23 at 2 39 58 PM" src="https://user-images.githubusercontent.com/69326547/134588404-d47e30d0-33dd-42bb-803d-2a6d2a965fb0.png">. To view in Google Colab, click this button at the top of the *.ipynb notebook and a new webpage will launch. These links are replacing the web page URL "github.com" with the string "colab.research.google.com" to start the Google Colab Notebooks. 
 
No account is necessary to view the notebooks. However, a Google Account login is required to execute and upload data to the notebooks. 

<a href="https://www.loom.com/share/e88828827d6e4d188404c71e09b75b5f">
    <p> How To Access SAR Google Colab Notebooks - Watch Video</p>
    <img style="max-width:300px;" src="https://cdn.loom.com/sessions/thumbnails/e88828827d6e4d188404c71e09b75b5f-with-play.gif">
  </a>

### Other Notebook Usage Options:

#### MyBinder

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/anniepeacock/DANSAR/main)

MyBinder turns a Github repository into a collection of interactive notebooks. 
From MyBinder's (https://mybinder.org) Python tutorial, the MyBinder link is using BinderHub (the backend of Binder) is launching the interactive notebooks by:
* Fetching your repo from GitHub
* Analysing the contents
* Creating a Docker file based on your repo
* Launching that Docker image in the Cloud
* Connecting you to it via your browser

This may take several minutes to load.

#### Jupyter Notebook

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

## Citation

## Contributors

