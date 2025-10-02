
# HOMA: Home Orchestration using Multi-Agent systems

![License](https://img.shields.io/badge/license-MIT-blue.svg)

HOMA is a multilingual agentic framework designed for home automation systems, enabling users to interact with smart home devices through natural language commands in multiple languages. The system leverages Large Language Models (LLMs) to interpret complex multilingual and code-mixed commands, translating them into actionable device control instructions.

## Features

- **Multilingual Support**: Handles commands in 11+ languages, including low-resource Indian languages
- **Multi-Device Control**: Supports various household appliances (TV, AC, fan, microwave, washer, dryer, fridge)
- **Complex Command Interpretation**: Understands concurrent and sequential tasks
- **Distributed Agent Architecture**: Uses specialized agents for different devices
- **Comprehensive Evaluation Framework**: Analyze performance across languages, device types, and command complexity
- **Interactive Dashboard**: Visualize evaluation results and performance metrics

## Architecture

HOMA uses a distributed multi-agent architecture:

1. **Orchestrator Agent**: Classifies commands, decomposes tasks, and manages execution
2. **Device Agents**: Specialized agents for each device type
3. **Evaluation System**: Measures performance across multiple dimensions
4. **Dashboard**: Visualizes results and provides insights

## Installation

### Prerequisites

- Python 3.8+
- Ollama or API access to LLMs (Gemini/Google AI)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/IISF-SIF/HOMA.git
cd HOMA
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
- Create a `.env` file in the `utils/` directory
- For Gemini API access, add: `GEMINI_API_KEY=your_api_key_here`

## Usage

### Running the System

1. Start the agent:
```bash
python main.py
```

2. Type in natural language commands like:
   - "Turn on the TV and set the volume to 30"
   - "Turn off the AC after 2 hours"
   - "Start the microwave for 2 minutes at 600 watts"
   - "Switch on fan and set AC temperature to 24"

### Dataset Creation

Generate synthetic datasets for evaluation:

```bash
python create_dataset.py
```

This creates multilingual commands with ground truth annotations for evaluation.

### Evaluation

Evaluate model performance on the dataset:

```bash
python evaluator.py
```

The evaluation produces detailed JSON reports in the `dataset_and_results/` directory.

### Results Dashboard

View and analyze evaluation results:

```bash
streamlit run analysis_dashboard.py
```

This opens an interactive dashboard with performance metrics, filtering options, and visualization tools.

## Models

HOMA has been evaluated with several open-source LLMs:

- Gemma 3 (1B, 4B, 12B, 27B)
- Gemma 2 (9B)
- Qwen 2.5 (1.5B, 3B, 7B, 14B)
- Phi-4

Performance varies by model size, with larger models generally achieving higher accuracy.

## Evaluation Metrics

The framework evaluates:

- Device recognition accuracy
- Task type classification (concurrent vs. sequential)
- Mode recognition
- Parameter extraction
- Overall weighted accuracy

Performance is analyzed across languages, device types, and command complexity.

## Configuration

Edit the `utils/config.json` file to adjust:

- Model selection
- Concurrency settings
- Dataset generation parameters
- Device mappings and capabilities

## Dataset Information

The repository includes a sample dataset (`11_languages_200_points_dataset.csv`) with commands in 11 languages covering multiple device types and operations.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Acknowledgments

This project was developed as part of a collaboration between Vellore Institute of Technology, Samsung R&D Institute Bangalore, and The University of Edinburgh.
