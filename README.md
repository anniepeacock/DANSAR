# SAR Exploration Notebooks

To edit the Google Colab Notebooks: 
1. Follow the Google Colab Notebook links at the top of the Jupyter Notebook (*.ipynb). 
2. Login to your Github Account to run the notebooks and make and edits. 
3. In the upper left corner of the Colab Notebook, select "File" --> "Save a copy in Github". This will launch a new window asking for a Github login. After logging in, you will be asked to specify where to save the change on Github. Double check the "Branch" and "File Path" are pointing to the desired location.

Alternatively, clone this repo locally to push changes.

## Google Colab Usage
* Import Data in Notebook: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/DANSAR/blob/devel/Data_Import.ipynb)
* Biomass: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/DANSAR/blob/devel/Biomass.ipynb)
* Crop: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/DANSAR/blob/devel/Crop_Type.ipynb)
* Fire: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/DANSAR/blob/devel/Fire.ipynb)
* Flood:[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/DANSAR/blob/devel/Flood.ipynb)
* Forest Disturbance:[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/DANSAR/blob/devel/Forest_Disturbance.ipynb)
* Wetland Inundation:[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/DANSAR/blob/devel/Wetland_Inundation.ipynb)
* Landslides:[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/DANSAR/blob/devel/Landslide.ipynb)
* Oil Spill:[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/DANSAR/blob/devel/Oil_Spill.ipynb)
* Open Water:[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/DANSAR/blob/devel/Open_Water.ipynb)
* Generate RGBs:[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/DANSAR/blob/devel/RGB_Stretch.ipynb)
* Sea Ice:[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/DANSAR/blob/devel/Sea_Ice.ipynb)
* Soil Moisture:[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/DANSAR/blob/devel/Soil_Moisture.ipynb)
* Urban Landcover: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/DANSAR/blob/devel/Urban_Landcover.ipynb)

To view the Google Colab Notebooks, click the "Open in Colab" button for each example. No account is necessary to view the notebooks. However, logging into a Google Account is required to run the notebooks and make code changes.

To view a jupyter notebook file on github as a Google Colab notebook, delete all characters of the web page URL through “github.com” and replace the deleted characters with the string “colab.research.google.com”.

## MyBinder Usage

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/anniepeacock/DANSAR/devel)

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

UAVSAR data in presentations and/or publications with UAVSAR data courtesy NASA/JPL-Caltech. UAVSAR data policy is governed by JPL's data policy shown here: http://www.jpl.nasa.gov/imagepolicy
