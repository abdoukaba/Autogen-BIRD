#!/usr/bin/env python3
"""
Main entry point for the AutoGen BIRD SQL Mini-Dev benchmark evaluation.
This script orchestrates the multi-agent system to solve SQL queries
based on natural language questions and evaluates the results.
"""

import os
import argparse
import logging
import json
from pathlib import Path
from tqdm import tqdm

from evaluate import evaluate_benchmark
from agents.agent_system import SQLAgentSystem

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'output.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='AutoGen BIRD SQL Mini-Dev Benchmark')
    parser.add_argument('--data_dir', type=str, default='mini_dev-main',
                        help='Path to the BIRD mini_dev dataset')
    parser.add_argument('--config', type=str, default='configs/agent_config.yaml',
                        help='Path to the agent configuration file')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of questions to process (for testing)')
    parser.add_argument('--output', type=str, default='logs/results.json',
                        help='Path to save evaluation results')
    return parser.parse_args()

def main():
    """Main function to run the benchmark evaluation."""
    args = parse_args()
    
    logger.info("Starting AutoGen BIRD SQL Mini-Dev benchmark evaluation")
    
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        logger.error(f"Dataset directory not found: {data_dir}")
        return
    
    agent_system = SQLAgentSystem(args.config)
    
    # Run evaluation on the benchmark
    results = evaluate_benchmark(
        agent_system=agent_system,
        data_dir=data_dir,
        limit=args.limit
    )
    
    total_questions = len(results['questions'])
    correct_answers = sum(1 for q in results['questions'] if q['execution_correct'])
    execution_accuracy = correct_answers / total_questions if total_questions > 0 else 0
    
    logger.info(f"Evaluation complete. Execution Accuracy: {execution_accuracy:.2%}")
    logger.info(f"Total questions: {total_questions}")
    logger.info(f"Correct executions: {correct_answers}")
    
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Detailed results saved to {args.output}")

if __name__ == "__main__":
    main()