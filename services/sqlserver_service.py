"""
On-Premises SQL Server Service
Handles connections and operations for on-premises SQL Server instances
"""

import os
import logging

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False
    pyodbc = None
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

class SQLServerService:
    """Service for managing on-premises SQL Server connections and operations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.connection_cache = {}
        self.schema_cache = {}
        
    def test_connection(self, connection_params: Dict[str, str]) -> Dict[str, Any]:
        """Test connection to SQL Server instance"""
        try:
            conn_string = self._build_connection_string(connection_params)
            
            with pyodbc.connect(conn_string, timeout=10) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT @@VERSION, @@SERVERNAME, DB_NAME()")
                result = cursor.fetchone()
                
                return {
                    'success': True,
                    'server_info': {
                        'version': result[0].split('\n')[0] if result and result[0] else 'Unknown',
                        'server_name': result[1] if result and len(result) > 1 else 'Unknown',
                        'database': result[2] if result and len(result) > 2 else 'Unknown'
                    },
                    'message': 'Connection successful'
                }
                
        except Exception as e:
            self.logger.error(f"SQL Server connection test failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Connection failed'
            }
    
    def get_databases(self, connection_params: Dict[str, str]) -> Dict[str, Any]:
        """Get list of accessible databases on SQL Server instance"""
        try:
            conn_string = self._build_connection_string(connection_params)
            
            with pyodbc.connect(conn_string) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        name,
                        database_id,
                        create_date,
                        collation_name,
                        state_desc,
                        compatibility_level
                    FROM sys.databases 
                    WHERE state = 0 
                        AND name NOT IN ('master', 'tempdb', 'model', 'msdb')
                    ORDER BY name
                """)
                
                databases = []
                for row in cursor.fetchall():
                    databases.append({
                        'name': row[0],
                        'database_id': row[1],
                        'created_date': row[2].isoformat() if row[2] else None,
                        'collation': row[3],
                        'state': row[4],
                        'compatibility_level': row[5]
                    })
                
                return {
                    'success': True,
                    'databases': databases,
                    'count': len(databases)
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get databases: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'databases': []
            }
    
    def get_database_schema(self, connection_params: Dict[str, str], database_name: str) -> Dict[str, Any]:
        """Get comprehensive schema information for a specific database"""
        try:
            # Update connection params to use specific database
            db_params = connection_params.copy()
            db_params['database'] = database_name
            
            conn_string = self._build_connection_string(db_params)
            
            with pyodbc.connect(conn_string) as conn:
                cursor = conn.cursor()
                
                # Get tables and views
                cursor.execute("""
                    SELECT 
                        TABLE_SCHEMA,
                        TABLE_NAME,
                        TABLE_TYPE,
                        CASE 
                            WHEN TABLE_TYPE = 'BASE TABLE' THEN 'table'
                            WHEN TABLE_TYPE = 'VIEW' THEN 'view'
                            ELSE 'other'
                        END as object_type
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_TYPE IN ('BASE TABLE', 'VIEW')
                    ORDER BY TABLE_SCHEMA, TABLE_NAME
                """)
                
                tables_info = {}
                for row in cursor.fetchall():
                    schema_name = row[0]
                    table_name = row[1]
                    table_type = row[2]
                    object_type = row[3]
                    
                    full_name = f"{schema_name}.{table_name}"
                    tables_info[full_name] = {
                        'schema': schema_name,
                        'name': table_name,
                        'type': object_type,
                        'full_name': full_name,
                        'columns': []
                    }
                
                # Get column information
                cursor.execute("""
                    SELECT 
                        c.TABLE_SCHEMA,
                        c.TABLE_NAME,
                        c.COLUMN_NAME,
                        c.DATA_TYPE,
                        c.IS_NULLABLE,
                        c.COLUMN_DEFAULT,
                        c.CHARACTER_MAXIMUM_LENGTH,
                        c.NUMERIC_PRECISION,
                        c.NUMERIC_SCALE,
                        c.ORDINAL_POSITION,
                        CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 1 ELSE 0 END as IS_PRIMARY_KEY
                    FROM INFORMATION_SCHEMA.COLUMNS c
                    LEFT JOIN (
                        SELECT ku.TABLE_SCHEMA, ku.TABLE_NAME, ku.COLUMN_NAME
                        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku
                            ON tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                            AND tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
                            AND tc.TABLE_SCHEMA = ku.TABLE_SCHEMA
                            AND tc.TABLE_NAME = ku.TABLE_NAME
                    ) pk ON c.TABLE_SCHEMA = pk.TABLE_SCHEMA 
                        AND c.TABLE_NAME = pk.TABLE_NAME 
                        AND c.COLUMN_NAME = pk.COLUMN_NAME
                    ORDER BY c.TABLE_SCHEMA, c.TABLE_NAME, c.ORDINAL_POSITION
                """)
                
                for row in cursor.fetchall():
                    schema_name = row[0]
                    table_name = row[1]
                    full_name = f"{schema_name}.{table_name}"
                    
                    if full_name in tables_info:
                        column_info = {
                            'name': row[2],
                            'data_type': row[3],
                            'is_nullable': row[4] == 'YES',
                            'default_value': row[5],
                            'max_length': row[6],
                            'precision': row[7],
                            'scale': row[8],
                            'ordinal_position': row[9],
                            'is_primary_key': bool(row[10]),
                            'is_foreign_key': False  # Will be updated below
                        }
                        tables_info[full_name]['columns'].append(column_info)
                
                # Get foreign key information
                cursor.execute("""
                    SELECT 
                        fk.TABLE_SCHEMA,
                        fk.TABLE_NAME,
                        fk.COLUMN_NAME,
                        fk.REFERENCED_TABLE_SCHEMA,
                        fk.REFERENCED_TABLE_NAME,
                        fk.REFERENCED_COLUMN_NAME,
                        fk.CONSTRAINT_NAME
                    FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
                    JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE fk
                        ON rc.CONSTRAINT_NAME = fk.CONSTRAINT_NAME
                        AND rc.CONSTRAINT_SCHEMA = fk.TABLE_SCHEMA
                    ORDER BY fk.TABLE_SCHEMA, fk.TABLE_NAME, fk.COLUMN_NAME
                """)
                
                foreign_keys = []
                for row in cursor.fetchall():
                    schema_name = row[0]
                    table_name = row[1]
                    full_name = f"{schema_name}.{table_name}"
                    column_name = row[2]
                    
                    # Mark column as foreign key
                    if full_name in tables_info:
                        for column in tables_info[full_name]['columns']:
                            if column['name'] == column_name:
                                column['is_foreign_key'] = True
                                column['referenced_table'] = f"{row[3]}.{row[4]}"
                                column['referenced_column'] = row[5]
                                break
                    
                    foreign_keys.append({
                        'from_schema': row[0],
                        'from_table': row[1],
                        'from_column': row[2],
                        'to_schema': row[3],
                        'to_table': row[4],
                        'to_column': row[5],
                        'constraint_name': row[6]
                    })
                
                # Get table row counts and additional metadata
                for full_name, table_info in tables_info.items():
                    if table_info['type'] == 'table':  # Only for tables, not views
                        try:
                            cursor.execute(f"""
                                SELECT 
                                    SUM(p.rows) as row_count
                                FROM sys.tables t
                                JOIN sys.schemas s ON t.schema_id = s.schema_id
                                JOIN sys.partitions p ON t.object_id = p.object_id
                                WHERE s.name = ? AND t.name = ? AND p.index_id IN (0, 1)
                                GROUP BY t.object_id
                            """, table_info['schema'], table_info['name'])
                            
                            row_count_result = cursor.fetchone()
                            table_info['row_count'] = row_count_result[0] if row_count_result else 0
                            
                        except Exception as e:
                            self.logger.warning(f"Could not get row count for {full_name}: {str(e)}")
                            table_info['row_count'] = 0
                
                return {
                    'success': True,
                    'database_name': database_name,
                    'tables': tables_info,
                    'foreign_keys': foreign_keys,
                    'schema_count': len(set(t['schema'] for t in tables_info.values())),
                    'table_count': len([t for t in tables_info.values() if t['type'] == 'table']),
                    'view_count': len([t for t in tables_info.values() if t['type'] == 'view'])
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get database schema for {database_name}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'database_name': database_name,
                'tables': {}
            }
    
    def execute_query(self, connection_params: Dict[str, str], query: str, limit: int = 1000) -> Dict[str, Any]:
        """Execute a SELECT query against SQL Server (read-only)"""
        try:
            # Validate query is SELECT only
            query_stripped = query.strip().upper()
            if not query_stripped.startswith('SELECT') and not query_stripped.startswith('WITH'):
                return {
                    'success': False,
                    'error': 'Only SELECT queries are allowed',
                    'data': []
                }
            
            conn_string = self._build_connection_string(connection_params)
            
            with pyodbc.connect(conn_string) as conn:
                cursor = conn.cursor()
                
                # Add TOP clause if not present and limit specified
                if limit and 'TOP' not in query_stripped and 'LIMIT' not in query_stripped:
                    if query_stripped.startswith('SELECT'):
                        query = query.replace('SELECT', f'SELECT TOP {limit}', 1)
                
                start_time = datetime.now()
                cursor.execute(query)
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # Get column names
                columns = [column[0] for column in cursor.description]
                
                # Fetch results
                rows = cursor.fetchall()
                
                # Convert to list of dictionaries
                data = []
                for row in rows:
                    row_dict = {}
                    for i, value in enumerate(row):
                        # Handle datetime objects
                        if isinstance(value, datetime):
                            row_dict[columns[i]] = value.isoformat()
                        else:
                            row_dict[columns[i]] = value
                    data.append(row_dict)
                
                return {
                    'success': True,
                    'data': data,
                    'columns': columns,
                    'row_count': len(data),
                    'execution_time': execution_time,
                    'query': query
                }
                
        except Exception as e:
            self.logger.error(f"Query execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'query': query
            }
    
    def get_query_plan(self, connection_params: Dict[str, str], query: str) -> Dict[str, Any]:
        """Get execution plan for a query"""
        try:
            conn_string = self._build_connection_string(connection_params)
            
            with pyodbc.connect(conn_string) as conn:
                cursor = conn.cursor()
                
                # Get estimated execution plan
                cursor.execute("SET SHOWPLAN_XML ON")
                cursor.execute(query)
                plan_result = cursor.fetchone()
                cursor.execute("SET SHOWPLAN_XML OFF")
                
                return {
                    'success': True,
                    'execution_plan': plan_result[0] if plan_result else None,
                    'query': query
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get query plan: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'execution_plan': None
            }
    
    def _build_connection_string(self, params: Dict[str, str]) -> str:
        """Build SQL Server connection string from parameters"""
        # Handle different parameter naming conventions
        server = params.get('server', params.get('host', 'localhost'))
        database = params.get('database', 'master')
        username = params.get('username', '')
        password = params.get('password', '')
        driver = params.get('driver', '{ODBC Driver 17 for SQL Server}')
        port = params.get('port', '1433')
        trust_cert = params.get('trust_server_certificate', 'yes')
        encrypt = params.get('encrypt', 'yes')
        timeout = params.get('timeout', '30')
        
        # Handle different authentication methods (support both auth_method and auth_type)
        auth_method = params.get('auth_method', params.get('auth_type', 'sql'))
        
        if auth_method == 'windows':
            # Windows Authentication
            conn_string = f"DRIVER={driver};SERVER={server},{port};DATABASE={database};Trusted_Connection=yes;TrustServerCertificate={trust_cert};Encrypt={encrypt};Connection Timeout={timeout};"
        elif auth_method == 'azure_ad':
            # Azure AD Authentication
            conn_string = f"DRIVER={driver};SERVER={server},{port};DATABASE={database};Authentication=ActiveDirectoryInteractive;TrustServerCertificate={trust_cert};Encrypt={encrypt};Connection Timeout={timeout};"
        else:
            # SQL Server Authentication
            if not username or not password:
                raise ValueError("Username and password required for SQL Server authentication")
            conn_string = f"DRIVER={driver};SERVER={server},{port};DATABASE={database};UID={username};PWD={password};TrustServerCertificate={trust_cert};Encrypt={encrypt};Connection Timeout={timeout};"
        
        return conn_string
    
    def get_server_info(self, connection_params: Dict[str, str]) -> Dict[str, Any]:
        """Get detailed SQL Server instance information"""
        try:
            conn_string = self._build_connection_string(connection_params)
            
            with pyodbc.connect(conn_string) as conn:
                cursor = conn.cursor()
                
                # Get server properties
                cursor.execute("""
                    SELECT 
                        @@VERSION as version,
                        @@SERVERNAME as server_name,
                        SERVERPROPERTY('ProductVersion') as product_version,
                        SERVERPROPERTY('ProductLevel') as product_level,
                        SERVERPROPERTY('Edition') as edition,
                        SERVERPROPERTY('EngineEdition') as engine_edition,
                        SERVERPROPERTY('MachineName') as machine_name,
                        SERVERPROPERTY('ServerName') as instance_name,
                        SERVERPROPERTY('IsClustered') as is_clustered,
                        SERVERPROPERTY('IsIntegratedSecurityOnly') as windows_auth_only
                """)
                
                server_info = cursor.fetchone()
                
                # Get database count
                cursor.execute("SELECT COUNT(*) FROM sys.databases WHERE state = 0")
                db_result = cursor.fetchone()
                db_count = db_result[0] if db_result else 0
                
                return {
                    'success': True,
                    'server_info': {
                        'version': server_info[0].split('\n')[0] if server_info and server_info[0] else 'Unknown',
                        'server_name': server_info[1] if server_info and len(server_info) > 1 else 'Unknown',
                        'product_version': server_info[2] if server_info and len(server_info) > 2 else 'Unknown',
                        'product_level': server_info[3] if server_info and len(server_info) > 3 else 'Unknown',
                        'edition': server_info[4] if server_info and len(server_info) > 4 else 'Unknown',
                        'engine_edition': server_info[5] if server_info and len(server_info) > 5 else 'Unknown',
                        'machine_name': server_info[6] if server_info and len(server_info) > 6 else 'Unknown',
                        'instance_name': server_info[7] if server_info and len(server_info) > 7 else 'Unknown',
                        'is_clustered': bool(server_info[8]) if server_info and len(server_info) > 8 else False,
                        'windows_auth_only': bool(server_info[9]) if server_info and len(server_info) > 9 else False,
                        'database_count': db_count
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get server info: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'server_info': {}
            }
    
    def validate_sql_server_query(self, query: str) -> Dict[str, Any]:
        """Validate SQL Server specific syntax and best practices"""
        issues = []
        suggestions = []
        
        query_upper = query.upper().strip()
        
        # Check for SQL Server specific issues
        if 'NOLOCK' in query_upper:
            issues.append("NOLOCK hint detected - may cause dirty reads")
            suggestions.append("Consider using READ UNCOMMITTED isolation level instead")
        
        if 'SELECT *' in query_upper:
            issues.append("SELECT * detected - avoid in production queries")
            suggestions.append("Specify explicit column names for better performance")
        
        if 'CURSOR' in query_upper:
            issues.append("Cursor usage detected - consider set-based operations")
            suggestions.append("Replace cursors with JOINs or CTEs where possible")
        
        # Check for missing WHERE clause in potentially large tables
        if ('FROM' in query_upper and 'WHERE' not in query_upper and 
            'JOIN' not in query_upper and 'GROUP BY' not in query_upper):
            issues.append("No WHERE clause detected - may return large result set")
            suggestions.append("Add WHERE clause to limit results")
        
        # Performance suggestions
        if 'ORDER BY' in query_upper and 'TOP' not in query_upper and 'OFFSET' not in query_upper:
            suggestions.append("Consider using TOP clause with ORDER BY for better performance")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'suggestions': suggestions,
            'query': query
        }