"""
AI-Powered Schema Analyzer Service
Analyzes database schemas with cryptic names and generates meaningful descriptions
"""

import logging
import os
from typing import Dict, List, Any, Optional

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False
    pyodbc = None

# PostgreSQL support removed - using in-memory storage instead
PSYCOPG2_AVAILABLE = False
psycopg2 = None
RealDictCursor = None
import json
import re
from collections import Counter

class SchemaAnalyzer:
    """Service for analyzing database schemas and generating AI descriptions"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def analyze_database(self, connection_info: Dict[str, str]) -> Dict[str, Any]:
        """
        Analyze a database and generate AI descriptions for tables and columns
        
        Args:
            connection_info: Database connection parameters
            
        Returns:
            Dictionary containing analysis results and suggested descriptions
        """
        try:
            # Connect to database
            conn = self._connect_to_database(connection_info)
            if not conn:
                return {
                    'success': False,
                    'error': 'Failed to connect to database'
                }
            
            # Get schema information
            schema_info = self._extract_schema_information(conn, connection_info.get('database_type', 'postgresql'))
            
            # Analyze patterns in the data
            analysis = self._analyze_schema_patterns(schema_info)
            
            # Generate AI descriptions
            descriptions = self._generate_ai_descriptions(schema_info, analysis)
            
            conn.close()
            
            return {
                'success': True,
                'analysis': analysis,
                'descriptions': descriptions,
                'schema_info': schema_info
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing database: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _connect_to_database(self, connection_info: Dict[str, str]):
        """Connect to database based on connection info"""
        db_type = connection_info.get('database_type', 'postgresql').lower()
        
        try:
            if db_type == 'sqlserver':
                if not PYODBC_AVAILABLE or pyodbc is None:
                    raise ImportError("pyodbc is not available. Please install it to connect to SQL Server.")
                
                # Build connection string with support for different authentication types
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
                
                return pyodbc.connect(conn_str)
            else:
                raise ValueError(f"Unsupported database type: {db_type}. Only SQL Server is supported.")
                
        except Exception as e:
            self.logger.error(f"Database connection failed: {str(e)}")
            return None
    
    def _extract_schema_information(self, conn, db_type: str) -> Dict[str, Any]:
        """Extract comprehensive schema information from database"""
        schema_info = {
            'tables': {},
            'relationships': [],
            'indexes': {},
            'constraints': {}
        }
        
        try:
            if db_type == 'postgresql':
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                # Get table and column information
                cursor.execute("""
                    SELECT 
                        t.table_name,
                        c.column_name,
                        c.data_type,
                        c.is_nullable,
                        c.column_default,
                        c.character_maximum_length,
                        c.numeric_precision,
                        c.numeric_scale,
                        tc.constraint_type,
                        kcu.constraint_name
                    FROM information_schema.tables t
                    LEFT JOIN information_schema.columns c ON t.table_name = c.table_name
                    LEFT JOIN information_schema.table_constraints tc ON t.table_name = tc.table_name
                    LEFT JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
                    WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
                    ORDER BY t.table_name, c.ordinal_position
                """)
                
                # Process results
                for row in cursor.fetchall():
                    table_name = row['table_name']
                    if table_name not in schema_info['tables']:
                        schema_info['tables'][table_name] = {
                            'columns': [],
                            'row_count': 0,
                            'sample_data': {}
                        }
                    
                    if row['column_name']:
                        column_info = {
                            'name': row['column_name'],
                            'type': row['data_type'],
                            'nullable': row['is_nullable'] == 'YES',
                            'default': row['column_default'],
                            'max_length': row['character_maximum_length'],
                            'precision': row['numeric_precision'],
                            'scale': row['numeric_scale'],
                            'is_primary_key': row['constraint_type'] == 'PRIMARY KEY',
                            'is_foreign_key': row['constraint_type'] == 'FOREIGN KEY'
                        }
                        schema_info['tables'][table_name]['columns'].append(column_info)
                
                # Get foreign key relationships
                cursor.execute("""
                    SELECT
                        tc.table_name,
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                """)
                
                for row in cursor.fetchall():
                    schema_info['relationships'].append({
                        'from_table': row['table_name'],
                        'from_column': row['column_name'],
                        'to_table': row['foreign_table_name'],
                        'to_column': row['foreign_column_name']
                    })
                
                # Get sample data and row counts for analysis
                for table_name in schema_info['tables']:
                    try:
                        # Validate table name to prevent SQL injection
                        if not self._is_valid_identifier(table_name):
                            self.logger.warning(f"Invalid table name detected: {table_name}")
                            continue
                            
                        # Get row count using INFORMATION_SCHEMA (safer approach)
                        if db_type == 'mysql':
                            cursor.execute("""
                                SELECT table_rows 
                                FROM INFORMATION_SCHEMA.TABLES 
                                WHERE table_schema = DATABASE() AND table_name = %s
                            """, (table_name,))
                        elif db_type == 'postgresql':
                            cursor.execute("""
                                SELECT n_tup_ins - n_tup_del as row_count
                                FROM pg_stat_user_tables 
                                WHERE relname = %s
                            """, (table_name,))
                        elif db_type == 'sqlserver':
                            cursor.execute("""
                                SELECT SUM(row_count) as row_count
                                FROM sys.dm_db_partition_stats 
                                WHERE object_id = OBJECT_ID(?)
                            """, (table_name,))
                        else:
                            # Fallback for other databases
                            cursor.execute("SELECT COUNT(*) FROM " + self._quote_identifier(table_name))
                            
                        count_result = cursor.fetchone()
                        schema_info['tables'][table_name]['row_count'] = count_result[0] if count_result else 0
                        
                        # Get sample data using quoted identifier for safety
                        quoted_table = self._quote_identifier(table_name)
                        cursor.execute(f"SELECT * FROM {quoted_table} LIMIT 5")
                        sample_rows = cursor.fetchall()
                        schema_info['tables'][table_name]['sample_data'] = [dict(row) for row in sample_rows]
                        
                    except Exception as e:
                        self.logger.warning(f"Could not get sample data for {table_name}: {str(e)}")
                        schema_info['tables'][table_name]['sample_data'] = []
                
                cursor.close()
                
        except Exception as e:
            self.logger.error(f"Error extracting schema information: {str(e)}")
        
        return schema_info
    
    def _analyze_schema_patterns(self, schema_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze patterns in the schema to understand table purposes"""
        analysis = {
            'table_patterns': {},
            'column_patterns': {},
            'naming_conventions': {},
            'data_patterns': {},
            'relationship_patterns': {}
        }
        
        # Analyze table naming patterns
        table_names = list(schema_info['tables'].keys())
        analysis['naming_conventions'] = {
            'common_prefixes': self._find_common_prefixes(table_names),
            'common_suffixes': self._find_common_suffixes(table_names),
            'naming_style': self._detect_naming_style(table_names)
        }
        
        # Analyze column patterns
        all_columns = []
        for table_name, table_info in schema_info['tables'].items():
            for column in table_info['columns']:
                all_columns.append(column['name'])
        
        analysis['column_patterns'] = {
            'common_column_names': Counter(all_columns).most_common(20),
            'id_patterns': [col for col in all_columns if 'id' in col.lower()],
            'date_patterns': [col for col in all_columns if any(term in col.lower() for term in ['date', 'time', 'created', 'updated', 'modified'])],
            'name_patterns': [col for col in all_columns if any(term in col.lower() for term in ['name', 'title', 'description'])]
        }
        
        # Analyze each table
        for table_name, table_info in schema_info['tables'].items():
            table_analysis = self._analyze_single_table(table_name, table_info, schema_info)
            analysis['table_patterns'][table_name] = table_analysis
        
        return analysis
    
    def _analyze_single_table(self, table_name: str, table_info: Dict[str, Any], schema_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single table to determine its purpose"""
        analysis = {
            'likely_purpose': 'unknown',
            'confidence': 0.0,
            'evidence': [],
            'column_analysis': {}
        }
        
        columns = table_info['columns']
        column_names = [col['name'].lower() for col in columns]
        sample_data = table_info.get('sample_data', [])
        
        # Analyze column names for clues
        purpose_indicators = {
            'user': ['user', 'customer', 'person', 'account', 'profile', 'member'],
            'product': ['product', 'item', 'goods', 'catalog', 'inventory'],
            'order': ['order', 'purchase', 'transaction', 'sale', 'payment'],
            'log': ['log', 'audit', 'history', 'event', 'activity'],
            'configuration': ['config', 'setting', 'preference', 'option'],
            'lookup': ['lookup', 'reference', 'code', 'type', 'category'],
            'relationship': ['mapping', 'link', 'junction', 'bridge', 'cross']
        }
        
        # Score each potential purpose
        purpose_scores = {}
        for purpose, indicators in purpose_indicators.items():
            score = 0
            evidence = []
            
            # Check table name
            for indicator in indicators:
                if indicator in table_name.lower():
                    score += 3
                    evidence.append(f"Table name contains '{indicator}'")
            
            # Check column names
            for indicator in indicators:
                matching_columns = [col for col in column_names if indicator in col]
                if matching_columns:
                    score += len(matching_columns)
                    evidence.append(f"Columns contain '{indicator}': {matching_columns}")
            
            # Check for common patterns
            if purpose == 'user' and any(col in column_names for col in ['email', 'username', 'password', 'first_name', 'last_name']):
                score += 5
                evidence.append("Contains typical user fields")
            
            if purpose == 'order' and any(col in column_names for col in ['total', 'amount', 'price', 'quantity']):
                score += 5
                evidence.append("Contains typical order/transaction fields")
            
            if purpose == 'log' and any(col in column_names for col in ['timestamp', 'created_at', 'logged_at']):
                score += 3
                evidence.append("Contains timestamp fields typical of logs")
            
            purpose_scores[purpose] = {'score': score, 'evidence': evidence}
        
        # Determine most likely purpose
        if purpose_scores:
            best_purpose = max(purpose_scores.items(), key=lambda x: x[1]['score'])
            if best_purpose[1]['score'] > 0:
                analysis['likely_purpose'] = best_purpose[0]
                analysis['confidence'] = min(best_purpose[1]['score'] / 10.0, 1.0)
                analysis['evidence'] = best_purpose[1]['evidence']
        
        # Analyze individual columns
        for column in columns:
            col_analysis = self._analyze_column(column, sample_data)
            analysis['column_analysis'][column['name']] = col_analysis
        
        return analysis
    
    def _analyze_column(self, column: Dict[str, Any], sample_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze a single column to understand its purpose"""
        analysis = {
            'likely_purpose': 'unknown',
            'data_patterns': [],
            'suggested_description': ''
        }
        
        col_name = column['name'].lower()
        col_type = column['type'].lower()
        
        # Analyze column name patterns
        if 'id' in col_name:
            analysis['likely_purpose'] = 'identifier'
        elif any(term in col_name for term in ['name', 'title']):
            analysis['likely_purpose'] = 'name/title'
        elif any(term in col_name for term in ['email', 'mail']):
            analysis['likely_purpose'] = 'email'
        elif any(term in col_name for term in ['phone', 'mobile', 'tel']):
            analysis['likely_purpose'] = 'phone'
        elif any(term in col_name for term in ['date', 'time', 'created', 'updated']):
            analysis['likely_purpose'] = 'datetime'
        elif any(term in col_name for term in ['price', 'amount', 'cost', 'total']):
            analysis['likely_purpose'] = 'monetary'
        elif any(term in col_name for term in ['status', 'state', 'flag']):
            analysis['likely_purpose'] = 'status'
        elif any(term in col_name for term in ['description', 'comment', 'note']):
            analysis['likely_purpose'] = 'description'
        
        # Analyze data type
        if 'varchar' in col_type or 'text' in col_type:
            analysis['data_patterns'].append('text_field')
        elif 'int' in col_type or 'bigint' in col_type:
            analysis['data_patterns'].append('integer_field')
        elif 'decimal' in col_type or 'numeric' in col_type:
            analysis['data_patterns'].append('decimal_field')
        elif 'timestamp' in col_type or 'datetime' in col_type:
            analysis['data_patterns'].append('datetime_field')
        elif 'boolean' in col_type or 'bit' in col_type:
            analysis['data_patterns'].append('boolean_field')
        
        # Analyze sample data patterns
        if sample_data:
            sample_values = [row.get(column['name']) for row in sample_data if row.get(column['name']) is not None]
            if sample_values:
                # Check for email patterns
                if any('@' in str(val) for val in sample_values):
                    analysis['data_patterns'].append('email_pattern')
                
                # Check for phone patterns
                if any(re.match(r'[\d\-\+\(\)\s]+', str(val)) and len(str(val)) > 7 for val in sample_values):
                    analysis['data_patterns'].append('phone_pattern')
                
                # Check for URL patterns
                if any(str(val).startswith(('http://', 'https://')) for val in sample_values):
                    analysis['data_patterns'].append('url_pattern')
        
        # Generate suggested description
        analysis['suggested_description'] = self._generate_column_description(column['name'], analysis)
        
        return analysis
    
    def _generate_column_description(self, column_name: str, analysis: Dict[str, Any]) -> str:
        """Generate a description for a column based on analysis"""
        purpose = analysis['likely_purpose']
        
        # Basic descriptions based on purpose
        descriptions = {
            'identifier': f"Unique identifier for {column_name}",
            'name/title': f"Name or title field",
            'email': "Email address",
            'phone': "Phone number",
            'datetime': "Date and time field",
            'monetary': "Monetary amount or price",
            'status': "Status or state indicator",
            'description': "Descriptive text field"
        }
        
        base_description = descriptions.get(purpose, f"Data field: {column_name}")
        
        # Add data pattern information
        if 'email_pattern' in analysis['data_patterns']:
            base_description += " (contains email addresses)"
        elif 'phone_pattern' in analysis['data_patterns']:
            base_description += " (contains phone numbers)"
        elif 'url_pattern' in analysis['data_patterns']:
            base_description += " (contains URLs)"
        
        return base_description
    
    def _generate_ai_descriptions(self, schema_info: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI-powered descriptions for tables and columns"""
        descriptions = {
            'tables': {},
            'columns': {}
        }
        
        # Generate table descriptions
        for table_name, table_analysis in analysis['table_patterns'].items():
            purpose = table_analysis['likely_purpose']
            confidence = table_analysis['confidence']
            evidence = table_analysis['evidence']
            
            if purpose != 'unknown' and confidence > 0.3:
                description = self._generate_table_description(table_name, purpose, evidence, schema_info['tables'][table_name])
            else:
                description = self._generate_fallback_table_description(table_name, schema_info['tables'][table_name])
            
            descriptions['tables'][table_name] = {
                'description': description,
                'confidence': confidence,
                'purpose': purpose,
                'evidence': evidence
            }
        
        # Generate column descriptions
        for table_name, table_analysis in analysis['table_patterns'].items():
            descriptions['columns'][table_name] = {}
            for column_name, column_analysis in table_analysis['column_analysis'].items():
                descriptions['columns'][table_name][column_name] = column_analysis['suggested_description']
        
        return descriptions
    
    def _generate_table_description(self, table_name: str, purpose: str, evidence: List[str], table_info: Dict[str, Any]) -> str:
        """Generate a description for a table based on its analyzed purpose"""
        row_count = table_info.get('row_count', 0)
        column_count = len(table_info.get('columns', []))
        
        purpose_descriptions = {
            'user': f"User/customer information table storing user profiles and account details",
            'product': f"Product catalog table containing product information and details",
            'order': f"Order/transaction table storing purchase and sales information",
            'log': f"Log/audit table recording system events and activities",
            'configuration': f"Configuration table storing system settings and preferences",
            'lookup': f"Lookup/reference table containing code values and categories",
            'relationship': f"Junction/mapping table managing relationships between entities"
        }
        
        base_description = purpose_descriptions.get(purpose, f"Data table: {table_name}")
        
        # Add metadata
        metadata = f" (Table: {table_name}, {column_count} columns, ~{row_count:,} rows)"
        
        return base_description + metadata
    
    def _generate_fallback_table_description(self, table_name: str, table_info: Dict[str, Any]) -> str:
        """Generate a fallback description when purpose cannot be determined"""
        row_count = table_info.get('row_count', 0)
        column_count = len(table_info.get('columns', []))
        
        # Look at column names for clues
        columns = [col['name'] for col in table_info.get('columns', [])]
        key_columns = [col for col in columns if any(term in col.lower() for term in ['id', 'key', 'code'])]
        
        description = f"Data table '{table_name}'"
        
        if key_columns:
            description += f" with key fields: {', '.join(key_columns[:3])}"
        
        description += f" ({column_count} columns, ~{row_count:,} rows)"
        
        return description
    
    def _find_common_prefixes(self, names: List[str]) -> List[str]:
        """Find common prefixes in table names"""
        if not names:
            return []
        
        prefixes = []
        for name in names:
            parts = name.split('_')
            if len(parts) > 1:
                prefixes.append(parts[0])
        
        return [prefix for prefix, count in Counter(prefixes).most_common(5) if count > 1]
    
    def _find_common_suffixes(self, names: List[str]) -> List[str]:
        """Find common suffixes in table names"""
        if not names:
            return []
        
        suffixes = []
        for name in names:
            parts = name.split('_')
            if len(parts) > 1:
                suffixes.append(parts[-1])
        
        return [suffix for suffix, count in Counter(suffixes).most_common(5) if count > 1]
    
    def _detect_naming_style(self, names: List[str]) -> str:
        """Detect the naming convention used"""
        if not names:
            return 'unknown'
        
        snake_case_count = sum(1 for name in names if '_' in name)
        camel_case_count = sum(1 for name in names if any(c.isupper() for c in name[1:]))
        
        if snake_case_count > len(names) * 0.7:
            return 'snake_case'
        elif camel_case_count > len(names) * 0.7:
            return 'camelCase'
        else:
            return 'mixed'
    
    def _is_valid_identifier(self, name: str) -> bool:
        """Validate that a name is a safe SQL identifier"""
        if not name:
            return False
        
        # Check for basic SQL injection patterns
        if any(char in name for char in [';', '--', '/*', '*/', "'", '"', '\\', '\n', '\r']):
            return False
        
        # Check for SQL keywords that shouldn't be table names
        sql_keywords = {'drop', 'delete', 'insert', 'update', 'create', 'alter', 'exec', 'execute'}
        if name.lower() in sql_keywords:
            return False
        
        # Must start with letter or underscore, contain only alphanumeric and underscores
        import re
        return re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name) is not None
    
    def _quote_identifier(self, identifier: str) -> str:
        """Safely quote a SQL identifier based on database type"""
        if not self._is_valid_identifier(identifier):
            raise ValueError(f"Invalid identifier: {identifier}")
        
        # Use square brackets for SQL Server, backticks for MySQL, double quotes for PostgreSQL
        return f'[{identifier}]'  # Default to SQL Server style