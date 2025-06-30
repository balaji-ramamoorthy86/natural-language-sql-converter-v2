import os
import logging
from typing import Dict, Any
import json
import re

try:
    from azure.ai.inference import ChatCompletionsClient
    from azure.ai.inference.models import SystemMessage, UserMessage
    from azure.core.credentials import AzureKeyCredential
except ImportError:
    # Fallback to openai library if azure-ai-inference is not available
    try:
        import openai
    except ImportError:
        openai = None

class AzureOpenAIService:
    """Service for interacting with Azure OpenAI to generate SQL queries"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Azure OpenAI configuration from environment variables
        self.endpoint = os.getenv('AZURE_OPENAI_ENDPOINT', '')
        self.api_key = os.getenv('AZURE_OPENAI_API_KEY', '')
        self.deployment_name = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4')
        self.api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-01')
        
        # Initialize client
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Azure OpenAI client"""
        try:
            if self.endpoint and self.api_key:
                self.client = ChatCompletionsClient(
                    endpoint=self.endpoint,
                    credential=AzureKeyCredential(self.api_key)
                )
                self.logger.info("Azure OpenAI client initialized successfully")
            else:
                self.logger.warning("Azure OpenAI credentials not found. Using fallback service.")
        except Exception as e:
            self.logger.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
            self.client = None
    
    def generate_sql(self, natural_language: str, schema_context: str = "") -> Dict[str, Any]:
        """
        Generate SQL query from natural language description
        
        Args:
            natural_language: The natural language description
            schema_context: Database schema context information
            
        Returns:
            Dictionary containing success status, SQL query, explanation, and any errors
        """
        try:
            if not self.client:
                return self._fallback_sql_generation(natural_language, schema_context)
            
            # Construct the system prompt for SQL generation
            system_prompt = self._create_system_prompt(schema_context)
            
            # Create the user message
            user_message = f"""
            Convert the following natural language description to a SQL Server SELECT query:
            
            "{natural_language}"
            
            Requirements:
            1. Generate ONLY SELECT queries - no data modification allowed
            2. Generate syntactically correct SQL Server T-SQL
            3. Use appropriate joins, indexes, and optimization techniques
            4. Include comments explaining complex logic
            5. Ensure the query is efficient and follows best practices
            6. Handle potential edge cases
            7. Use proper parameterization to prevent SQL injection
            
            Please provide the SELECT query and a brief explanation of what it does.
            """
            
            messages = [
                SystemMessage(content=system_prompt),
                UserMessage(content=user_message)
            ]
            
            # Make the API call
            response = self.client.complete(
                messages=messages,
                model=self.deployment_name,
                temperature=0.1,  # Low temperature for more deterministic output
                max_tokens=2000
            )
            
            # Extract the response content
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                
                # Parse the response to extract SQL and explanation
                sql_query, explanation = self._parse_response(content)
                
                if sql_query:
                    return {
                        'success': True,
                        'sql': sql_query,
                        'explanation': explanation,
                        'raw_response': content
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Failed to extract SQL query from response',
                        'raw_response': content
                    }
            else:
                return {
                    'success': False,
                    'error': 'No response received from Azure OpenAI'
                }
                
        except Exception as e:
            self.logger.error(f"Error generating SQL with Azure OpenAI: {str(e)}")
            return {
                'success': False,
                'error': f'Azure OpenAI service error: {str(e)}'
            }
    
    def _create_system_prompt(self, schema_context: str) -> str:
        """Create the system prompt for SQL generation"""
        
        base_prompt = """
        You are an expert SQL Server database developer and query optimizer. Your task is to convert natural language descriptions into optimized SQL Server T-SQL queries.
        
        CRITICAL SECURITY REQUIREMENT: You must ONLY generate SELECT queries. Never generate INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, TRUNCATE, or any other data modification statements. This is a read-only query system.
        
        Guidelines:
        1. Generate ONLY SELECT queries - no data modification allowed
        2. Always generate syntactically correct SQL Server T-SQL
        3. Use appropriate SQL Server specific functions and syntax
        4. Optimize queries for performance using proper indexing strategies
        5. Use CTEs, window functions, and other advanced SQL features when appropriate
        6. Always use parameterized queries or proper escaping to prevent SQL injection
        7. Include meaningful comments for complex logic
        8. Use proper naming conventions and formatting
        9. Consider query execution plans and performance implications
        10. Handle NULL values appropriately
        11. Use appropriate data types and conversions
        12. If asked for data modification, explain that only SELECT queries are permitted
        
        Response format:
        Provide your response in the following format:
        
        ```sql
        -- Your optimized SQL query here
        ```
        
        Explanation: Brief explanation of the query logic and optimization choices.
        """
        
        if schema_context:
            base_prompt += f"""
            
        Database Schema Context:
        {schema_context}
        
        Use this schema information to generate accurate queries with correct table and column names.
        """
        
        return base_prompt
    
    def _parse_response(self, content: str) -> tuple:
        """
        Parse the Azure OpenAI response to extract SQL query and explanation
        
        Args:
            content: The raw response content
            
        Returns:
            Tuple of (sql_query, explanation)
        """
        try:
            # Look for SQL code blocks
            sql_pattern = r'```sql\s*(.*?)\s*```'
            sql_matches = re.findall(sql_pattern, content, re.DOTALL | re.IGNORECASE)
            
            if sql_matches:
                sql_query = sql_matches[0].strip()
            else:
                # Fallback: look for SELECT, INSERT, UPDATE, DELETE statements
                sql_pattern = r'((?:SELECT|INSERT|UPDATE|DELETE|WITH|CREATE|ALTER|DROP).*?)(?=\n\n|\nExplanation:|\nNote:|\Z)'
                sql_matches = re.findall(sql_pattern, content, re.DOTALL | re.IGNORECASE)
                sql_query = sql_matches[0].strip() if sql_matches else ""
            
            # Extract explanation
            explanation_pattern = r'(?:Explanation|Description):\s*(.*?)(?:\n\n|\Z)'
            explanation_matches = re.findall(explanation_pattern, content, re.DOTALL | re.IGNORECASE)
            
            if explanation_matches:
                explanation = explanation_matches[0].strip()
            else:
                # Try to get text after the SQL block
                parts = content.split('```')
                if len(parts) > 2:
                    explanation = parts[2].strip()
                else:
                    explanation = "SQL query generated successfully."
            
            return sql_query, explanation
            
        except Exception as e:
            self.logger.error(f"Error parsing response: {str(e)}")
            return content, "Unable to parse response properly."
    
    def _fallback_sql_generation(self, natural_language: str, schema_context: str = "") -> Dict[str, Any]:
        """
        Fallback SQL generation when Azure OpenAI is not available
        """
        self.logger.warning("Using fallback SQL generation")
        
        # Simple keyword-based SQL generation for common patterns
        nl_lower = natural_language.lower()
        
        if 'select' in nl_lower or 'find' in nl_lower or 'get' in nl_lower or 'show' in nl_lower:
            # Basic SELECT query template
            if 'all' in nl_lower or 'everything' in nl_lower:
                sql = "SELECT * FROM [TableName];"
                explanation = "Basic SELECT query to retrieve all columns. Please replace [TableName] with the actual table name."
            else:
                sql = "SELECT [ColumnNames] FROM [TableName] WHERE [Condition];"
                explanation = "SELECT query template. Please replace placeholders with actual table and column names."
        
        elif 'insert' in nl_lower or 'add' in nl_lower or 'update' in nl_lower or 'modify' in nl_lower or 'change' in nl_lower or 'delete' in nl_lower or 'remove' in nl_lower or 'drop' in nl_lower or 'create' in nl_lower or 'truncate' in nl_lower or 'alter' in nl_lower or 'grant' in nl_lower or 'revoke' in nl_lower or 'exec' in nl_lower or 'execute' in nl_lower or 'merge' in nl_lower:
            return {
                'success': False,
                'error': 'Only SELECT queries are allowed. Data modification and administrative operations (INSERT, UPDATE, DELETE, DROP, CREATE, TRUNCATE, ALTER, MERGE, GRANT, REVOKE, EXEC) are prohibited for security.',
                'fallback': True
            }
        
        else:
            sql = "-- Unable to generate SQL from the given description\n-- Please provide more specific requirements"
            explanation = "Could not determine the type of SQL operation. Please provide a more specific description."
        
        return {
            'success': True,
            'sql': sql,
            'explanation': explanation + "\n\nNote: This is a template generated by the fallback service. Azure OpenAI integration is recommended for better results."
        }
    
    def optimize_sql(self, sql_query: str) -> Dict[str, Any]:
        """
        Optimize an existing SQL query using Azure OpenAI
        
        Args:
            sql_query: The SQL query to optimize
            
        Returns:
            Dictionary containing the optimized query and optimization suggestions
        """
        try:
            if not self.client:
                return {
                    'success': False,
                    'error': 'Azure OpenAI service not available for optimization'
                }
            
            system_prompt = """
            You are an expert SQL Server performance tuning specialist. Your task is to analyze and optimize SQL queries for better performance.
            
            Focus on:
            1. Index usage optimization
            2. Query execution plan improvements
            3. Reducing I/O operations
            4. Proper use of joins and subqueries
            5. Eliminating unnecessary operations
            6. Using appropriate SQL Server features
            
            Provide the optimized query and explain the changes made.
            """
            
            user_message = f"""
            Please analyze and optimize this SQL Server query:
            
            ```sql
            {sql_query}
            ```
            
            Provide:
            1. The optimized query
            2. Explanation of optimizations made
            3. Performance improvement recommendations
            """
            
            messages = [
                SystemMessage(content=system_prompt),
                UserMessage(content=user_message)
            ]
            
            response = self.client.complete(
                messages=messages,
                model=self.deployment_name,
                temperature=0.1,
                max_tokens=2000
            )
            
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                optimized_sql, explanation = self._parse_response(content)
                
                return {
                    'success': True,
                    'optimized_sql': optimized_sql,
                    'optimization_notes': explanation,
                    'original_sql': sql_query
                }
            else:
                return {
                    'success': False,
                    'error': 'No optimization response received'
                }
                
        except Exception as e:
            self.logger.error(f"Error optimizing SQL: {str(e)}")
            return {
                'success': False,
                'error': f'Optimization service error: {str(e)}'
            }
