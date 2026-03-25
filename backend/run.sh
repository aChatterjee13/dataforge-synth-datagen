#!/bin/bash
# Set TensorFlow environment variables BEFORE starting uvicorn
# This prevents mutex lock warnings on macOS

export TF_CPP_MIN_LOG_LEVEL=3
export KMP_DUPLICATE_LIB_OK=TRUE
export OMP_NUM_THREADS=1
export TF_NUM_INTEROP_THREADS=1
export TF_NUM_INTRAOP_THREADS=1

# Activate virtual environment if available
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Start uvicorn with these environment variables
uvicorn app.main:app --reload --port 8000
