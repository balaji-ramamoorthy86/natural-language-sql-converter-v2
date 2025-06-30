"""
Windows Authentication Service
Handles Windows-based authentication for the Flask application
"""

import logging
import os
import subprocess
import ldap3
from typing import Dict, Any, Optional
import socket
from flask import request
import base64

class WindowsAuthService:
    """Service for handling Windows authentication"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # LDAP/AD configuration
        self.domain_controller = os.getenv('AD_DOMAIN_CONTROLLER', 'localhost')
        self.domain_name = os.getenv('AD_DOMAIN_NAME', 'DOMAIN')
        self.ldap_base_dn = os.getenv('AD_BASE_DN', f'DC={self.domain_name.lower()},DC=local')
        
        # Authentication methods
        self.auth_methods = {
            'ntlm': self._authenticate_ntlm,
            'kerberos': self._authenticate_kerberos,
            'ldap': self._authenticate_ldap,
            'header': self._authenticate_from_headers
        }
    
    def authenticate_user(self, method: str = 'auto') -> Dict[str, Any]:
        """
        Authenticate user using Windows credentials
        
        Args:
            method: Authentication method ('auto', 'ntlm', 'kerberos', 'ldap', 'header')
            
        Returns:
            Dictionary containing authentication result
        """
        try:
            if method == 'auto':
                # Try different methods in order of preference
                for auth_method in ['header', 'ntlm', 'kerberos', 'ldap']:
                    result = self._try_authentication_method(auth_method)
                    if result['success']:
                        return result
                
                return {
                    'success': False,
                    'error': 'No authentication method succeeded',
                    'user': None
                }
            else:
                return self._try_authentication_method(method)
                
        except Exception as e:
            self.logger.error(f"Authentication error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'user': None
            }
    
    def _try_authentication_method(self, method: str) -> Dict[str, Any]:
        """Try a specific authentication method"""
        if method not in self.auth_methods:
            return {
                'success': False,
                'error': f'Unknown authentication method: {method}',
                'user': None
            }
        
        try:
            return self.auth_methods[method]()
        except Exception as e:
            self.logger.warning(f"Authentication method {method} failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'user': None
            }
    
    def _authenticate_from_headers(self) -> Dict[str, Any]:
        """
        Authenticate from HTTP headers (when behind IIS/Apache with Windows Auth)
        """
        # Check for common Windows authentication headers
        headers_to_check = [
            'REMOTE_USER',
            'HTTP_REMOTE_USER',
            'AUTH_USER',
            'LOGON_USER',
            'HTTP_X_REMOTE_USER'
        ]
        
        username = None
        for header in headers_to_check:
            username = request.environ.get(header) or request.headers.get(header.replace('HTTP_', '').replace('_', '-'))
            if username:
                break
        
        if not username:
            return {
                'success': False,
                'error': 'No Windows authentication headers found',
                'user': None
            }
        
        # Clean up the username (remove domain prefix if present)
        if '\\' in username:
            domain, username = username.split('\\', 1)
        elif '@' in username:
            username = username.split('@')[0]
        
        # Get additional user information from AD if available
        user_info = self._get_user_info_from_ad(username)
        
        return {
            'success': True,
            'method': 'header',
            'user': {
                'username': username,
                'display_name': user_info.get('display_name', username),
                'email': user_info.get('email', ''),
                'groups': user_info.get('groups', []),
                'domain': user_info.get('domain', self.domain_name)
            }
        }
    
    def _authenticate_ntlm(self) -> Dict[str, Any]:
        """
        Authenticate using NTLM (requires client to send NTLM tokens)
        """
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('NTLM '):
            return {
                'success': False,
                'error': 'NTLM authentication required',
                'user': None,
                'challenge': True
            }
        
        # In a real implementation, you would:
        # 1. Parse the NTLM token
        # 2. Validate against domain controller
        # 3. Extract user information
        
        # For now, return a placeholder response
        return {
            'success': False,
            'error': 'NTLM authentication not fully implemented',
            'user': None
        }
    
    def _authenticate_kerberos(self) -> Dict[str, Any]:
        """
        Authenticate using Kerberos
        """
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Negotiate '):
            return {
                'success': False,
                'error': 'Kerberos authentication required',
                'user': None
            }
        
        # In a real implementation, you would:
        # 1. Parse the Kerberos token
        # 2. Validate the ticket
        # 3. Extract user information
        
        return {
            'success': False,
            'error': 'Kerberos authentication not fully implemented',
            'user': None
        }
    
    def _authenticate_ldap(self) -> Dict[str, Any]:
        """
        Authenticate using LDAP bind
        """
        # This method requires username/password from a form
        # Not suitable for single sign-on scenarios
        return {
            'success': False,
            'error': 'LDAP authentication requires explicit credentials',
            'user': None
        }
    
    def _get_user_info_from_ad(self, username: str) -> Dict[str, Any]:
        """
        Get user information from Active Directory
        """
        try:
            # Connect to AD
            server = ldap3.Server(self.domain_controller, get_info=ldap3.ALL)
            
            # Use anonymous bind or service account
            service_user = os.getenv('AD_SERVICE_USER')
            service_pass = os.getenv('AD_SERVICE_PASSWORD')
            
            if service_user and service_pass:
                conn = ldap3.Connection(server, user=service_user, password=service_pass)
            else:
                conn = ldap3.Connection(server)
            
            if not conn.bind():
                self.logger.warning("Could not bind to Active Directory")
                return {}
            
            # Search for user
            search_filter = f'(sAMAccountName={username})'
            attributes = ['displayName', 'mail', 'memberOf', 'userPrincipalName']
            
            conn.search(
                search_base=self.ldap_base_dn,
                search_filter=search_filter,
                attributes=attributes
            )
            
            if not conn.entries:
                return {}
            
            entry = conn.entries[0]
            
            # Extract group memberships
            groups = []
            if hasattr(entry, 'memberOf'):
                for group_dn in entry.memberOf:
                    # Extract group name from DN
                    group_name = group_dn.split(',')[0].replace('CN=', '')
                    groups.append(group_name)
            
            user_info = {
                'display_name': str(entry.displayName) if hasattr(entry, 'displayName') else username,
                'email': str(entry.mail) if hasattr(entry, 'mail') else '',
                'groups': groups,
                'domain': self.domain_name,
                'principal_name': str(entry.userPrincipalName) if hasattr(entry, 'userPrincipalName') else ''
            }
            
            conn.unbind()
            return user_info
            
        except Exception as e:
            self.logger.error(f"Error getting user info from AD: {str(e)}")
            return {}
    
    def check_user_authorization(self, username: str, required_groups: list = None) -> bool:
        """
        Check if user is authorized based on group membership
        
        Args:
            username: Username to check
            required_groups: List of required group names
            
        Returns:
            True if user is authorized, False otherwise
        """
        if not required_groups:
            return True
        
        user_info = self._get_user_info_from_ad(username)
        user_groups = user_info.get('groups', [])
        
        # Check if user is in any of the required groups
        return any(group in user_groups for group in required_groups)
    
    def get_client_ip(self) -> str:
        """Get client IP address"""
        if request.environ.get('HTTP_X_FORWARDED_FOR'):
            return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
        elif request.environ.get('HTTP_X_REAL_IP'):
            return request.environ['HTTP_X_REAL_IP']
        else:
            return request.environ.get('REMOTE_ADDR', 'unknown')
    
    def is_domain_computer(self, ip_address: str = None) -> bool:
        """
        Check if the request is coming from a domain computer
        """
        if not ip_address:
            ip_address = self.get_client_ip()
        
        try:
            # Try to resolve hostname
            hostname = socket.gethostbyaddr(ip_address)[0]
            
            # Check if hostname contains domain name
            return self.domain_name.lower() in hostname.lower()
            
        except:
            return False
    
    def create_user_session(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create user session data
        """
        return {
            'user_id': user_info['username'],
            'username': user_info['username'],
            'display_name': user_info.get('display_name', user_info['username']),
            'email': user_info.get('email', ''),
            'groups': user_info.get('groups', []),
            'domain': user_info.get('domain', self.domain_name),
            'authenticated_at': int(self._get_current_timestamp()),
            'auth_method': user_info.get('method', 'windows')
        }
    
    def _get_current_timestamp(self) -> float:
        """Get current timestamp"""
        import time
        return time.time()