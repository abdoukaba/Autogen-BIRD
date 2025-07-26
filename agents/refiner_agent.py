#!/usr/bin/env python3
"""
RefinerAgent: Agent responsible for refining initial SQL queries.
This agent takes an initial SQL query and the error message (if any)
and attempts to fix/refine the query for successful execution.
"""

import logging
from autogen.agentchat import ConversableAgent
from typing import Dict

logger = logging.getLogger(__name__)

class RefinerAgent:
    """
    Agent responsible for refining and fixing SQL queries based on errors or feedback.
    """

    def __init__(self, config: Dict):
        self.config = config
        self.llm_config = {
            "config_list": [
                {
                    "model": config.get("model", "gpt-4-turbo"),
                    "api_key": config.get("openai_api_key")
                }
            ]
        }
        self.refiner_agent = ConversableAgent(
            name="sql_refiner",
            system_message=self._get_system_prompt(),
            llm_config=self.llm_config
        )
        logger.info("RefinerAgent initialized")

    def refine_sql(self, question: str, schema: Dict, prev_sql: str, error_message: str = "") -> str:
        logger.info("Refining SQL for question: %s", question)
        schema_str = self._format_schema(schema)
        prompt = f"""
        Question: {question}

        Database Schema:
        {schema_str}

        Previous SQL:
        {prev_sql}

        Error Message (if any):
        {error_message}

        Please refine or fix the SQL query to ensure it runs successfully.
        """
        chat_response = self.refiner_agent.generate_reply(
            [{"role": "user", "content": prompt}]
        )
        if hasattr(chat_response, "response"):
            chat_response = chat_response.response

        sql_query = self._extract_sql(chat_response)
        logger.info("SQL refinement complete: %s", sql_query)
        return sql_query

    def _get_system_prompt(self) -> str:
        return (
            "IMPORTANT: You must ONLY use table and column names exactly as shown in the schema below. Do NOT invent or guess any table or column names. If a required table/column does not exist, explain or return an empty result."
            "You are an expert SQL fixer. Given a database schema, a previous SQL query, "
            "and an error message (if any), generate a corrected SQL query that will execute successfully. "
            "Only return the SQL code in a code block (```sql ... ```)."
        )
    
    def _extract_sql(self, agent_response: str) -> str:
        """
        Extract the SQL query from the agent's response (code block, inline, or raw).
        """
        import re

        # Try code block first
        sql_match = re.search(r'```sql\s*([\s\S]+?)```', agent_response)
        if sql_match:
            return sql_match.group(1).strip()

        # If not found, look for standalone SQL SELECT/WITH
        sql_patterns = [
            r'(SELECT\s+[\s\S]+?;)',
            r'(WITH\s+[\s\S]+?;)',
        ]
        for pattern in sql_patterns:
            match = re.search(pattern, agent_response, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # If LLM gives step-by-step followed by SQL, try to extract last SELECT
        selects = re.findall(r'(SELECT\s+[\s\S]+?;)', agent_response, re.IGNORECASE)
        if selects:
            return selects[-1].strip()

        logger.warning("Could not extract SQL from agent response:\n%s", agent_response)
        return "SELECT 'ERROR: Could not generate SQL';"


    def _format_schema(self, schema: Dict) -> str:
        """
        Outputs a clear, LLM-friendly table/column summary for the prompt.
        Example:
        Tables in this database:
        - california_schools (columns: id, name, county, free_rate)
        - teachers (columns: teacher_id, name, school_id, subject)
        
        End of schema.
        """
        formatted_schema = []
        for table in schema.get("tables", []):
            table_name = table.get("name", "")
            columns = table.get("columns", [])
            column_names = [col.get("name", "") for col in columns]
            formatted_schema.append(f"- {table_name} (columns: {', '.join(column_names)})")
        schema_str = "Tables in this database:\n"
        schema_str += "\n".join(formatted_schema)
        schema_str += "\n\nEnd of schema."
        return schema_str

        logger.warning("Could not extract SQL from agent response")
        return "SELECT 'ERROR: Could not generate SQL';"
