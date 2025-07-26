#!/usr/bin/env python3
"""
DecomposerAgent: Agent responsible for decomposing questions and generating SQL queries.
This agent breaks down complex questions and generates SQL queries using chain-of-thought
reasoning, following the approach described in the MAC-SQL paper.
"""

import logging
from autogen.agentchat import ConversableAgent
from typing import Dict


logger = logging.getLogger(__name__)

class DecomposerAgent:
    """
    Agent responsible for decomposing natural language questions and
    generating SQL queries using chain-of-thought reasoning.
    """

    def __init__(self, config: Dict):
        """
        Initialize the DecomposerAgent with the given configuration.

        Args:
            config: Configuration dictionary with LLM settings
        """
        self.config = config
        self.llm_config = self._prepare_llm_config(config)
        self.decomposer_agent = ConversableAgent(
            name="sql_generator",
            system_message=self._get_system_prompt(),
            llm_config=self.llm_config
        )
        logger.info("DecomposerAgent initialized")

    def _prepare_llm_config(self, config: Dict) -> Dict:
        """Prepare the LLM configuration for the agent."""
        return {
            "config_list": [
                {
                    "model": config.get("model", "gpt-4-turbo"),
                    "api_key": config.get("openai_api_key")
                }
            ]
        }

    def generate_sql(self, question: str, schema: Dict) -> str:
        """
        Generate a SQL query for the given question using the provided schema.

        Args:
            question: The natural language question
            schema: The pruned database schema

        Returns:
            Generated SQL query
        """
        logger.info("Generating SQL for question: %s", question)

        schema_str = self._format_schema(schema)
        decomposer_input = f"""
        Question: {question}

        Database Schema:
        {schema_str}

        Please generate a SQL query to answer this question. Use step-by-step reasoning.
        """

        # Use ConversableAgent's generate_reply with a messages list
        chat_response = self.decomposer_agent.generate_reply(
            [{"role": "user", "content": decomposer_input}]
        )
        if hasattr(chat_response, "response"):
            chat_response = chat_response.response

        sql_query = self._extract_sql(chat_response)

        logger.info("SQL generation complete: %s", sql_query)
        return sql_query

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the decomposer agent."""
        return """
        IMPORTANT: You must ONLY use table and column names exactly as shown in the schema below. Do NOT invent or guess any table or column names. If a required table/column does not exist, explain or return an empty result.
        You are an expert in SQL query generation. Your task is to convert natural language questions
        into SQL queries by using chain-of-thought reasoning.

        Follow these steps for each question:

        1. ANALYZE THE QUESTION:
           - Identify the main entities and attributes mentioned
           - Determine the operations needed (filtering, joining, aggregation, etc.)
           - Identify any conditions or constraints

        2. BREAK DOWN COMPLEX QUESTIONS:
           - For complex questions, decompose them into simpler sub-questions
           - For each sub-question, determine what intermediate results are needed

        3. UNDERSTAND THE SCHEMA:
           - Identify the relevant tables for the question
           - Determine the relationships between these tables
           - Identify the columns needed for selection, filtering, and joining

        4. GENERATE THE SQL QUERY:
           - Start with simple SELECT, FROM, WHERE clauses
           - Add JOINs to connect related tables
           - Add conditions and filters in the WHERE clause
           - Include GROUP BY and aggregation functions if needed
           - Add HAVING clauses for filtering aggregated results
           - Use ORDER BY for sorting if required
           - Apply LIMIT if the question asks for specific number of results

        5. VERIFY THE QUERY:
           - Check that all entities mentioned in the question are represented
           - Ensure all conditions and constraints are included
           - Verify that the query will return the expected result format

        Your final answer MUST include the complete SQL query formatted with proper indentation.
        Wrap your SQL query in ```sql and ``` tags.

        Example output format:
        Let me analyze this step by step.
        [Your reasoning here...]

        The SQL query to answer this question is:
        ```sql
        SELECT column1, column2
        FROM table1
        JOIN table2 ON table1.id = table2.id
        WHERE condition
        GROUP BY column1
        HAVING aggregate_condition
        ORDER BY column3;
        ```
        """

    def _format_schema(self, schema: Dict) -> str:
        """
        Format the schema with both a quick summary and a detailed view for the LLM.
        Example:
        Tables in this database:
        - california_schools (columns: id, name, county, free_rate)
        - other_table (columns: col1, col2)

        End of schema.

        [Full schema details...]
        """
        # Quick summary for LLM table name clarity
        summary_lines = []
        for table in schema.get("tables", []):
            table_name = table.get("name", "")
            columns = table.get("columns", [])
            column_names = [col.get("name", "") for col in columns]
            summary_lines.append(f"- {table_name} (columns: {', '.join(column_names)})")
        schema_str = "Tables in this database:\n" + "\n".join(summary_lines) + "\n\nEnd of schema.\n\n"

        # (Optional) Full detailed schema for LLM reference
        detailed_lines = []
        for table in schema.get("tables", []):
            table_name = table.get("name", "")
            columns = table.get("columns", [])
            primary_keys = [col.get("name", "") for col in columns if col.get("is_primary_key", False)]
            foreign_keys = []
            if "foreign_keys" in table:
                for fk in table["foreign_keys"]:
                    if isinstance(fk, dict) and "column_name" in fk and "referenced_table" in fk and "referenced_column" in fk:
                        foreign_keys.append(
                            f"{fk['column_name']} -> {fk['referenced_table']}.{fk['referenced_column']}"
                        )
            column_descriptions = []
            for col in columns:
                col_name = col.get("name", "")
                col_type = col.get("type", "")
                pk_marker = " (PK)" if col_name in primary_keys else ""
                column_descriptions.append(f"{col_name} ({col_type}){pk_marker}")
            table_info = [
                f"Table: {table_name}",
                f"Columns: {', '.join(column_descriptions)}"
            ]
            if primary_keys:
                table_info.append(f"Primary Keys: {', '.join(primary_keys)}")
            if foreign_keys:
                table_info.append(f"Foreign Keys: {'; '.join(foreign_keys)}")
            detailed_lines.append("\n".join(table_info))
        schema_str += "\n\n".join(detailed_lines)

        return schema_str


    def _extract_sql(self, agent_response: str) -> str:
        """Extract the SQL query from the agent's response."""
        import re

        # Try to extract SQL from code blocks
        sql_match = re.search(r'```sql\s*(.*?)\s*```', agent_response, re.DOTALL)
        if sql_match:
            return sql_match.group(1).strip()

        # If no SQL code block found, try to find SQL-like patterns
        sql_patterns = [
            r'SELECT\s+.*?(?:;|$)',
            r'WITH\s+.*?(?:;|$)'
        ]

        for pattern in sql_patterns:
            match = re.search(pattern, agent_response, re.IGNORECASE | re.DOTALL)
            if match:
                sql = match.group(0).strip()
                # Add semicolon if missing
                if not sql.endswith(';'):
                    sql += ';'
                return sql

        # If no SQL found, return empty string or error message
        logger.warning("Could not extract SQL from agent response")
        return "SELECT 'ERROR: Could not generate SQL';"
