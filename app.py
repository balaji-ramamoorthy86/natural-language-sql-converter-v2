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

def convert_analysis_to_json_schema(analysis_result, schema_name):
    """Convert schema analyzer results to JSON schema format"""
    json_schema = {
        "schema_name": schema_name,
        "description": f"AI-analyzed schema for {schema_name} database",
        "tables": {}
    }
    
    schema_info = analysis_result.get('schema_info', {})
    descriptions = analysis_result.get('descriptions', {})
    
    for table_name, table_info in schema_info.items():
        json_schema['tables'][table_name] = {
            "description": descriptions.get('tables', {}).get(table_name, {}).get('description', f'Table: {table_name}'),
            "columns": {}
        }
        
        for column_info in table_info.get('columns', []):
            col_name = column_info['name']
            json_schema['tables'][table_name]['columns'][col_name] = {
                "type": column_info.get('type', 'varchar(255)'),
                "nullable": column_info.get('nullable', True),
                "primary_key": column_info.get('is_primary_key', False),
                "description": descriptions.get('columns', {}).get(table_name, {}).get(col_name, f'{col_name} column')
            }
            
            # Add foreign key information if available
            if column_info.get('foreign_key'):
                json_schema['tables'][table_name]['columns'][col_name]['foreign_key'] = {
                    "table": column_info['foreign_key'].get('table'),
                    "column": column_info['foreign_key'].get('column')
                }
    
    return json_schema

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
        
        # Create JSON schema file using the schema service
        import tempfile
        import json
        
        schema_data = {
            'schema_name': schema_name,
            'description': f'Custom schema: {schema_name}',
            'tables': {}
        }
        
        # Convert the uploaded format to our JSON format
        for table_name, table_info in tables.items():
            schema_data['tables'][table_name] = {
                'description': f'Table: {table_name}',
                'columns': {}
            }
            
            for column in table_info.get('columns', []):
                col_name = column['name']
                schema_data['tables'][table_name]['columns'][col_name] = {
                    'type': column.get('type', 'varchar(255)'),
                    'nullable': column.get('nullable', True),
                    'primary_key': column.get('is_primary_key', False),
                    'description': column.get('description', f'{col_name} column')
                }
                
                # Handle foreign keys
                if column.get('is_foreign_key') and column.get('referenced_table'):
                    schema_data['tables'][table_name]['columns'][col_name]['foreign_key'] = {
                        'table': column.get('referenced_table'),
                        'column': column.get('referenced_column')
                    }
        
        # Write to temporary file and then add to service
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(schema_data, temp_file, indent=2)
            temp_file_path = temp_file.name
        
        # Add schema using the service
        success = schema_service.add_schema_from_json_file(temp_file_path, schema_name)
        
        # Clean up temp file
        import os
        os.unlink(temp_file_path)
        
        if not success:
            raise Exception('Failed to save schema to JSON file')
        
        return jsonify({
            'success': True,
            'message': f'Schema "{schema_name}" uploaded successfully as JSON file'
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
            # Automatically create and save JSON schema from analysis
            schema_name = connection_info.get('database', 'analyzed_schema')
            json_schema = convert_analysis_to_json_schema(analysis_result, schema_name)
            
            # Save to JSON file automatically
            import tempfile
            import json
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump(json_schema, temp_file, indent=2)
                temp_file_path = temp_file.name
            
            # Add schema using the service
            success = schema_service.add_schema_from_json_file(temp_file_path, schema_name)
            
            # Clean up temp file
            import os
            os.unlink(temp_file_path)
            
            return jsonify({
                'success': True,
                'analysis': analysis_result['analysis'],
                'suggested_descriptions': analysis_result['descriptions'],
                'schema_saved': success,
                'schema_name': schema_name,
                'message': f'Schema "{schema_name}" automatically saved to services/schemas/' if success else 'Analysis complete but failed to save schema'
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



@app.errorhandler(404)
def not_found_error(error):
    return render_template('base.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('base.html'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
