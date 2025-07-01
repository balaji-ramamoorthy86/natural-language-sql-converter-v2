"""
Query Feedback Service
Implements feedback loop to check correctness and efficiency of Azure OpenAI generated queries
"""

import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import re

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False
    pyodbc = None

class QueryFeedbackService:
    """Service for analyzing and providing feedback on generated SQL queries"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.feedback_history = []  # In-memory storage for feedback
        
    def analyze_query_quality(self, sql_query: str, schema_context: str = "", 
                            natural_language: str = "", connection_info: Dict = None) -> Dict[str, Any]:
        """
        Comprehensive analysis of generated SQL query quality
        
        Args:
            sql_query: The generated SQL query
            schema_context: Database schema information
            natural_language: Original natural language request
            connection_info: Database connection for execution testing
            
        Returns:
            Dictionary containing feedback analysis
        """
        feedback = {
            'query': sql_query,
            'natural_language': natural_language,
            'timestamp': datetime.now().isoformat(),
            'analysis': {
                'syntax_score': 0,
                'semantic_score': 0,
                'performance_score': 0,
                'security_score': 0,
                'overall_score': 0
            },
            'feedback': {
                'syntax_issues': [],
                'semantic_issues': [],
                'performance_suggestions': [],
                'security_warnings': [],
                'correctness_issues': []
            },
            'execution_results': {},
            'recommendations': []
        }
        
        try:
            # 1. Syntax Analysis
            syntax_analysis = self._analyze_syntax(sql_query)
            feedback['analysis']['syntax_score'] = syntax_analysis['score']
            feedback['feedback']['syntax_issues'] = syntax_analysis['issues']
            
            # 2. Semantic Analysis (intent matching)
            semantic_analysis = self._analyze_semantic_alignment(sql_query, natural_language, schema_context)
            feedback['analysis']['semantic_score'] = semantic_analysis['score']
            feedback['feedback']['semantic_issues'] = semantic_analysis['issues']
            
            # 3. Performance Analysis
            performance_analysis = self._analyze_performance(sql_query)
            feedback['analysis']['performance_score'] = performance_analysis['score']
            feedback['feedback']['performance_suggestions'] = performance_analysis['suggestions']
            
            # 4. Security Analysis
            security_analysis = self._analyze_security(sql_query)
            feedback['analysis']['security_score'] = security_analysis['score']
            feedback['feedback']['security_warnings'] = security_analysis['warnings']
            
            # 5. Execution Testing (if connection provided)
            if connection_info:
                execution_results = self._test_query_execution(sql_query, connection_info)
                feedback['execution_results'] = execution_results
                
                # Adjust scores based on execution results
                if execution_results.get('success'):
                    feedback['analysis']['syntax_score'] = min(100, feedback['analysis']['syntax_score'] + 20)
                else:
                    feedback['analysis']['syntax_score'] = max(0, feedback['analysis']['syntax_score'] - 30)
                    feedback['feedback']['correctness_issues'].append(
                        f"Query execution failed: {execution_results.get('error', 'Unknown error')}"
                    )
            
            # 6. Calculate overall score
            scores = feedback['analysis']
            feedback['analysis']['overall_score'] = (
                scores['syntax_score'] * 0.3 +
                scores['semantic_score'] * 0.3 +
                scores['performance_score'] * 0.2 +
                scores['security_score'] * 0.2
            )
            
            # 7. Generate recommendations
            feedback['recommendations'] = self._generate_recommendations(feedback)
            
            # Store feedback for learning
            self.feedback_history.append(feedback)
            
            return feedback
            
        except Exception as e:
            self.logger.error(f"Error analyzing query quality: {str(e)}")
            feedback['error'] = str(e)
            return feedback
    
    def _analyze_syntax(self, sql_query: str) -> Dict[str, Any]:
        """Analyze SQL syntax correctness and best practices"""
        score = 100
        issues = []
        
        try:
            # Basic syntax checks
            query_upper = sql_query.upper().strip()
            
            # Check for basic SQL structure
            if not any(keyword in query_upper for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']):
                score -= 50
                issues.append("No valid SQL statement detected")
            
            # Check for proper formatting
            if sql_query.count('(') != sql_query.count(')'):
                score -= 20
                issues.append("Unmatched parentheses")
            
            # Check for SQL injection patterns
            injection_patterns = [
                r"';.*--",
                r"UNION.*SELECT",
                r"DROP\s+TABLE",
                r"DELETE\s+FROM.*WHERE\s+1\s*=\s*1"
            ]
            
            for pattern in injection_patterns:
                if re.search(pattern, query_upper):
                    score -= 30
                    issues.append(f"Potential SQL injection pattern detected: {pattern}")
            
            # Check for best practices
            if 'SELECT *' in query_upper:
                score -= 10
                issues.append("Consider specifying column names instead of SELECT *")
            
            if not re.search(r'WHERE|JOIN|GROUP BY|ORDER BY', query_upper):
                score -= 5
                issues.append("Query might benefit from filtering or sorting clauses")
            
        except Exception as e:
            score = 0
            issues.append(f"Syntax analysis error: {str(e)}")
        
        return {
            'score': max(0, score),
            'issues': issues
        }
    
    def _analyze_semantic_alignment(self, sql_query: str, natural_language: str, schema_context: str) -> Dict[str, Any]:
        """Analyze how well the SQL query matches the natural language intent"""
        score = 70  # Base score
        issues = []
        
        try:
            if not natural_language:
                return {'score': score, 'issues': ['No natural language context provided']}
            
            nl_lower = natural_language.lower()
            sql_upper = sql_query.upper()
            
            # Intent mapping analysis
            intent_keywords = {
                'retrieve': ['SELECT', 'SHOW'],
                'count': ['COUNT', 'SUM'],
                'filter': ['WHERE', 'HAVING'],
                'sort': ['ORDER BY'],
                'group': ['GROUP BY'],
                'join': ['JOIN', 'INNER JOIN', 'LEFT JOIN'],
                'aggregate': ['SUM', 'AVG', 'COUNT', 'MAX', 'MIN'],
                'recent': ['ORDER BY.*DESC', 'TOP', 'LIMIT'],
                'total': ['SUM', 'COUNT'],
                'average': ['AVG'],
                'maximum': ['MAX'],
                'minimum': ['MIN']
            }
            
            # Check intent alignment
            for intent, keywords in intent_keywords.items():
                if intent in nl_lower:
                    if not any(keyword in sql_upper for keyword in keywords):
                        score -= 15
                        issues.append(f"Natural language suggests '{intent}' but SQL query doesn't reflect this")
                    else:
                        score += 5
            
            # Check for table/column name alignment with schema
            if schema_context:
                schema_lower = schema_context.lower()
                # Extract table names mentioned in natural language
                potential_tables = re.findall(r'\b\w+\b', nl_lower)
                for table in potential_tables:
                    if table in schema_lower and table.upper() not in sql_upper:
                        score -= 10
                        issues.append(f"Mentioned table '{table}' not found in query")
            
            # Time-based query checks
            time_indicators = ['today', 'yesterday', 'last week', 'this month', 'recent']
            if any(indicator in nl_lower for indicator in time_indicators):
                if not re.search(r'DATE|GETDATE|NOW\(\)|CURDATE', sql_upper):
                    score -= 20
                    issues.append("Natural language mentions time constraints but query lacks date filtering")
            
        except Exception as e:
            score = 50
            issues.append(f"Semantic analysis error: {str(e)}")
        
        return {
            'score': max(0, min(100, score)),
            'issues': issues
        }
    
    def _analyze_performance(self, sql_query: str) -> Dict[str, Any]:
        """Analyze query performance characteristics"""
        score = 80  # Base score
        suggestions = []
        
        try:
            query_upper = sql_query.upper()
            
            # Performance anti-patterns
            if 'SELECT *' in query_upper:
                score -= 15
                suggestions.append("Replace SELECT * with specific column names to improve performance")
            
            if re.search(r'WHERE.*LIKE\s+[\'"]%.*%[\'"]', query_upper):
                score -= 20
                suggestions.append("Leading wildcard in LIKE clause can prevent index usage")
            
            if 'ORDER BY' in query_upper and 'LIMIT' not in query_upper and 'TOP' not in query_upper:
                score -= 10
                suggestions.append("Consider adding LIMIT/TOP clause when ordering results")
            
            # Check for subqueries that could be JOINs
            subquery_count = query_upper.count('SELECT') - 1
            if subquery_count > 2:
                score -= 15
                suggestions.append("Multiple subqueries detected - consider using JOINs for better performance")
            
            # Check for missing WHERE clauses on large operations
            if any(op in query_upper for op in ['UPDATE', 'DELETE']) and 'WHERE' not in query_upper:
                score -= 30
                suggestions.append("UPDATE/DELETE without WHERE clause can affect performance and data integrity")
            
            # Check for DISTINCT usage
            if 'DISTINCT' in query_upper:
                score -= 5
                suggestions.append("DISTINCT can be expensive - ensure it's necessary")
            
            # Positive patterns
            if 'INDEX' in query_upper or 'INDEXED' in query_upper:
                score += 10
                suggestions.append("Good: Query appears to consider indexing")
            
            if re.search(r'LIMIT|TOP\s+\d+', query_upper):
                score += 10
                suggestions.append("Good: Query limits result set size")
            
        except Exception as e:
            score = 50
            suggestions.append(f"Performance analysis error: {str(e)}")
        
        return {
            'score': max(0, min(100, score)),
            'suggestions': suggestions
        }
    
    def _analyze_security(self, sql_query: str) -> Dict[str, Any]:
        """Analyze query for security issues"""
        score = 100
        warnings = []
        
        try:
            query_upper = sql_query.upper()
            
            # SQL injection patterns
            injection_patterns = [
                (r"';.*--", "Potential SQL injection with comment termination"),
                (r"UNION.*SELECT", "UNION-based injection pattern"),
                (r"DROP\s+TABLE", "Dangerous DROP statement"),
                (r"EXEC\s*\(", "Dynamic SQL execution detected"),
                (r"SHUTDOWN", "System shutdown command"),
                (r"xp_cmdshell", "Command shell execution"),
                (r"sp_configure", "System configuration access")
            ]
            
            for pattern, warning in injection_patterns:
                if re.search(pattern, query_upper):
                    score -= 30
                    warnings.append(warning)
            
            # Check for hardcoded credentials
            if re.search(r"PASSWORD\s*=|PWD\s*=", query_upper):
                score -= 40
                warnings.append("Hardcoded credentials detected")
            
            # Check for overly permissive queries
            if re.search(r"WHERE\s+1\s*=\s*1", query_upper):
                score -= 20
                warnings.append("Overly permissive WHERE clause (1=1)")
            
            # Positive security practices
            if re.search(r"WHERE.*=\s*[@?]", sql_query):
                score += 10
                warnings.append("Good: Parameterized query detected")
            
        except Exception as e:
            score = 50
            warnings.append(f"Security analysis error: {str(e)}")
        
        return {
            'score': max(0, score),
            'warnings': warnings
        }
    
    def _test_query_execution(self, sql_query: str, connection_info: Dict) -> Dict[str, Any]:
        """Test query execution if database connection is available"""
        if not PYODBC_AVAILABLE or not connection_info:
            return {'success': False, 'error': 'Database connection not available'}
        
        try:
            # Build connection string
            auth_type = connection_info.get('auth_type', 'sql')
            server = connection_info.get('host', 'localhost')
            port = connection_info.get('port', '1433')
            database = connection_info.get('database', 'master')
            
            if auth_type == 'windows':
                conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server},{port};DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes;Encrypt=yes"
            else:
                username = connection_info.get('username', '')
                password = connection_info.get('password', '')
                conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server},{port};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;Encrypt=yes"
            
            start_time = time.time()
            
            with pyodbc.connect(conn_str, timeout=30) as conn:
                cursor = conn.cursor()
                
                # For safety, only execute SELECT queries
                if not sql_query.strip().upper().startswith('SELECT'):
                    return {
                        'success': False,
                        'error': 'Only SELECT queries are executed for safety',
                        'execution_time': 0
                    }
                
                # Execute with limit for safety
                limited_query = sql_query
                if 'LIMIT' not in sql_query.upper() and 'TOP' not in sql_query.upper():
                    # Add TOP clause for SQL Server
                    limited_query = sql_query.replace('SELECT', 'SELECT TOP 100', 1)
                
                cursor.execute(limited_query)
                rows = cursor.fetchall()
                
                execution_time = time.time() - start_time
                
                return {
                    'success': True,
                    'execution_time': round(execution_time, 3),
                    'row_count': len(rows),
                    'columns': [desc[0] for desc in cursor.description] if cursor.description else [],
                    'sample_data': [list(row) for row in rows[:5]]  # First 5 rows as sample
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'execution_time': 0
            }
    
    def _generate_recommendations(self, feedback: Dict) -> List[str]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []
        
        try:
            overall_score = feedback['analysis']['overall_score']
            
            if overall_score >= 90:
                recommendations.append("Excellent query! This SQL appears to be well-structured and efficient.")
            elif overall_score >= 70:
                recommendations.append("Good query with room for minor improvements.")
            elif overall_score >= 50:
                recommendations.append("Query needs attention in several areas for optimal performance.")
            else:
                recommendations.append("Query requires significant improvements before production use.")
            
            # Specific recommendations based on analysis
            if feedback['analysis']['syntax_score'] < 70:
                recommendations.append("Review SQL syntax and fix any structural issues.")
            
            if feedback['analysis']['semantic_score'] < 70:
                recommendations.append("Ensure the query accurately reflects the natural language intent.")
            
            if feedback['analysis']['performance_score'] < 70:
                recommendations.append("Consider performance optimizations like indexing and query restructuring.")
            
            if feedback['analysis']['security_score'] < 80:
                recommendations.append("Address security concerns before using this query in production.")
            
            # Execution-based recommendations
            if feedback['execution_results'].get('success'):
                exec_time = feedback['execution_results'].get('execution_time', 0)
                if exec_time > 5:
                    recommendations.append("Query execution time is high - consider optimization.")
                elif exec_time < 0.1:
                    recommendations.append("Good: Query executes efficiently.")
            
        except Exception as e:
            recommendations.append(f"Error generating recommendations: {str(e)}")
        
        return recommendations
    
    def get_feedback_summary(self, limit: int = 10) -> Dict[str, Any]:
        """Get summary of recent feedback for learning and improvement"""
        recent_feedback = self.feedback_history[-limit:] if self.feedback_history else []
        
        if not recent_feedback:
            return {'message': 'No feedback data available'}
        
        # Calculate average scores
        avg_scores = {
            'syntax': sum(f['analysis']['syntax_score'] for f in recent_feedback) / len(recent_feedback),
            'semantic': sum(f['analysis']['semantic_score'] for f in recent_feedback) / len(recent_feedback),
            'performance': sum(f['analysis']['performance_score'] for f in recent_feedback) / len(recent_feedback),
            'security': sum(f['analysis']['security_score'] for f in recent_feedback) / len(recent_feedback),
            'overall': sum(f['analysis']['overall_score'] for f in recent_feedback) / len(recent_feedback)
        }
        
        # Common issues
        all_issues = []
        for feedback in recent_feedback:
            all_issues.extend(feedback['feedback']['syntax_issues'])
            all_issues.extend(feedback['feedback']['semantic_issues'])
            all_issues.extend(feedback['feedback']['performance_suggestions'])
            all_issues.extend(feedback['feedback']['security_warnings'])
        
        # Count issue frequency
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        common_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'total_queries_analyzed': len(recent_feedback),
            'average_scores': avg_scores,
            'common_issues': common_issues,
            'recent_feedback': recent_feedback
        }
    
    def submit_user_feedback(self, query_id: str, user_rating: int, user_comments: str = "") -> bool:
        """Allow users to provide feedback on query quality"""
        try:
            # Find the feedback entry
            for feedback in self.feedback_history:
                if feedback.get('id') == query_id:
                    feedback['user_feedback'] = {
                        'rating': user_rating,
                        'comments': user_comments,
                        'timestamp': datetime.now().isoformat()
                    }
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Error submitting user feedback: {str(e)}")
            return False