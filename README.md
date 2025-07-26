# AutoGen BIRD SQL Multi-Agent System

This project implements a multi-agent system using AutoGen to solve the BIRD-SQL Mini-Dev benchmark. The goal is to achieve at least 60% execution accuracy on SQL query generation from natural language questions.

## Overview

The system follows the MAC-SQL (Multi-Agent Collaborative SQL generation) framework, consisting of three specialized agents:

1. **Selector Agent**: Prunes the database schema to include only relevant tables and columns
2. **Decomposer Agent**: Generates initial SQL queries using chain-of-thought reasoning
3. **Refiner Agent**: Iteratively refines SQL queries when execution errors occur

## Project Structure

```
autogen-bird-mini-dev/
├── agents/                    # Agent implementations
│   ├── agent_system.py        # Main agent orchestration system
│   ├── selector_agent.py      # Schema selection agent
│   ├── decomposer_agent.py    # SQL generation agent
│   ├── refiner_agent.py       # SQL refinement agent
├── configs/                   # Configuration files
│   └── agent_config.yaml      # Agent system configuration
├── logs/                      # Log files (auto-generated)
├── mini_dev-main/             # BIRD Mini-Dev dataset (to be extracted)
├── evaluate.py                # Evaluation script
├── main.py                    # Main entry point
└── requirements.txt           # Project dependencies
```

## Setup and Installation

1. Clone the repository and navigate to the project directory
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Extract the BIRD Mini-Dev dataset:
   ```
   unzip mini_dev-main.zip -d .
   ```
5. Set up your OpenAI API key:
   ```
   export OPENAI_API_KEY="your-api-key"  # On Windows: set OPENAI_API_KEY=your-api-key
   ```

## Usage

Run the evaluation on the BIRD Mini-Dev benchmark:

```
python main.py --data_dir mini_dev-main --config configs/agent_config.yaml
```

Additional options:
- `--limit N`: Process only the first N questions (useful for testing)
- `--output PATH`: Specify output path for results (default: logs/results.json)

## How It Works

1. The Selector Agent analyzes the question and database schema to identify relevant tables and columns
2. The Decomposer Agent generates an initial SQL query using the pruned schema
3. The system attempts to execute the query on the database
4. If execution fails, the Refiner Agent fixes the query based on error messages
5. Steps 3-4 repeat for up to `max_iterations` times or until execution succeeds
6. The system evaluates execution accuracy by comparing results with gold standard queries

## Results

Results are saved as a JSON file with detailed information for each question:
- Question text
- Gold SQL query
- Predicted SQL query
- Execution correctness
- Agent interactions and reasoning trace

Overall accuracy statistics are also included in the results file.

## Customization

You can customize the system behavior by modifying `configs/agent_config.yaml`:
- Change LLM models used by each agent
- Adjust temperature settings
- Configure the maximum number of refinement iterations

## Requirements

- Python 3.8+
- AutoGen
- Access to OpenAI API (for GPT-4 or other compatible models)
- SQLite for query execution

## References

- BIRD: Big Bench for Large-Language Models of Code - [arXiv:2312.11242](https://arxiv.org/abs/2312.11242)