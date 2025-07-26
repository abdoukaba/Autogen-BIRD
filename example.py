#!/usr/bin/env python3
"""
Example script demonstrating how to use the AutoGen BIRD SQL Multi-Agent System
with a simple example database.
"""

import os
import sqlite3
import logging
from pathlib import Path
from agents.agent_system import SQLAgentSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'example.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def create_example_database(db_path):
    """Create a simple example database for demonstration."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create employees table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        department TEXT NOT NULL,
        salary REAL NOT NULL,
        hire_date DATE NOT NULL
    )
    ''')
    
    # Create departments table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        location TEXT NOT NULL,
        budget REAL NOT NULL
    )
    ''')
    
    # Insert sample data into employees
    employees_data = [
        (1, 'Alice Smith', 'Engineering', 85000.00, '2019-06-15'),
        (2, 'Bob Johnson', 'Marketing', 72000.00, '2020-01-10'),
        (3, 'Charlie Brown', 'Engineering', 90000.00, '2018-03-22'),
        (4, 'Diana Lee', 'HR', 65000.00, '2021-05-05'),
        (5, 'Edward Davis', 'Finance', 95000.00, '2017-11-18'),
        (6, 'Fiona Wilson', 'Marketing', 70000.00, '2020-07-30'),
        (7, 'George Miller', 'Engineering', 88000.00, '2018-09-12'),
        (8, 'Hannah Garcia', 'Finance', 92000.00, '2019-02-03')
    ]
    cursor.executemany('INSERT OR REPLACE INTO employees VALUES (?, ?, ?, ?, ?)', employees_data)
    
    # Insert sample data into departments
    departments_data = [
        (1, 'Engineering', 'Building A', 1500000.00),
        (2, 'Marketing', 'Building B', 800000.00),
        (3, 'HR', 'Building A', 400000.00),
        (4, 'Finance', 'Building C', 1200000.00)
    ]
    cursor.executemany('INSERT OR REPLACE INTO departments VALUES (?, ?, ?, ?)', departments_data)
    
    conn.commit()
    conn.close()
    
    logger.info(f"Example database created at {db_path}")

def create_example_schema():
    """Create a schema description for the example database."""
    schema = {
        "tables": [
            {
                "name": "employees",
                "columns": [
                    {"name": "id", "type": "INTEGER", "is_primary_key": True},
                    {"name": "name", "type": "TEXT"},
                    {"name": "department", "type": "TEXT"},
                    {"name": "salary", "type": "REAL"},
                    {"name": "hire_date", "type": "DATE"}
                ]
            },
            {
                "name": "departments",
                "columns": [
                    {"name": "id", "type": "INTEGER", "is_primary_key": True},
                    {"name": "name", "type": "TEXT"},
                    {"name": "location", "type": "TEXT"},
                    {"name": "budget", "type": "REAL"}
                ]
            }
        ]
    }
    return schema

def main():
    """Main function demonstrating the use of the SQL agent system."""
    # Create example database
    example_dir = Path('example')
    example_dir.mkdir(exist_ok=True)
    db_path = example_dir / "example.db"
    create_example_database(db_path)
    
    # Create example schema
    schema = create_example_schema()
    
    # Initialize agent system
    agent_system = SQLAgentSystem('configs/agent_config.yaml')
    
    # Example question
    question = "What is the average salary of employees in each department?"
    
    logger.info(f"Processing question: {question}")
    
    # Generate SQL query using the agent system
    sql_query, trace = agent_system.solve(
        question=question,
        schema=schema,
        db_path=str(db_path)
    )
    
    logger.info(f"Generated SQL: {sql_query}")
    
    # Execute the query and display results
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(sql_query)
    results = cursor.fetchall()
    column_names = [desc[0] for desc in cursor.description]
    conn.close()
    
    print("\n--- Results ---")
    print(f"Question: {question}")
    print(f"SQL Query: {sql_query}")
    print("\nResults:")
    print(", ".join(column_names))
    for row in results:
        print(", ".join(str(item) for item in row))

if __name__ == "__main__":
    main()