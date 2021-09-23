# SAR Exploration Notebooks

## Google Colab Usage

* RGB Stretching: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/sar_notebooks/blob/devel/sar_notebooks/RGB/RGB_Stretch.ipynb)
* Biomass: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/sar_notebooks/blob/devel/sar_notebooks/Science/biomass/Biomass.ipynb)
* Crop Type: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/sar_notebooks/blob/devel/sar_notebooks/Science/crop_classification/Crop_Example.ipynb)
* Fire: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/sar_notebooks/blob/devel/sar_notebooks/Science/fire/Fire.ipynb)
* Flood: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/sar_notebooks/blob/devel/sar_notebooks/Science/flood/Flood.ipynb)
* Forest Disturbance: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/sar_notebooks/blob/devel/sar_notebooks/Science/forest_disturbance/Forest_Disturbance.ipynb)
* Wetland Inundation: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/sar_notebooks/blob/devel/sar_notebooks/Science/inundation_wetlands/wetland_inundation.ipynb)
* Landslide: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/sar_notebooks/blob/devel/sar_notebooks/Science/landslide/Landslide.ipynb)
* Oil Spill: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/sar_notebooks/blob/devel/sar_notebooks/Science/oil_spill/Oil_Spill.ipynb)
* Open Water: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/sar_notebooks/blob/devel/sar_notebooks/Science/openwater/Open_Water.ipynb)
* Sea Ice: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/sar_notebooks/blob/devel/sar_notebooks/Science/sea_ice/Sea_Ice.ipynb)
* Soil Moisture: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/sar_notebooks/blob/devel/sar_notebooks/Science/soil_moisture/soil_moisture.ipynb)
* Urban Landcover: [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/anniepeacock/sar_notebooks/blob/devel/sar_notebooks/Science/urban_landcover/Land_Use.ipynb)

To view the Google Colab Notebooks, click the "Open in Colab" button for each example. No account is necessary to view the notebooks. However, logging into a Google Account is required to run the notebooks and make code changes.

To view a jupyter notebook file on github as a Google Colab notebook, delete all characters of the web page URL through “github.com” and replace the deleted characters with the string “colab.research.google.com”.

## MyBinder Usage

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/anniepeacock/sar_notebooks/devel)

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

Redistribution  and  use  in  source  and  binary  forms,  with  or  without  modification,  are  permitted  provided that the  following  conditions are  met:   
* Redistributions  of  source  code  must  retain  the  above  copyright  notice,  this  list  of  conditions  and the  following  disclaimer. 
* Redistributions  in  binary  form  must  reproduce  the  above  copyright  notice,  this  list  of  conditions and  the  following  disclaimer  in  the        documentation  and/or other materials provided  with  the distribution. 
* Neither  the  name  of  Caltech  nor  its  operating  division,  the  Jet  Propulsion  Laboratory,  nor  the names  of  its  contributors  may  be  used  to  endorse  or  promote  products  derived  from  this  software without  specific  prior  written  permission. 
  
  
THIS  SOFTWARE  IS  PROVIDED  BY  THE  COPYRIGHT  HOLDERS  AND  CONTRIBUTORS  "AS IS" AND  ANY  EXPRESS  OR  IMPLIED  WARRANTIES, INCLUDING, BUT  NOT  LIMITED  TO, THE  IMPLIED  WARRANTIES  OF  MERCHANTABILITY  AND  FITNESS  FOR A  PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE  COPYRIGHT  OWNER OR CONTRIBUTORS BE  LIABLE  FOR  ANY  DIRECT,  INDIRECT,  INCIDENTAL,  SPECIAL, EXEMPLARY, OR  CONSEQUENTIAL  DAMAGES (INCLUDING,  BUT  NOT  LIMITED  TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS  OF  USE, DATA, OR  PROFITS; OR  BUSINESS  INTERRUPTION)  HOWEVER  CAUSED  AND  ON  ANY  THEORY  OF  LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,  OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)  ARISING  IN  ANY  WAY  OUT  OF  THE  USE  OF  THIS  SOFTWARE,  EVEN  IF ADVISED OF  THE  POSSIBILITY  OF  SUCH  DAMAGE. 

Open  Source  License  Approved  by  Caltech/JPL 

APACHE  LICENSE,  VERSION  2.0 
* Text version:  https://www.apache.org/licenses/LICENSE-2.0.txt 
* SPDX short identifier:  Apache-2.0 
* OSI Approved  License:  https://opensource.org/licenses/Apache-2.0 
