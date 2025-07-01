import os
import logging
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from services.azure_openai_service import AzureOpenAIService
from services.sql_validator import SQLValidator
from services.schema_service import SchemaService
from services.sqlserver_service import SQLServerService
from services.connection_api_service import ConnectionAPIService

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///nlp_to_sql.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Disable caching for development
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

# Initialize the app with the extension
db.init_app(app)

# Initialize services
azure_openai_service = AzureOpenAIService()
sql_validator = SQLValidator()
schema_service = SchemaService()
sqlserver_service = SQLServerService()
connection_api_service = ConnectionAPIService()

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()

@app.route('/')
def index():
    """Main page with the natural language to SQL converter"""
    try:
        # Get available database schemas for context
        schemas = schema_service.get_available_schemas()
        return render_template('index.html', schemas=schemas)
    except Exception as e:
        app.logger.error(f"Error loading main page: {str(e)}")
        flash("Error loading application. Please try again.", "error")
        return render_template('index.html', schemas=[])

@app.route('/convert', methods=['POST'])
def convert_to_sql():
    """Convert natural language to SQL query"""
    try:
        data = request.get_json()
        
        if not data or 'natural_language' not in data:
            return jsonify({
                'success': False,
                'error': 'Natural language input is required'
            }), 400
        
        natural_language = data['natural_language'].strip()
        schema_context = data.get('schema_context', '')
        
        if not natural_language:
            return jsonify({
                'success': False,
                'error': 'Please provide a natural language description'
            }), 400
        
        app.logger.info(f"Converting natural language to SQL: {natural_language}")
        
        # Get schema context if provided
        schema_info = ""
        if schema_context:
            schema_info = schema_service.get_schema_context(schema_context)
        
        # Generate SQL using Azure OpenAI
        sql_result = azure_openai_service.generate_sql(
            natural_language=natural_language,
            schema_context=schema_info
        )
        
        if not sql_result['success']:
            return jsonify({
                'success': False,
                'error': sql_result['error']
            }), 500
        
        generated_sql = sql_result['sql']
        
        # Validate and optimize the generated SQL
        validation_result = sql_validator.validate_and_optimize(generated_sql)
        
        # Store the query in database for history
        query_record = models.QueryHistory(
            natural_language=natural_language,
            generated_sql=generated_sql,
            optimized_sql=validation_result.get('optimized_sql', generated_sql),
            is_valid=validation_result['is_valid']
        )
        db.session.add(query_record)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'sql': validation_result.get('optimized_sql', generated_sql),
            'explanation': sql_result.get('explanation', ''),
            'validation': validation_result,
            'query_id': query_record.id
        })
        
    except Exception as e:
        app.logger.error(f"Error converting natural language to SQL: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'An error occurred while generating SQL: {str(e)}'
        }), 500

@app.route('/validate', methods=['POST'])
def validate_sql():
    """Validate SQL query"""
    try:
        data = request.get_json()
        
        if not data or 'sql' not in data:
            return jsonify({
                'success': False,
                'error': 'SQL query is required'
            }), 400
        
        sql_query = data['sql'].strip()
        
        if not sql_query:
            return jsonify({
                'success': False,
                'error': 'Please provide a SQL query to validate'
            }), 400
        
        # Validate the SQL
        validation_result = sql_validator.validate_and_optimize(sql_query)
        
        return jsonify({
            'success': True,
            'validation': validation_result
        })
        
    except Exception as e:
        app.logger.error(f"Error validating SQL: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'An error occurred while validating SQL: {str(e)}'
        }), 500

@app.route('/schemas')
def get_schemas():
    """Get available database schemas"""
    try:
        schemas = schema_service.get_available_schemas()
        return jsonify({
            'success': True,
            'schemas': schemas
        })
    except Exception as e:
        app.logger.error(f"Error getting schemas: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'An error occurred while fetching schemas: {str(e)}'
        }), 500

@app.route('/schema/<schema_name>')
def get_schema_details(schema_name):
    """Get detailed information about a specific schema"""
    try:
        schema_details = schema_service.get_schema_details(schema_name)
        return jsonify({
            'success': True,
            'schema': schema_details
        })
    except Exception as e:
        app.logger.error(f"Error getting schema details: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'An error occurred while fetching schema details: {str(e)}'
        }), 500

@app.route('/history')
def query_history():
    """Get query history"""
    try:
        queries = models.QueryHistory.query.order_by(models.QueryHistory.created_at.desc()).limit(50).all()
        
        history = []
        for query in queries:
            history.append({
                'id': query.id,
                'natural_language': query.natural_language,
                'generated_sql': query.generated_sql,
                'optimized_sql': query.optimized_sql,
                'is_valid': query.is_valid,
                'created_at': query.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'history': history
        })
    except Exception as e:
        app.logger.error(f"Error getting query history: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'An error occurred while fetching query history: {str(e)}'
        }), 500

@app.route('/upload-schema', methods=['POST'])
def upload_schema():
    """Upload custom database schema"""
    try:
        data = request.get_json()
        
        if not data or 'schema_name' not in data or 'tables' not in data:
            return jsonify({
                'success': False,
                'error': 'Schema name and tables are required'
            }), 400
        
        schema_name = data['schema_name'].strip()
        tables = data['tables']
        
        if not schema_name or not tables:
            return jsonify({
                'success': False,
                'error': 'Please provide a valid schema name and table definitions'
            }), 400
        
        # Clear existing schema data for this schema
        models.DatabaseSchema.query.filter_by(schema_name=schema_name).delete()
        
        # Add new schema data
        for table_name, table_info in tables.items():
            for column in table_info.get('columns', []):
                schema_entry = models.DatabaseSchema(
                    schema_name=schema_name,
                    table_name=table_name,
                    column_name=column['name'],
                    data_type=column.get('type', 'varchar(255)'),
                    is_nullable=column.get('nullable', True),
                    is_primary_key=column.get('is_primary_key', False),
                    is_foreign_key=column.get('is_foreign_key', False),
                    referenced_table=column.get('referenced_table'),
                    referenced_column=column.get('referenced_column'),
                    column_description=column.get('description', '')
                )
                db.session.add(schema_entry)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Schema "{schema_name}" uploaded successfully'
        })
        
    except Exception as e:
        app.logger.error(f"Error uploading schema: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'An error occurred while uploading schema: {str(e)}'
        }), 500

@app.route('/analyze-schema', methods=['POST'])
def analyze_schema():
    """Analyze database schema and generate AI descriptions"""
    try:
        data = request.get_json()
        
        if not data or 'connection_info' not in data:
            return jsonify({
                'success': False,
                'error': 'Database connection information is required'
            }), 400
        
        connection_info = data['connection_info']
        
        # Initialize schema analyzer
        from services.schema_analyzer import SchemaAnalyzer
        analyzer = SchemaAnalyzer()
        
        # Analyze the database
        analysis_result = analyzer.analyze_database(connection_info)
        
        if analysis_result['success']:
            return jsonify({
                'success': True,
                'analysis': analysis_result['analysis'],
                'suggested_descriptions': analysis_result['descriptions']
            })
        else:
            return jsonify({
                'success': False,
                'error': analysis_result['error']
            }), 500
            
    except Exception as e:
        app.logger.error(f"Error analyzing schema: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'An error occurred while analyzing schema: {str(e)}'
        }), 500

# SQL Server specific routes
@app.route('/sqlserver/test-connection', methods=['POST'])
def test_sqlserver_connection():
    """Test connection to on-premises SQL Server"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Connection parameters are required'
            }), 400
        
        result = sqlserver_service.test_connection(data)
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error testing SQL Server connection: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Connection test failed: {str(e)}'
        }), 500

@app.route('/sqlserver/databases', methods=['POST'])
def get_sqlserver_databases():
    """Get list of databases from SQL Server instance"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Connection parameters are required'
            }), 400
        
        result = sqlserver_service.get_databases(data)
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error getting SQL Server databases: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get databases: {str(e)}'
        }), 500

@app.route('/sqlserver/schema/<database_name>', methods=['POST'])
def get_sqlserver_schema(database_name):
    """Get database schema from SQL Server"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Connection parameters are required'
            }), 400
        
        result = sqlserver_service.get_database_schema(data, database_name)
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error getting SQL Server schema: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get schema: {str(e)}'
        }), 500

@app.route('/sqlserver/execute', methods=['POST'])
def execute_sqlserver_query():
    """Execute query against SQL Server"""
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({
                'success': False,
                'error': 'Query and connection parameters are required'
            }), 400
        
        query = data['query']
        connection_params = data.get('connection', {})
        limit = data.get('limit', 1000)
        
        # Validate query using SQL Server service
        validation_result = sqlserver_service.validate_sql_server_query(query)
        
        # Execute query
        result = sqlserver_service.execute_query(connection_params, query, limit)
        
        # Add validation info to result
        result['validation'] = validation_result
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error executing SQL Server query: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Query execution failed: {str(e)}'
        }), 500

@app.route('/sqlserver/server-info', methods=['POST'])
def get_sqlserver_info():
    """Get SQL Server instance information"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Connection parameters are required'
            }), 400
        
        result = sqlserver_service.get_server_info(data)
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error getting SQL Server info: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get server info: {str(e)}'
        }), 500

@app.route('/sqlserver/query-plan', methods=['POST'])
def get_sqlserver_query_plan():
    """Get execution plan for SQL Server query"""
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({
                'success': False,
                'error': 'Query and connection parameters are required'
            }), 400
        
        query = data['query']
        connection_params = data.get('connection', {})
        
        result = sqlserver_service.get_query_plan(connection_params, query)
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error getting query plan: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get query plan: {str(e)}'
        }), 500

@app.route('/api/databases', methods=['GET'])
def get_available_databases():
    """Get available databases from API"""
    try:
        result = connection_api_service.get_available_databases()
        
        # If API is not available, provide demo databases for testing
        if not result['success'] and 'Connection API key not configured' in result.get('error', ''):
            result = connection_api_service.get_demo_databases()
            
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error getting available databases: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get databases: {str(e)}'
        }), 500

@app.route('/api/databases/<database_name>/connection', methods=['GET'])
def get_database_connection_string(database_name):
    """Get connection string for a specific database from API"""
    try:
        # Check if it's a demo database
        demo_databases = ['Northwind', 'AdventureWorks2019', 'WideWorldImporters']
        if database_name in demo_databases:
            result = connection_api_service.get_demo_connection_string(database_name)
        else:
            result = connection_api_service.get_connection_string_for_database(database_name)
            
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error getting connection string: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get connection string: {str(e)}'
        }), 500

@app.route('/api/databases/<database_name>/test', methods=['POST'])
def test_database_connection(database_name):
    """Test connection to a specific database using API-provided connection string"""
    try:
        # Get connection string from API
        demo_databases = ['Northwind', 'AdventureWorks2019', 'WideWorldImporters']
        if database_name in demo_databases:
            connection_result = connection_api_service.get_demo_connection_string(database_name)
        else:
            connection_result = connection_api_service.get_connection_string_for_database(database_name)
            
        if not connection_result['success']:
            return jsonify(connection_result), 400
            
        # Format for SQL Server service
        connection_params = connection_api_service.format_connection_for_sqlserver_service(
            connection_result['connection']
        )
        
        # Test the connection
        result = sqlserver_service.test_connection(connection_params)
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error testing database connection: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to test connection: {str(e)}'
        }), 500

@app.route('/api/databases/<database_name>/schema', methods=['GET'])
def get_database_schema_via_api(database_name):
    """Get schema for a specific database via API connection"""
    try:
        # Get connection string from API
        demo_databases = ['Northwind', 'AdventureWorks2019', 'WideWorldImporters']
        if database_name in demo_databases:
            connection_result = connection_api_service.get_demo_connection_string(database_name)
        else:
            connection_result = connection_api_service.get_connection_string_for_database(database_name)
            
        if not connection_result['success']:
            return jsonify(connection_result), 400
            
        # Format for SQL Server service
        connection_params = connection_api_service.format_connection_for_sqlserver_service(
            connection_result['connection']
        )
        
        # Get schema
        result = sqlserver_service.get_database_schema(connection_params, database_name)
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error getting database schema: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get schema: {str(e)}'
        }), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('base.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('base.html'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
