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

Create and activate the DANSAR environment:

```bash
conda env create -f environment.yaml
conda activate DANSAR
```
