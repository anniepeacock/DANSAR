## DANSAR
# Installation

The instructions below are for Linux or macOS systems using Conda for package management.

Clone the repository:

```bash
git clone https://github.com/anniepeacock/DANSAR
cd DANSAR
```

Configure Conda to use `conda-forge`:

```bash
conda config --remove-key channels
conda config --add channels conda-forge
conda config --set channel_priority strict
```

Create and activate the DANSAR environment, then check that the new environment is there:

```bash
conda env create -f environment.yaml
source ~/.bashrc
conda activate DANSAR
conda env list
```

If you with to run Jupyter notebooks, set the kernel:
```bash
python -m ipykernel install --user \
    --name dansar \
    --display-name "Python (DANSAR)"
jupyter kernelspec list
```
Now you can open the notebooks and select the DANSAR kernel in the upper right.
