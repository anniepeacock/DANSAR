# DANSAR
 Data Applications Notebooks with SAR 
 
DANSAR is a collection of notebooks exploring SAR data applications. To view the notebooks with Google Colab, click on the *.ipynb files above. At the top of the notebook, there is an "Open in Colab" button such as this image here <img width="105" alt="Screen Shot 2021-09-23 at 2 39 58 PM" src="https://user-images.githubusercontent.com/69326547/134588404-d47e30d0-33dd-42bb-803d-2a6d2a965fb0.png">.  Click this button at the top of the *.ipynb notebook and a new webpage will launch. These links are replacing the web page URL "github.com" with the string "colab.research.google.com" to start the Google Colab Notebooks. 
 
No account is necessary to view the notebooks. However, a Google Account login is required to execute and upload data to the notebooks. 

<a href="https://www.loom.com/share/e88828827d6e4d188404c71e09b75b5f">
    <p> How To Access SAR Google Colab Notebooks - Watch Video</p>
    <img style="max-width:300px;" src="https://cdn.loom.com/sessions/thumbnails/e88828827d6e4d188404c71e09b75b5f-with-play.gif">
  </a>

### Other Notebook Usage Options:

#### Run the Jupyter Notebooks Locally with Conda (tested on Mac)

1. Download the DANSAR GitHub repository to your desired local directory
<pre><code> cd /local/dir

git clone https://github.com/anniepeacock/DANSAR.git 
</code></pre>
2. The DANSAR notebooks are written in Python3 and employ a number of python packages (see [requirements.txt](https://github.com/anniepeacock/DANSAR/blob/main/requirements.txt)). To create a new python environment and install the python packages needed to run the notebooks, install [miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Anaconda](https://docs.anaconda.com/anaconda/install/index.html) if haven't already.

3. Once conda is installed, set the terminal's current working directory to the downloaded DANSAR repository, and create a virtual environment using conda. Here, we name the new environment "sar_notebooks" with python version 3.7.

<pre><code> conda create --name sar_notebooks python=3.7 </code></pre>

4. Activate the new sar_noteboks conda virtual environment

<pre><code> conda activate sar_notebooks </code></pre>

5. Install requirements:

<pre><code>pip install -r requirements.txt</code></pre>

6. Create a new jupyter kernel:

<pre><code>python -m ipykernel install --user --name sar_notebooks</code></pre>

7. To launch the notebooks from the terminal, navigate to the current working directory of the repository. Type the command below and a new internet browser should launch with the notebooks. 

<pre><code>jupyter-notebook</code></pre>


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

## Acknowledgements
UAVSAR data in presentations and/or publications with UAVSAR data courtesy NASA/JPL-Caltech. UAVSAR data policy is governed by JPL's data policy shown here: http://www.jpl.nasa.gov/imagepolicy

## Citation

## Contributors

