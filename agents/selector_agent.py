#!/usr/bin/env python3
"""
SelectorAgent: Agent responsible for pruning unnecessary schema elements.
This agent analyzes the question and database schema to identify the most
relevant tables and columns, reducing the complexity for SQL generation.
"""

import logging
from autogen.agentchat import ConversableAgent
from typing import Dict

logger = logging.getLogger(__name__)

class SelectorAgent:
    """
    Agent responsible for pruning the database schema to include only
    the most relevant tables and columns for a given question.
    """
    def __init__(self, config: Dict):
        """
        Initialize the SelectorAgent with the given configuration.
        Args:
            config: Configuration dictionary with LLM settings
        """
        self.config = config
        self.llm_config = self._prepare_llm_config(config)
        logger.info("SelectorAgent initialized")

        # Pre-create the conversable agent for efficiency
        self.selector_agent = ConversableAgent(
            name="schema_selector",
            system_message=self._get_system_prompt(),
            llm_config=self.llm_config
        )

    def _prepare_llm_config(self, config: Dict) -> Dict:
        """Prepare the LLM configuration for the agent."""
        # This matches official AutoGen's config structure
        return {
            "config_list": [
                {
                    "model": config.get("model", "gpt-4-turbo"),
                    "api_key": config.get("openai_api_key")
                }
            ],
          
        }

    def select_relevant_schema(self, question: str, schema: Dict) -> Dict:
        """
        Select relevant tables and columns from the schema based on the question.
        Returns pruned schema containing only relevant tables and columns.
        """
        logger.info("Selecting relevant schema for question: %s", question)
        schema_str = self._format_schema(schema)
        selector_input = f"""
        Question: {question}

        Full Database Schema:
        {schema_str}

        Please select only the relevant tables and columns for answering this question.
        """

        # Use the .chat() method on the ConversableAgent
        chat_response = self.selector_agent.generate_reply(
        [{"role": "user", "content": selector_input}])
        if hasattr(chat_response, "response"):
            chat_response = chat_response.response



        pruned_schema = self._extract_pruned_schema(chat_response, schema)
        logger.info("Schema selection complete, pruned from %d to %d tables",
                   len(schema.get("tables", [])), len(pruned_schema.get("tables", [])))
        return pruned_schema

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the selector agent."""
        return """
        IMPORTANT: You must ONLY use table and column names exactly as shown in the schema below. Do NOT invent or guess any table or column names. If a required table/column does not exist, explain or return an empty result.
        You are an expert database analyst specialized in identifying relevant schema elements for SQL queries.

        Your task is to analyze a question and a database schema, then select ONLY the tables and columns
        that are necessary to answer the question. This helps reduce complexity for SQL generation.

        Guidelines:
        1. Analyze the question carefully to identify entities and relationships needed.
        2. Include ALL tables and columns that could be relevant to the question.
        3. EXCLUDE tables and columns that are definitely not needed.
        4. Consider tables that might be needed for JOINs to connect relevant entities.
        5. If in doubt about a table or column, include it rather than exclude it.
        6. For questions involving aggregations, include columns needed for grouping and computation.

        Output your answer in JSON format:
        {
            "tables": [
                {
                    "name": "table_name",
                    "columns": ["column1", "column2", ...]
                },
                ...
            ]
        }

        Be concise and only include the JSON output without additional explanations.
        """

    from typing import Dict, Any

    def _format_schema(self, schema: Dict[str, Any]) -> str:
        """
        Format the schema as a string for the LLM prompt.

        Args:
            schema: Dict with "tables" key. Each table has "name" and "columns".
                    Each column has "name" and "type".

        Returns:
            str: Formatted schema string.
        """
        formatted_schema = []
        for table in schema.get("tables", []):
            table_name = table.get("name", "")
            columns = table.get("columns", [])
            column_descriptions = [
                f"{col.get('name', '')} ({col.get('type', '')})"
                for col in columns
            ]
            formatted_schema.append(
                f"Table: {table_name}\nColumns: {', '.join(column_descriptions)}"
            )
        return "\n\n".join(formatted_schema)


    def _extract_pruned_schema(self, agent_response: str, original_schema: Dict) -> Dict:
        """
        Extract the pruned schema from the agent's response.
        If parsing fails, fall back to the original schema.
        """
        try:
            import json
            import re
            # Try to find JSON in the response
            json_match = re.search(r'```json\s*(.*?)\s*```', agent_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'(\{.*\})', agent_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = agent_response
            pruned_schema_data = json.loads(json_str)
            # Convert to expected schema format
            pruned_schema = {"tables": []}
            for table_info in pruned_schema_data.get("tables", []):
                table_name = table_info.get("name", "")
                column_names = table_info.get("columns", [])
                original_table = next(
                    (t for t in original_schema.get("tables", []) if t.get("name") == table_name),
                    None
                )
                if original_table:
                    columns = [
                        col for col in original_table.get("columns", [])
                        if col.get("name") in column_names
                    ]
                    pruned_schema["tables"].append({
                        "name": table_name,
                        "columns": columns
                    })
            return pruned_schema
        except Exception as e:
            logger.error("Failed to parse pruned schema: %s. Using original schema instead.", str(e))
            return original_schema
