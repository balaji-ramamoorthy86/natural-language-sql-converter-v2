import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Any

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False
    pyodbc = None

class SchemaService:
    """Service for managing database schema information from JSON files"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Path to schema JSON files
        self.schemas_dir = Path(__file__).parent / 'schemas'
        
        # SQL Server connection configuration (for optional live discovery)
        self.server = os.getenv('SQL_SERVER_HOST', 'localhost')
        self.database = os.getenv('SQL_SERVER_DATABASE', 'master')
        self.username = os.getenv('SQL_SERVER_USERNAME', '')
        self.password = os.getenv('SQL_SERVER_PASSWORD', '')
        self.driver = os.getenv('SQL_SERVER_DRIVER', '{ODBC Driver 17 for SQL Server}')
        
        # Cache for loaded schemas
        self._schema_cache = {}
        
        # Ensure schemas directory exists
        self.schemas_dir.mkdir(exist_ok=True)
    
    def _load_schema_from_json(self, schema_name: str) -> Dict[str, Any]:
        """Load schema from JSON file"""
        json_file = self.schemas_dir / f"{schema_name}.json"
        
        if not json_file.exists():
            self.logger.warning(f"Schema file not found: {json_file}")
            return {}
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                schema_data = json.load(f)
            
            self.logger.info(f"Loaded schema '{schema_name}' from JSON file")
            return schema_data
            
        except Exception as e:
            self.logger.error(f"Error loading schema from {json_file}: {str(e)}")
            return {}
    
    def _discover_json_schemas(self) -> List[str]:
        """Discover all available JSON schema files"""
        try:
            json_files = list(self.schemas_dir.glob("*.json"))
            schema_names = [f.stem for f in json_files]
            self.logger.info(f"Discovered {len(schema_names)} JSON schema files: {schema_names}")
            return sorted(schema_names)
        except Exception as e:
            self.logger.error(f"Error discovering JSON schemas: {str(e)}")
            return []
    
    def get_available_schemas(self) -> List[str]:
        """Get list of available database schemas from JSON files"""
        try:
            # First try to get schemas from SQL Server if configured
            sql_schemas = self._get_schemas_from_sqlserver()
            if sql_schemas:
                self.logger.info(f"Found {len(sql_schemas)} schemas from SQL Server")
                return sql_schemas
            
            # Fallback to JSON file discovery
            json_schemas = self._discover_json_schemas()
            self.logger.info(f"Using {len(json_schemas)} schemas from JSON files")
            return json_schemas
            
        except Exception as e:
            self.logger.error(f"Error getting available schemas: {str(e)}")
            return []
    
    def get_schema_details(self, schema_name: str) -> Dict[str, Any]:
        """Get detailed schema information for a specific schema"""
        try:
            # Check cache first
            if schema_name in self._schema_cache:
                return self._schema_cache[schema_name]
            
            # Try to get from SQL Server first
            if self.server and self.server != 'localhost':
                sql_details = self._get_schema_details_from_sqlserver(schema_name)
                if sql_details:
                    self._schema_cache[schema_name] = sql_details
                    return sql_details
            
            # Fallback to JSON file
            json_schema = self._load_schema_from_json(schema_name)
            if json_schema:
                # Convert JSON format to expected API format
                formatted_schema = self._format_json_schema(json_schema)
                self._schema_cache[schema_name] = formatted_schema
                return formatted_schema
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Error getting schema details for '{schema_name}': {str(e)}")
            return {}
    
    def _format_json_schema(self, json_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Convert JSON schema format to API format"""
        try:
            formatted = {
                'schema_name': json_schema.get('schema_name', ''),
                'tables': {}
            }
            
            tables = json_schema.get('tables', {})
            for table_name, table_info in tables.items():
                columns = []
                primary_keys = []
                foreign_keys = []
                
                table_columns = table_info.get('columns', {})
                for col_name, col_info in table_columns.items():
                    column = {
                        'name': col_name,
                        'type': col_info.get('type', 'varchar'),
                        'nullable': col_info.get('nullable', True),
                        'description': col_info.get('description', '')
                    }
                    columns.append(column)
                    
                    # Track primary keys
                    if col_info.get('primary_key', False):
                        primary_keys.append(col_name)
                    
                    # Track foreign keys
                    if 'foreign_key' in col_info:
                        fk_info = col_info['foreign_key']
                        foreign_keys.append({
                            'column': col_name,
                            'referenced_table': fk_info.get('table', ''),
                            'referenced_column': fk_info.get('column', '')
                        })
                
                formatted['tables'][table_name] = {
                    'columns': columns,
                    'primary_keys': primary_keys,
                    'foreign_keys': foreign_keys
                }
            
            return formatted
            
        except Exception as e:
            self.logger.error(f"Error formatting JSON schema: {str(e)}")
            return {}
    
    def get_schema_context(self, schema_name: str) -> str:
        """Get formatted schema context for AI prompt"""
        try:
            schema_details = self.get_schema_details(schema_name)
            if not schema_details:
                return ""
            
            context_lines = [f"Database Schema: {schema_name}"]
            context_lines.append("=" * 50)
            
            tables = schema_details.get('tables', {})
            for table_name, table_info in tables.items():
                context_lines.append(f"\nTable: {table_name}")
                context_lines.append("-" * 30)
                
                columns = table_info.get('columns', [])
                for column in columns:
                    col_line = f"  {column['name']} ({column['type']})"
                    if not column.get('nullable', True):
                        col_line += " NOT NULL"
                    if column.get('description'):
                        col_line += f" - {column['description']}"
                    context_lines.append(col_line)
                
                # Add primary key info
                primary_keys = table_info.get('primary_keys', [])
                if primary_keys:
                    context_lines.append(f"  PRIMARY KEY: {', '.join(primary_keys)}")
                
                # Add foreign key info
                foreign_keys = table_info.get('foreign_keys', [])
                for fk in foreign_keys:
                    context_lines.append(
                        f"  FOREIGN KEY: {fk['column']} -> {fk['referenced_table']}.{fk['referenced_column']}"
                    )
            
            return "\n".join(context_lines)
            
        except Exception as e:
            self.logger.error(f"Error generating schema context: {str(e)}")
            return ""
    
    def add_schema_from_json_file(self, file_path: str, schema_name: str = None) -> bool:
        """Add a new schema from an uploaded JSON file"""
        try:
            source_path = Path(file_path)
            if not source_path.exists():
                self.logger.error(f"Source JSON file not found: {file_path}")
                return False
            
            # Determine schema name
            if not schema_name:
                schema_name = source_path.stem
            
            # Validate JSON format
            with open(source_path, 'r', encoding='utf-8') as f:
                schema_data = json.load(f)
            
            if 'schema_name' not in schema_data or 'tables' not in schema_data:
                self.logger.error("Invalid JSON schema format. Must contain 'schema_name' and 'tables'")
                return False
            
            # Copy to schemas directory
            target_path = self.schemas_dir / f"{schema_name}.json"
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(schema_data, f, indent=2, ensure_ascii=False)
            
            # Clear cache for this schema
            if schema_name in self._schema_cache:
                del self._schema_cache[schema_name]
            
            self.logger.info(f"Successfully added schema '{schema_name}' from JSON file")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding schema from JSON file: {str(e)}")
            return False
    
    def remove_schema(self, schema_name: str) -> bool:
        """Remove a schema by deleting its JSON file"""
        try:
            json_file = self.schemas_dir / f"{schema_name}.json"
            if json_file.exists():
                json_file.unlink()
                
                # Clear from cache
                if schema_name in self._schema_cache:
                    del self._schema_cache[schema_name]
                
                self.logger.info(f"Successfully removed schema '{schema_name}'")
                return True
            else:
                self.logger.warning(f"Schema file not found: {json_file}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error removing schema '{schema_name}': {str(e)}")
            return False
    
    def refresh_schema_cache(self, schema_name: str = None):
        """Refresh the cached schema information"""
        try:
            if schema_name:
                # Clear specific schema from cache
                if schema_name in self._schema_cache:
                    del self._schema_cache[schema_name]
                    self.logger.info(f"Cleared cache for schema '{schema_name}'")
            else:
                # Clear entire cache
                self._schema_cache.clear()
                self.logger.info("Cleared entire schema cache")
                
        except Exception as e:
            self.logger.error(f"Error refreshing schema cache: {str(e)}")
    
    # Keep SQL Server methods for live discovery (optional)
    def _get_connection_string(self) -> str:
        """Build SQL Server connection string"""
        if self.username and self.password:
            return f"DRIVER={self.driver};SERVER={self.server};DATABASE={self.database};UID={self.username};PWD={self.password}"
        else:
            return f"DRIVER={self.driver};SERVER={self.server};DATABASE={self.database};Trusted_Connection=yes"
    
    def _get_schemas_from_sqlserver(self) -> List[str]:
        """Get schemas directly from SQL Server"""
        try:
            if not PYODBC_AVAILABLE or not self.server or self.server == 'localhost':
                return []  # Skip if no real server configured
            
            conn_str = self._get_connection_string()
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sys.databases WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb')")
                schemas = [row[0] for row in cursor.fetchall()]
                return schemas
                
        except Exception as e:
            self.logger.warning(f"Could not connect to SQL Server: {str(e)}")
            return []
    
    def _get_schema_details_from_sqlserver(self, schema_name: str) -> Dict[str, Any]:
        """Get schema details directly from SQL Server"""
        try:
            if not PYODBC_AVAILABLE or not self.server or self.server == 'localhost':
                return {}  # Skip if no real server configured
            
            conn_str = self._get_connection_string()
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                
                # Query to get table and column information
                query = """
                SELECT 
                    t.TABLE_NAME,
                    c.COLUMN_NAME,
                    c.DATA_TYPE,
                    c.IS_NULLABLE,
                    c.COLUMN_DEFAULT,
                    CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 1 ELSE 0 END as IS_PRIMARY_KEY,
                    fk.REFERENCED_TABLE_NAME,
                    fk.REFERENCED_COLUMN_NAME
                FROM INFORMATION_SCHEMA.TABLES t
                LEFT JOIN INFORMATION_SCHEMA.COLUMNS c ON t.TABLE_NAME = c.TABLE_NAME
                LEFT JOIN (
                    SELECT ku.TABLE_NAME, ku.COLUMN_NAME
                    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS AS tc
                    INNER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE AS ku
                        ON tc.CONSTRAINT_TYPE = 'PRIMARY KEY' 
                        AND tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
                ) pk ON c.TABLE_NAME = pk.TABLE_NAME AND c.COLUMN_NAME = pk.COLUMN_NAME
                LEFT JOIN (
                    SELECT 
                        ku.TABLE_NAME,
                        ku.COLUMN_NAME,
                        ku.REFERENCED_TABLE_NAME,
                        ku.REFERENCED_COLUMN_NAME
                    FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS AS rc
                    INNER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE AS ku
                        ON rc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
                ) fk ON c.TABLE_NAME = fk.TABLE_NAME AND c.COLUMN_NAME = fk.COLUMN_NAME
                WHERE t.TABLE_CATALOG = ? AND t.TABLE_TYPE = 'BASE TABLE'
                ORDER BY t.TABLE_NAME, c.ORDINAL_POSITION
                """
                
                cursor.execute(query, (schema_name,))
                rows = cursor.fetchall()
                
                if not rows:
                    return {}
                
                # Process results into schema format
                tables = {}
                for row in rows:
                    table_name = row.TABLE_NAME
                    if table_name not in tables:
                        tables[table_name] = {
                            'columns': [],
                            'primary_keys': [],
                            'foreign_keys': []
                        }
                    
                    if row.COLUMN_NAME:  # Skip if no column info
                        column_info = {
                            'name': row.COLUMN_NAME,
                            'type': row.DATA_TYPE,
                            'nullable': row.IS_NULLABLE == 'YES',
                            'description': f"{row.COLUMN_NAME} column"
                        }
                        tables[table_name]['columns'].append(column_info)
                        
                        if row.IS_PRIMARY_KEY:
                            tables[table_name]['primary_keys'].append(row.COLUMN_NAME)
                        
                        if row.REFERENCED_TABLE_NAME:
                            fk_info = {
                                'column': row.COLUMN_NAME,
                                'referenced_table': row.REFERENCED_TABLE_NAME,
                                'referenced_column': row.REFERENCED_COLUMN_NAME
                            }
                            tables[table_name]['foreign_keys'].append(fk_info)
                
                return {
                    'schema_name': schema_name,
                    'tables': tables
                }
                
        except Exception as e:
            self.logger.warning(f"Could not get schema details from SQL Server: {str(e)}")
            return {}