#!/usr/bin/env python3
"""
Evaluation script for the BIRD SQL Mini-Dev benchmark.
This script loads the benchmark data, runs the multi-agent system,
and evaluates the execution accuracy of the predicted SQL queries.
"""

import os
import json
import sqlite3
import logging
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from typing import Dict, List, Any, Optional


logger = logging.getLogger(__name__)

def execute_sql(db_path: str, sql_query: str) -> tuple:
    """
    Execute a SQL query on the given SQLite database.
    
    Args:
        db_path: Path to the SQLite database file
        sql_query: SQL query to execute
        
    Returns:
        Tuple containing (column_names, results)
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        results = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()
        return column_names, results
    except Exception as e:
        logger.error(f"Error executing SQL: {e}")
        return None, str(e)

def normalize_sql_result(result: tuple) -> tuple:
    """
    Normalize SQL execution results for comparison.
    
    Args:
        result: Tuple of (column_names, rows)
        
    Returns:
        Normalized version of the result for comparison
    """
    if result[0] is None:  # Error case
        return result
    
    columns, rows = result
    
    # Convert all values to strings for consistent comparison
    normalized_rows = []
    for row in rows:
        normalized_row = []
        for val in row:
            if val is None:
                normalized_row.append(None)
            elif isinstance(val, (int, float)):
                normalized_row.append(float(val))
            else:
                normalized_row.append(str(val).lower())
        normalized_rows.append(tuple(normalized_row))
    
    normalized_rows.sort()
    
    return columns, normalized_rows

def results_match(result1: tuple, result2: tuple) -> bool:
    """
    Check if two SQL execution results match.
    
    Args:
        result1: First result tuple (columns, rows)
        result2: Second result tuple (columns, rows)
        
    Returns:
        True if results match, False otherwise
    """
    # Handle error cases
    if result1[0] is None or result2[0] is None:
        return False
    
    norm_result1 = normalize_sql_result(result1)
    norm_result2 = normalize_sql_result(result2)
    
    cols1 = set([c.lower() for c in norm_result1[0]])
    cols2 = set([c.lower() for c in norm_result2[0]])
    
    if cols1 != cols2:
        return False
    
    if norm_result1[0] != norm_result2[0]:
        col_map = {old: new for old, new in zip(norm_result1[0], norm_result2[0])}
        # Remap columns in result1
        remapped_rows = []
        for row in norm_result1[1]:
            remapped_row = tuple(row[norm_result1[0].index(col)] for col in norm_result2[0])
            remapped_rows.append(remapped_row)
        norm_result1 = (norm_result2[0], remapped_rows)
    
    # Compare row counts
    if len(norm_result1[1]) != len(norm_result2[1]):
        return False
    
    # Compare actual rows (already normalized and sorted)
    return norm_result1[1] == norm_result2[1]

def load_benchmark_data(data_dir: Path, limit: Optional[int] = None) -> List[Dict]:
    """
    Load the BIRD SQL Mini-Dev benchmark data.
    
    Args:
        data_dir: Path to the mini_dev directory
        limit: Optional limit on number of questions to load
        
    Returns:
        List of benchmark questions with their metadata
    """
    dev_file = data_dir / "dev.json"
    if not dev_file.exists():
        raise FileNotFoundError(f"Dev file not found: {dev_file}")
    
    with open(dev_file, 'r') as f:
        benchmark_data = json.load(f)
    
    if limit is not None:
        benchmark_data = benchmark_data[:limit]
    
    return benchmark_data

def evaluate_benchmark(agent_system: Any, data_dir: Path, limit: Optional[int] = None) -> Dict:
    """
    Evaluate the multi-agent system on the BIRD SQL Mini-Dev benchmark.
    
    Args:
        agent_system: The multi-agent system to evaluate
        data_dir: Path to the mini_dev directory
        limit: Optional limit on number of questions to evaluate
        
    Returns:
        Dictionary with evaluation results
    """
    benchmark_data = load_benchmark_data(data_dir, limit)
    
    results = {
        "questions": [],
        "total": len(benchmark_data),
        "correct": 0
    }
    
    for idx, question_data in enumerate(tqdm(benchmark_data, desc="Evaluating")):
        question_id = question_data["question_id"]
        question = question_data["question"]
        db_path = data_dir / "database" / question_data["db_id"] / "sqlite.db"
        gold_sql = question_data["gold_sql"]
        
        logger.info(f"Processing question {idx+1}/{len(benchmark_data)}: {question_id}")
        logger.info(f"Question: {question}")
        
        # Get the database schema
        schema_path = data_dir / "database" / question_data["db_id"] / "schema.json"
        logger.info(f"Loading schema from: {schema_path}")
        try:
            with open(schema_path, 'r') as f:
                schema_data = json.load(f)
        except FileNotFoundError:
            logger.error(f"Schema file not found: {schema_path}")
            alt_schema_path = os.path.join(str(data_dir), "database", question_data["db_id"], "schema.json")
            logger.info(f"Trying alternate path: {alt_schema_path}")
            with open(alt_schema_path, 'r') as f:
                schema_data = json.load(f)
        
        predicted_sql, agent_trace = agent_system.solve(
            question=question,
            schema=schema_data,
            db_path=str(db_path)
        )
        print("Using DB file at:", os.path.abspath(db_path))
        gold_result = execute_sql(str(db_path), gold_sql)
        predicted_result = execute_sql(str(db_path), predicted_sql)
        
        execution_correct = results_match(gold_result, predicted_result)
        
        question_result = {
            "question_id": question_id,
            "question": question,
            "gold_sql": gold_sql,
            "predicted_sql": predicted_sql,
            "execution_correct": execution_correct,
            "agent_trace": agent_trace
        }
        
        results["questions"].append(question_result)
        if execution_correct:
            results["correct"] += 1
        
        logger.info(f"Question {question_id} - Execution correct: {execution_correct}")
        logger.info(f"Gold SQL: {gold_sql}")
        logger.info(f"Predicted SQL: {predicted_sql}")
    
    results["accuracy"] = results["correct"] / results["total"] if results["total"] > 0 else 0
    logger.info(f"Overall execution accuracy: {results['accuracy']:.2%}")
    
    return results