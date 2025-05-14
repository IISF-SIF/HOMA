#!/bin/bash

source ./venv/bin/activate

# List of models to evaluate
models=("gemma3:12b" "qwen2.5:14b" "phi4" "gemma3:27b" "qwen2.5:32b")

for MODEL_NAME in "${models[@]}"; do
    REPORT_FILE="evaluation_report_${MODEL_NAME}.json"
    
    echo -e "\n========= Evaluating $MODEL_NAME ========="
    
    echo "Updating utils.py with model $MODEL_NAME..."
    sed -i "s/\(model_name='\)[^']*\('.*\)/\1$MODEL_NAME\2/" ./utils/utils.py

    echo "Updating evaluator.py to write report to $REPORT_FILE..."
    sed -i "s/evaluation_report[^']*/$REPORT_FILE/" evaluator.py

    echo "Installing Ollama Model $MODEL_NAME..."
    ollama pull "$MODEL_NAME"

    echo "Running evaluation..."
    python evaluator.py

    echo "Removing model $MODEL_NAME..."
    ollama rm "$MODEL_NAME"

    echo "Finished evaluation for $MODEL_NAME."
done
