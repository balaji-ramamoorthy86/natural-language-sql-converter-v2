import os
import logging
from typing import Dict, List, Any
import pyodbc

class SchemaService:
    """Service for managing database schema information"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # SQL Server connection configuration
        self.server = os.getenv('SQL_SERVER_HOST', 'localhost')
        self.database = os.getenv('SQL_SERVER_DATABASE', 'master')
        self.username = os.getenv('SQL_SERVER_USERNAME', '')
        self.password = os.getenv('SQL_SERVER_PASSWORD', '')
        self.driver = os.getenv('SQL_SERVER_DRIVER', '{ODBC Driver 17 for SQL Server}')
        
        # Sample schema data will be initialized when first accessed
    
    def _initialize_sample_schemas(self):
        """Initialize sample database schemas for demonstration"""
        try:
            from app import db
            from models import DatabaseSchema
            
            # Check if we already have the ecommerce schema
            existing_schema = DatabaseSchema.query.filter_by(schema_name='ecommerce').first()
            if existing_schema:
                return
            
            # Sample e-commerce schema
            sample_schemas = [
                # Users table
                {
                    'schema_name': 'ecommerce',
                    'table_name': 'users',
                    'column_name': 'user_id',
                    'data_type': 'int',
                    'is_nullable': False,
                    'is_primary_key': True,
                    'column_description': 'Unique identifier for users'
                },
                {
                    'schema_name': 'ecommerce',
                    'table_name': 'users',
                    'column_name': 'username',
                    'data_type': 'varchar(50)',
                    'is_nullable': False,
                    'column_description': 'User login name'
                },
                {
                    'schema_name': 'ecommerce',
                    'table_name': 'users',
                    'column_name': 'email',
                    'data_type': 'varchar(255)',
                    'is_nullable': False,
                    'column_description': 'User email address'
                },
                {
                    'schema_name': 'ecommerce',
                    'table_name': 'users',
                    'column_name': 'created_at',
                    'data_type': 'datetime',
                    'is_nullable': False,
                    'column_description': 'Account creation timestamp'
                },
                
                # Products table
                {
                    'schema_name': 'ecommerce',
                    'table_name': 'products',
                    'column_name': 'product_id',
                    'data_type': 'int',
                    'is_nullable': False,
                    'is_primary_key': True,
                    'column_description': 'Unique identifier for products'
                },
                {
                    'schema_name': 'ecommerce',
                    'table_name': 'products',
                    'column_name': 'product_name',
                    'data_type': 'varchar(255)',
                    'is_nullable': False,
                    'column_description': 'Product name'
                },
                {
                    'schema_name': 'ecommerce',
                    'table_name': 'products',
                    'column_name': 'price',
                    'data_type': 'decimal(10,2)',
                    'is_nullable': False,
                    'column_description': 'Product price'
                },
                {
                    'schema_name': 'ecommerce',
                    'table_name': 'products',
                    'column_name': 'category_id',
                    'data_type': 'int',
                    'is_nullable': True,
                    'is_foreign_key': True,
                    'referenced_table': 'categories',
                    'referenced_column': 'category_id',
                    'column_description': 'Product category reference'
                },
                
                # Orders table
                {
                    'schema_name': 'ecommerce',
                    'table_name': 'orders',
                    'column_name': 'order_id',
                    'data_type': 'int',
                    'is_nullable': False,
                    'is_primary_key': True,
                    'column_description': 'Unique identifier for orders'
                },
                {
                    'schema_name': 'ecommerce',
                    'table_name': 'orders',
                    'column_name': 'user_id',
                    'data_type': 'int',
                    'is_nullable': False,
                    'is_foreign_key': True,
                    'referenced_table': 'users',
                    'referenced_column': 'user_id',
                    'column_description': 'Customer reference'
                },
                {
                    'schema_name': 'ecommerce',
                    'table_name': 'orders',
                    'column_name': 'order_date',
                    'data_type': 'datetime',
                    'is_nullable': False,
                    'column_description': 'Order creation date'
                },
                {
                    'schema_name': 'ecommerce',
                    'table_name': 'orders',
                    'column_name': 'total_amount',
                    'data_type': 'decimal(10,2)',
                    'is_nullable': False,
                    'column_description': 'Total order amount'
                },
                
                # Categories table
                {
                    'schema_name': 'ecommerce',
                    'table_name': 'categories',
                    'column_name': 'category_id',
                    'data_type': 'int',
                    'is_nullable': False,
                    'is_primary_key': True,
                    'column_description': 'Unique identifier for categories'
                },
                {
                    'schema_name': 'ecommerce',
                    'table_name': 'categories',
                    'column_name': 'category_name',
                    'data_type': 'varchar(100)',
                    'is_nullable': False,
                    'column_description': 'Category name'
                }
            ]
            
            # Add sample schemas to database
            for schema_data in sample_schemas:
                schema_entry = DatabaseSchema(**schema_data)
                db.session.add(schema_entry)
            
            db.session.commit()
            self.logger.info("Sample database schemas initialized")
            
        except Exception as e:
            self.logger.error(f"Error initializing sample schemas: {str(e)}")
            # Try to rollback if db is available
            try:
                from app import db
                db.session.rollback()
            except:
                pass
    
    def get_available_schemas(self) -> List[str]:
        """Get list of available database schemas"""
        try:
            # Try to connect to actual SQL Server
            schemas = self._get_schemas_from_sqlserver()
            if schemas:
                return schemas
            
            # Fallback to stored schema information
            try:
                from app import db
                from models import DatabaseSchema
                
                # Initialize sample schemas if needed
                existing_schemas = DatabaseSchema.query.filter_by(schema_name='ecommerce').first()
                if not existing_schemas:
                    self._initialize_sample_schemas()
                
                stored_schemas = db.session.query(DatabaseSchema.schema_name).distinct().all()
                return [schema[0] for schema in stored_schemas]
            except:
                return ['ecommerce']  # Default fallback
            
        except Exception as e:
            self.logger.error(f"Error getting available schemas: {str(e)}")
            return ['ecommerce']  # Default fallback
    
    def get_schema_details(self, schema_name: str) -> Dict[str, Any]:
        """Get detailed schema information for a specific schema"""
        try:
            # Try to get from actual SQL Server first
            details = self._get_schema_details_from_sqlserver(schema_name)
            if details:
                return details
            
            # Fallback to stored schema information
            try:
                from models import DatabaseSchema
                schema_entries = DatabaseSchema.query.filter_by(schema_name=schema_name).all()
                
                if not schema_entries:
                    return {}
                
                tables = {}
                for entry in schema_entries:
                    if entry.table_name not in tables:
                        tables[entry.table_name] = {
                            'columns': [],
                            'primary_keys': [],
                            'foreign_keys': []
                        }
                    
                    column_info = {
                        'name': entry.column_name,
                        'type': entry.data_type,
                        'nullable': entry.is_nullable,
                        'description': entry.column_description
                    }
                    
                    tables[entry.table_name]['columns'].append(column_info)
                    
                    if entry.is_primary_key:
                        tables[entry.table_name]['primary_keys'].append(entry.column_name)
                    
                    if entry.is_foreign_key:
                        tables[entry.table_name]['foreign_keys'].append({
                            'column': entry.column_name,
                            'referenced_table': entry.referenced_table,
                            'referenced_column': entry.referenced_column
                        })
                
                return {
                    'schema_name': schema_name,
                    'tables': tables
                }
            except:
                return {}
            
        except Exception as e:
            self.logger.error(f"Error getting schema details: {str(e)}")
            return {}
    
    def get_schema_context(self, schema_name: str) -> str:
        """Get formatted schema context for AI prompt"""
        try:
            schema_details = self.get_schema_details(schema_name)
            
            if not schema_details or 'tables' not in schema_details:
                return ""
            
            context = f"Database Schema: {schema_name}\n\n"
            
            for table_name, table_info in schema_details['tables'].items():
                context += f"Table: {table_name}\n"
                context += "Columns:\n"
                
                for column in table_info['columns']:
                    nullable = "NULL" if column['nullable'] else "NOT NULL"
                    description = f" -- {column['description']}" if column['description'] else ""
                    context += f"  - {column['name']} ({column['type']}) {nullable}{description}\n"
                
                if table_info['primary_keys']:
                    context += f"Primary Key(s): {', '.join(table_info['primary_keys'])}\n"
                
                if table_info['foreign_keys']:
                    context += "Foreign Keys:\n"
                    for fk in table_info['foreign_keys']:
                        context += f"  - {fk['column']} -> {fk['referenced_table']}.{fk['referenced_column']}\n"
                
                context += "\n"
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error generating schema context: {str(e)}")
            return ""
    
    def _get_connection_string(self) -> str:
        """Build SQL Server connection string"""
        if self.username and self.password:
            return f"DRIVER={self.driver};SERVER={self.server};DATABASE={self.database};UID={self.username};PWD={self.password}"
        else:
            return f"DRIVER={self.driver};SERVER={self.server};DATABASE={self.database};Trusted_Connection=yes"
    
    def _get_schemas_from_sqlserver(self) -> List[str]:
        """Get schemas directly from SQL Server"""
        try:
            if not self.server or self.server == 'localhost':
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
            if not self.server or self.server == 'localhost':
                return {}  # Skip if no real server configured
            
            conn_str = self._get_connection_string()
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                
                # Query to get table and column information
                query = """
                SELECT 
                    t.TABLE_SCHEMA,
                    t.TABLE_NAME,
                    c.COLUMN_NAME,
                    c.DATA_TYPE,
                    c.IS_NULLABLE,
                    CASE WHEN tc.CONSTRAINT_TYPE = 'PRIMARY KEY' THEN 1 ELSE 0 END as IS_PRIMARY_KEY,
                    CASE WHEN tc.CONSTRAINT_TYPE = 'FOREIGN KEY' THEN 1 ELSE 0 END as IS_FOREIGN_KEY
                FROM INFORMATION_SCHEMA.TABLES t
                JOIN INFORMATION_SCHEMA.COLUMNS c ON t.TABLE_NAME = c.TABLE_NAME
                LEFT JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu ON c.COLUMN_NAME = kcu.COLUMN_NAME AND c.TABLE_NAME = kcu.TABLE_NAME
                LEFT JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc ON kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
                WHERE t.TABLE_CATALOG = ?
                ORDER BY t.TABLE_NAME, c.ORDINAL_POSITION
                """
                
                cursor.execute(query, schema_name)
                rows = cursor.fetchall()
                
                tables = {}
                for row in rows:
                    table_name = row[1]
                    if table_name not in tables:
                        tables[table_name] = {
                            'columns': [],
                            'primary_keys': [],
                            'foreign_keys': []
                        }
                    
                    column_info = {
                        'name': row[2],
                        'type': row[3],
                        'nullable': row[4] == 'YES',
                        'description': ''
                    }
                    
                    tables[table_name]['columns'].append(column_info)
                    
                    if row[5]:  # IS_PRIMARY_KEY
                        tables[table_name]['primary_keys'].append(row[2])
                
                return {
                    'schema_name': schema_name,
                    'tables': tables
                }
                
        except Exception as e:
            self.logger.warning(f"Could not get schema details from SQL Server: {str(e)}")
            return {}
    
    def refresh_schema_cache(self, schema_name: str = None):
        """Refresh the cached schema information"""
        try:
            from app import db
            from models import DatabaseSchema
            
            if schema_name:
                # Refresh specific schema
                DatabaseSchema.query.filter_by(schema_name=schema_name).delete()
            else:
                # Refresh all schemas
                DatabaseSchema.query.delete()
            
            db.session.commit()
            
            # Re-initialize sample data if no real server
            if not self.server or self.server == 'localhost':
                self._initialize_sample_schemas()
            
            self.logger.info(f"Schema cache refreshed for: {schema_name or 'all schemas'}")
            
        except Exception as e:
            self.logger.error(f"Error refreshing schema cache: {str(e)}")
            try:
                from app import db
                db.session.rollback()
            except:
                pass