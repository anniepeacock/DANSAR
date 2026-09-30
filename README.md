# DANSAR
Data Application Notebooks with Synthetic Aperture Radar

The instructions below are for a linux or MacOS system using conda package management:

git clone https://github.com/anniepeacock/DANSAR
cd DANSAR
conda config --remove-key channels 
conda config --add channels conda-forge
conda config --set channel_priority strict
conda env create -f environment.yaml
conda activate DANSAR
