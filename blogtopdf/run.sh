#!/bin/bash

PROJECT_DIR="/home/avinash/development/python_code/blogtopdf"

source "$PROJECT_DIR/venv/bin/activate"

python "$PROJECT_DIR/blogs2pdf.py" \
    >> "$PROJECT_DIR/cron.log" 2>&1
