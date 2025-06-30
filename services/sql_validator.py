import re
import logging
from typing import Dict, Any, List
import sqlparse
from sqlparse import sql, tokens

class SQLValidator:
    """Service for validating and optimizing SQL queries"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # SQL Server reserved keywords that should be quoted
        self.reserved_keywords = {
            'user', 'order', 'group', 'table', 'column', 'index', 'view', 'trigger',
            'procedure', 'function', 'database', 'schema', 'key', 'primary', 'foreign',
            'references', 'constraint', 'check', 'default', 'null', 'not', 'and', 'or',
            'between', 'like', 'in', 'exists', 'case', 'when', 'then', 'else', 'end'
        }
        
        # Common SQL injection patterns
        self.injection_patterns = [
            r"('|(\\'))((\s|%20)+)?((\s|%20)+)?(union|select|insert|delete|update|create|drop|exec|execute)",
            r"(union(\s|%20)+select)",
            r"(select.*from.*information_schema)",
            r"(select.*from.*sys\.)",
            r"(exec(\s|%20)+xp_)",
            r"(sp_executesql)",
            r"(;\s*(drop|delete|truncate|update|insert))",
        ]
    
    def validate_and_optimize(self, sql_query: str) -> Dict[str, Any]:
        """
        Validate and optimize a SQL query
        
        Args:
            sql_query: The SQL query to validate
            
        Returns:
            Dictionary containing validation results and optimized query
        """
        try:
            result = {
                'is_valid': False,
                'errors': [],
                'warnings': [],
                'suggestions': [],
                'optimized_sql': sql_query,
                'security_issues': []
            }
            
            if not sql_query or not sql_query.strip():
                result['errors'].append('SQL query is empty')
                return result
            
            # First check if query is read-only (SELECT only)
            if not self.is_read_only_query(sql_query):
                result['errors'].append('Only SELECT queries are allowed. UPDATE, INSERT, DELETE, DROP, and other modification statements are prohibited for security.')
                return result
            
            # Parse the SQL query
            try:
                parsed = sqlparse.parse(sql_query)
                if not parsed:
                    result['errors'].append('Unable to parse SQL query')
                    return result
                
                parsed_stmt = parsed[0]
                
            except Exception as e:
                result['errors'].append(f'SQL parsing error: {str(e)}')
                return result
            
            # Basic syntax validation
            syntax_errors = self._validate_syntax(sql_query, parsed_stmt)
            result['errors'].extend(syntax_errors)
            
            # Security validation
            security_issues = self._validate_security(sql_query)
            result['security_issues'].extend(security_issues)
            
            # Performance analysis
            performance_suggestions = self._analyze_performance(sql_query, parsed_stmt)
            result['suggestions'].extend(performance_suggestions)
            
            # SQL Server specific validations
            sqlserver_issues = self._validate_sqlserver_specifics(sql_query)
            result['warnings'].extend(sqlserver_issues)
            
            # Generate optimized SQL
            if not result['errors']:
                result['optimized_sql'] = self._optimize_query(sql_query, parsed_stmt)
                result['is_valid'] = True
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error validating SQL: {str(e)}")
            return {
                'is_valid': False,
                'errors': [f'Validation error: {str(e)}'],
                'warnings': [],
                'suggestions': [],
                'optimized_sql': sql_query,
                'security_issues': []
            }
    
    def _validate_syntax(self, sql_query: str, parsed_stmt) -> List[str]:
        """Validate basic SQL syntax"""
        errors = []
        
        try:
            # Check for balanced parentheses
            if sql_query.count('(') != sql_query.count(')'):
                errors.append('Unbalanced parentheses in query')
            
            # Check for balanced quotes
            single_quotes = sql_query.count("'")
            if single_quotes % 2 != 0:
                errors.append('Unbalanced single quotes in query')
            
            # Check for proper statement termination
            if not sql_query.strip().endswith(';'):
                # This is a warning, not an error
                pass
            
            # Check for empty statements
            if parsed_stmt.ttype is tokens.Whitespace:
                errors.append('Query contains only whitespace')
            
            # Basic keyword validation
            query_upper = sql_query.upper()
            if not any(keyword in query_upper for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'WITH']):
                errors.append('Query does not contain a recognized SQL statement type')
            
        except Exception as e:
            errors.append(f'Syntax validation error: {str(e)}')
        
        return errors
    
    def _validate_security(self, sql_query: str) -> List[str]:
        """Check for potential SQL injection vulnerabilities"""
        security_issues = []
        
        try:
            query_lower = sql_query.lower()
            
            # Check for potential injection patterns
            for pattern in self.injection_patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    security_issues.append(f'Potential SQL injection pattern detected: {pattern}')
            
            # Check for dangerous functions
            dangerous_functions = ['xp_cmdshell', 'sp_oacreate', 'sp_oamethod', 'openrowset', 'opendatasource']
            for func in dangerous_functions:
                if func in query_lower:
                    security_issues.append(f'Dangerous function detected: {func}')
            
            # Check for system table access
            if re.search(r'(sys\.|information_schema\.)', query_lower):
                security_issues.append('Access to system tables detected - ensure this is intentional')
            
            # Check for dynamic SQL construction
            if 'exec(' in query_lower or 'execute(' in query_lower:
                security_issues.append('Dynamic SQL execution detected - ensure proper parameterization')
            
        except Exception as e:
            security_issues.append(f'Security validation error: {str(e)}')
        
        return security_issues
    
    def _analyze_performance(self, sql_query: str, parsed_stmt) -> List[str]:
        """Analyze query for performance issues and suggestions"""
        suggestions = []
        
        try:
            query_lower = sql_query.lower()
            
            # Check for SELECT *
            if re.search(r'select\s+\*', query_lower):
                suggestions.append('Avoid SELECT * - specify only needed columns for better performance')
            
            # Check for missing WHERE clause in UPDATE/DELETE
            if re.search(r'(update|delete)\s+(?!.*where)', query_lower):
                suggestions.append('UPDATE/DELETE without WHERE clause detected - this will affect all rows')
            
            # Check for LIKE with leading wildcard
            if re.search(r"like\s+['\"]%", query_lower):
                suggestions.append('LIKE with leading wildcard (%) prevents index usage')
            
            # Check for functions in WHERE clause
            if re.search(r'where\s+.*\w+\s*\(.*\)\s*=', query_lower):
                suggestions.append('Functions in WHERE clause may prevent index usage')
            
            # Check for ORDER BY without LIMIT/TOP
            if 'order by' in query_lower and 'top' not in query_lower and 'limit' not in query_lower:
                suggestions.append('Consider using TOP clause with ORDER BY for better performance')
            
            # Check for nested subqueries
            subquery_count = query_lower.count('select') - 1
            if subquery_count > 2:
                suggestions.append('Consider using CTEs or JOINs instead of deeply nested subqueries')
            
            # Check for DISTINCT usage
            if 'distinct' in query_lower:
                suggestions.append('DISTINCT operation can be expensive - ensure it\'s necessary')
            
            # Check for GROUP BY without aggregate functions
            if 'group by' in query_lower and not any(func in query_lower for func in ['count(', 'sum(', 'avg(', 'max(', 'min(']):
                suggestions.append('GROUP BY without aggregate functions - consider if this is necessary')
            
        except Exception as e:
            suggestions.append(f'Performance analysis error: {str(e)}')
        
        return suggestions
    
    def _validate_sqlserver_specifics(self, sql_query: str) -> List[str]:
        """Validate SQL Server specific syntax and best practices"""
        warnings = []
        
        try:
            query_lower = sql_query.lower()
            
            # Check for deprecated features
            deprecated_features = {
                'text': 'TEXT data type is deprecated, use VARCHAR(MAX)',
                'ntext': 'NTEXT data type is deprecated, use NVARCHAR(MAX)',
                'image': 'IMAGE data type is deprecated, use VARBINARY(MAX)',
                'timestamp': 'TIMESTAMP is deprecated, use ROWVERSION'
            }
            
            for feature, message in deprecated_features.items():
                if feature in query_lower:
                    warnings.append(message)
            
            # Check for proper schema qualification
            if re.search(r'\bfrom\s+\w+\s+', query_lower) and 'dbo.' not in query_lower:
                warnings.append('Consider using schema-qualified table names (e.g., dbo.TableName)')
            
            # Check for NOLOCK hints
            if 'nolock' in query_lower:
                warnings.append('NOLOCK hint can cause dirty reads - use carefully')
            
            # Check for proper date formatting
            if re.search(r"'[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}'", sql_query):
                warnings.append('Use ISO date format (YYYY-MM-DD) for better portability')
            
        except Exception as e:
            warnings.append(f'SQL Server validation error: {str(e)}')
        
        return warnings
    
    def _optimize_query(self, sql_query: str, parsed_stmt) -> str:
        """Generate an optimized version of the SQL query"""
        try:
            # Format the query for better readability
            formatted_query = sqlparse.format(
                sql_query,
                reindent=True,
                keyword_case='upper',
                identifier_case='lower',
                strip_comments=False,
                strip_whitespace=True
            )
            
            # Add semicolon if missing
            if not formatted_query.strip().endswith(';'):
                formatted_query += ';'
            
            return formatted_query
            
        except Exception as e:
            self.logger.error(f'Error optimizing query: {str(e)}')
            return sql_query
    
    def is_read_only_query(self, sql_query: str) -> bool:
        """Check if the query is read-only (SELECT only)"""
        try:
            query_upper = sql_query.upper().strip()
            
            # Remove comments and whitespace
            cleaned_query = re.sub(r'--.*?\n', '', query_upper)
            cleaned_query = re.sub(r'/\*.*?\*/', '', cleaned_query, flags=re.DOTALL)
            cleaned_query = cleaned_query.strip()
            
            # Check if it starts with SELECT or WITH (for CTEs)
            return cleaned_query.startswith('SELECT') or cleaned_query.startswith('WITH')
            
        except Exception:
            return False
    
    def extract_table_names(self, sql_query: str) -> List[str]:
        """Extract table names from the SQL query"""
        try:
            parsed = sqlparse.parse(sql_query)
            tables = []
            
            for statement in parsed:
                tables.extend(self._extract_tables_from_statement(statement))
            
            return list(set(tables))  # Remove duplicates
            
        except Exception as e:
            self.logger.error(f'Error extracting table names: {str(e)}')
            return []
    
    def _extract_tables_from_statement(self, statement) -> List[str]:
        """Extract table names from a parsed SQL statement"""
        tables = []
        
        try:
            # This is a simplified extraction - could be enhanced
            tokens = list(statement.flatten())
            
            for i, token in enumerate(tokens):
                if token.ttype is tokens.Keyword and token.value.upper() in ('FROM', 'JOIN', 'UPDATE', 'INTO'):
                    # Look for the next identifier
                    for j in range(i + 1, len(tokens)):
                        next_token = tokens[j]
                        if next_token.ttype is None and not next_token.is_whitespace:
                            table_name = next_token.value.strip('[]`"')
                            if '.' in table_name:
                                table_name = table_name.split('.')[-1]  # Get table name without schema
                            tables.append(table_name)
                            break
        except Exception as e:
            self.logger.error(f'Error extracting tables from statement: {str(e)}')
        
        return tables
