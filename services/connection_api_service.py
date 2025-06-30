"""
Connection API Service
Handles fetching SQL Server connection strings from external API
"""

import os
import logging
import requests
from typing import Dict, Any, List, Optional

class ConnectionAPIService:
    """Service for fetching SQL Server connection details from API"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_base_url = os.environ.get('CONNECTION_API_URL', 'https://api.example.com/connections')
        self.api_key = os.environ.get('CONNECTION_API_KEY')
        self.timeout = 30
        
    def get_available_databases(self) -> Dict[str, Any]:
        """
        Get list of available databases from API
        
        Returns:
            Dictionary containing available databases or error
        """
        try:
            if not self.api_key:
                return {
                    'success': False,
                    'error': 'Connection API key not configured. Please set CONNECTION_API_KEY environment variable.'
                }
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f'{self.api_base_url}/databases',
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'databases': data.get('databases', [])
                }
            else:
                return {
                    'success': False,
                    'error': f'API returned status {response.status_code}: {response.text}'
                }
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching databases from API: {str(e)}")
            return {
                'success': False,
                'error': f'Network error: {str(e)}'
            }
        except Exception as e:
            self.logger.error(f"Unexpected error fetching databases: {str(e)}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }
    
    def get_connection_string_for_database(self, database_name: str) -> Dict[str, Any]:
        """
        Get connection string for a specific database from API
        
        Args:
            database_name: Name of the database to get connection string for
            
        Returns:
            Dictionary containing connection details or error
        """
        try:
            if not self.api_key:
                return {
                    'success': False,
                    'error': 'Connection API key not configured'
                }
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f'{self.api_base_url}/connection-string/{database_name}',
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                connection_details = data.get('connection', {})
                
                # Validate required fields
                required_fields = ['server', 'database', 'auth_method']
                for field in required_fields:
                    if field not in connection_details:
                        return {
                            'success': False,
                            'error': f'Missing required field: {field}'
                        }
                
                return {
                    'success': True,
                    'connection': connection_details
                }
            else:
                return {
                    'success': False,
                    'error': f'API returned status {response.status_code}: {response.text}'
                }
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching connection string from API: {str(e)}")
            return {
                'success': False,
                'error': f'Network error: {str(e)}'
            }
        except Exception as e:
            self.logger.error(f"Unexpected error fetching connection string: {str(e)}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }
    
    def validate_connection_format(self, connection: Dict[str, Any]) -> bool:
        """
        Validate that connection data has the expected format
        
        Args:
            connection: Connection dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['server', 'database', 'auth_method']
        
        for field in required_fields:
            if field not in connection:
                return False
        
        # Validate auth_method values
        valid_auth_methods = ['sql', 'windows', 'azure_ad']
        if connection['auth_method'] not in valid_auth_methods:
            return False
        
        # If SQL auth, check for credentials
        if connection['auth_method'] == 'sql':
            if 'username' not in connection or 'password' not in connection:
                return False
        
        return True
    
    def format_connection_for_sqlserver_service(self, connection: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format API connection data for SQLServerService
        
        Args:
            connection: Raw connection data from API
            
        Returns:
            Formatted connection parameters
        """
        formatted = {
            'server': connection['server'],
            'database': connection['database'],
            'auth_method': connection['auth_method'],
            'port': connection.get('port', '1433'),
            'timeout': connection.get('timeout', '30'),
            'encrypt': connection.get('encrypt', 'yes'),
            'trust_server_certificate': connection.get('trust_server_certificate', 'no')
        }
        
        # Add credentials if SQL auth
        if connection['auth_method'] == 'sql':
            formatted['username'] = connection.get('username', '')
            formatted['password'] = connection.get('password', '')
        
        return formatted
    
    def get_demo_databases(self) -> Dict[str, Any]:
        """
        Get demo databases for testing when API is not available
        
        Returns:
            Dictionary containing demo databases
        """
        return {
            'success': True,
            'databases': [
                {
                    'name': 'Northwind',
                    'description': 'Sample Northwind trading company database',
                    'environment': 'demo',
                    'server': 'Demo Server'
                },
                {
                    'name': 'AdventureWorks2019',
                    'description': 'Sample bicycle manufacturer database',
                    'environment': 'demo',
                    'server': 'Demo Server'
                },
                {
                    'name': 'WideWorldImporters',
                    'description': 'Sample wholesale novelty goods importer database',
                    'environment': 'demo',
                    'server': 'Demo Server'
                }
            ]
        }
    
    def get_demo_connection_string(self, database_name: str) -> Dict[str, Any]:
        """
        Get demo connection string for testing
        
        Args:
            database_name: Database name to get connection string for
            
        Returns:
            Dictionary containing demo connection details
        """
        demo_connections = {
            'Northwind': {
                'server': 'demo-server.database.windows.net',
                'database': 'Northwind',
                'auth_method': 'sql',
                'username': 'demo_user',
                'password': 'demo_password',
                'port': '1433',
                'encrypt': 'yes',
                'trust_server_certificate': 'no'
            },
            'AdventureWorks2019': {
                'server': 'demo-server.database.windows.net',
                'database': 'AdventureWorks2019',
                'auth_method': 'sql',
                'username': 'demo_user',
                'password': 'demo_password',
                'port': '1433',
                'encrypt': 'yes',
                'trust_server_certificate': 'no'
            },
            'WideWorldImporters': {
                'server': 'demo-server.database.windows.net',
                'database': 'WideWorldImporters',
                'auth_method': 'sql',
                'username': 'demo_user',
                'password': 'demo_password',
                'port': '1433',
                'encrypt': 'yes',
                'trust_server_certificate': 'no'
            }
        }
        
        if database_name in demo_connections:
            return {
                'success': True,
                'connection': demo_connections[database_name]
            }
        else:
            return {
                'success': False,
                'error': 'Demo database not found'
            }