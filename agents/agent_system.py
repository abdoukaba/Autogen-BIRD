#!/usr/bin/env python3
"""
SQLAgentSystem: Orchestrates the multi-agent system for SQL query generation.
Based on the MAC-SQL framework described in the BIRD paper, this system
coordinates three agents: Selector, Decomposer, and Refiner.
"""

import os
import yaml
import logging
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from typing import Dict, Tuple, List, Any, Optional
from pathlib import Path

from .selector_agent import SelectorAgent
from .decomposer_agent import DecomposerAgent
from .refiner_agent import RefinerAgent

logger = logging.getLogger(__name__)

class SQLAgentSystem:
    """
    Multi-agent system for SQL query generation based on the MAC-SQL framework.
    """
    
    def __init__(self, config_path: str):
        """
        Initialize the SQLAgentSystem with the given configuration.
        
        Args:
            config_path: Path to the agent configuration YAML file
        """
        self.config = self._load_config(config_path)
        self.max_iterations = self.config.get('max_iterations', 3)
        
        # Initialize the agents
        self.selector_agent = SelectorAgent(self.config.get('selector', {}))
        self.decomposer_agent = DecomposerAgent(self.config.get('decomposer', {}))
        self.refiner_agent = RefinerAgent(self.config.get('refiner', {}))
        
        logger.info("SQLAgentSystem initialized with config from %s", config_path)
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    
    def solve(self, question: str, schema: Dict, db_path: str) -> Tuple[str, Dict]:
        """
        Solve a natural language question by generating a SQL query.
        
        Args:
            question: The natural language question
            schema: Database schema information
            db_path: Path to the SQLite database
            
        Returns:
            Tuple containing (final_sql_query, agent_trace)
        """
       
        
     
        trace = {
            "question": question,
            "selector_output": None,
            "decomposer_output": None,
            "refiner_iterations": []
        }
        
       
        pruned_schema = schema

        pruned_schema = self.selector_agent.select_relevant_schema(question, schema)
        print("SCHEMA SENT TO AGENT:")
        import json
        print(json.dumps(pruned_schema, indent=2))

        trace["selector_output"] = pruned_schema
        logger.info("Selector agent pruned schema: %s", str(pruned_schema)[:100] + "...")
        
       
        initial_sql = self.decomposer_agent.generate_sql(question, pruned_schema)
        trace["decomposer_output"] = initial_sql
        logger.info("Decomposer agent generated SQL: %s", initial_sql)
        
        # Refiner Agent iteratively refines SQL if needed
        current_sql = initial_sql
        iteration = 0
        
        while iteration < self.max_iterations:
            # Try to execute the SQL
            import sqlite3
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(current_sql)
                cursor.fetchall() 
                conn.close()
                
                
                logger.info("SQL execution successful on iteration %d", iteration)
                break
                
            except sqlite3.Error as e:
                logger.info("SQL execution failed: %s", str(e))
                
                # Refine the SQL based on the error
                iteration_trace = {
                    "iteration": iteration + 1,
                    "sql_before": current_sql,
                    "error": str(e)
                }
                
                current_sql = self.refiner_agent.refine_sql(
                question=question,
                schema=pruned_schema,
                prev_sql=current_sql,        
                error_message=str(e)
                )

                
                iteration_trace["sql_after"] = current_sql
                trace["refiner_iterations"].append(iteration_trace)
                
                logger.info("Refiner agent refined SQL: %s", current_sql)
                
            iteration += 1
        
        logger.info("Final SQL: %s", current_sql)
        return current_sql, trace