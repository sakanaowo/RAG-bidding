#!/bin/bash

# Activate conda environment and start server
source ~/anaconda3/etc/profile.d/conda.sh
conda activate venv
python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
