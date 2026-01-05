#!/bin/bash

# Activate conda environment and start server
# source ~/anaconda3/etc/profile.d/conda.sh
conda activate venv
python -m uvicorn --workers 4 src.api.main:app --host 0.0.0.0 --port 8000
