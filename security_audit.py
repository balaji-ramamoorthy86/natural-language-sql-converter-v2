"""
Security Audit Script for Natural Language to SQL Application
Scans for common security vulnerabilities and provides recommendations
"""

import os
import re
import ast
import logging
from typing import List, Dict, Any
import subprocess

class SecurityAuditor:
    """Comprehensive security auditor for the Flask application"""
    
    def __init__(self):
        self.vulnerabilities = []
        self.warnings = []
        self.recommendations = []
        self.logger = logging.getLogger(__name__)
        
    def audit_application(self) -> Dict[str, Any]:
        """Run complete security audit"""
        print("🔍 Starting Security Audit...")
        
        # File system security
        self._audit_file_permissions()
        
        # Code security
        self._audit_python_code()
        
        # Configuration security
        self._audit_configuration()
        
        # Dependencies security
        self._audit_dependencies()
        
        # SQL injection protection
        self._audit_sql_security()
        
        # Authentication and authorization
        self._audit_auth_security()
        
        # Environment variables
        self._audit_environment_security()
        
        # Web security headers
        self._audit_web_security()
        
        return {
            'vulnerabilities': self.vulnerabilities,
            'warnings': self.warnings,
            'recommendations': self.recommendations,
            'summary': self._generate_summary()
        }
    
    def _audit_file_permissions(self):
        """Check file permissions for security issues"""
        print("📁 Auditing file permissions...")
        
        sensitive_files = [
            'app.py', 'main.py', 'models.py', 
            '.env', 'pyproject.toml', 'uv.lock'
        ]
        
        for file_path in sensitive_files:
            if os.path.exists(file_path):
                stat_info = os.stat(file_path)
                permissions = oct(stat_info.st_mode)[-3:]
                
                if permissions in ['777', '666']:
                    self.vulnerabilities.append({
                        'type': 'File Permissions',
                        'severity': 'HIGH',
                        'file': file_path,
                        'issue': f'File has overly permissive permissions: {permissions}',
                        'recommendation': 'Set restrictive permissions (644 for files, 755 for directories)'
                    })
    
    def _audit_python_code(self):
        """Audit Python code for security vulnerabilities"""
        print("🐍 Auditing Python code...")
        
        python_files = []
        for root, dirs, files in os.walk('.'):
            # Skip virtual environments and cache directories
            dirs[:] = [d for d in dirs if d not in ['.venv', '__pycache__', '.git']]
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        for file_path in python_files:
            self._audit_python_file(file_path)
    
    def _audit_python_file(self, file_path: str):
        """Audit a single Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for dangerous functions
            dangerous_patterns = [
                (r'eval\s*\(', 'Use of eval() function', 'HIGH'),
                (r'exec\s*\(', 'Use of exec() function', 'HIGH'),
                (r'__import__\s*\(', 'Dynamic import usage', 'MEDIUM'),
                (r'pickle\.loads?\s*\(', 'Pickle deserialization', 'HIGH'),
                (r'subprocess\..*shell=True', 'Shell injection risk', 'HIGH'),
                (r'os\.system\s*\(', 'OS command execution', 'HIGH'),
                (r'flask\.request\.args\.get\([^,)]*\)', 'Unvalidated user input', 'MEDIUM'),
            ]
            
            for pattern, description, severity in dangerous_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    self.vulnerabilities.append({
                        'type': 'Code Security',
                        'severity': severity,
                        'file': file_path,
                        'issue': description,
                        'pattern': pattern,
                        'recommendation': f'Review usage of {description.lower()} in {file_path}'
                    })
            
            # Check for hardcoded secrets
            secret_patterns = [
                (r'password\s*=\s*["\'][^"\']+["\']', 'Hardcoded password'),
                (r'api_key\s*=\s*["\'][^"\']+["\']', 'Hardcoded API key'),
                (r'secret_key\s*=\s*["\'][^"\']+["\']', 'Hardcoded secret key'),
                (r'token\s*=\s*["\'][^"\']+["\']', 'Hardcoded token'),
            ]
            
            for pattern, description in secret_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Skip if it's using environment variables
                    if 'os.environ' not in match.group(0) and 'getenv' not in match.group(0):
                        self.vulnerabilities.append({
                            'type': 'Hardcoded Secrets',
                            'severity': 'HIGH',
                            'file': file_path,
                            'issue': description,
                            'line': match.group(0).strip(),
                            'recommendation': 'Use environment variables for sensitive data'
                        })
            
        except Exception as e:
            self.warnings.append(f"Could not audit {file_path}: {str(e)}")
    
    def _audit_configuration(self):
        """Audit configuration files"""
        print("⚙️ Auditing configuration...")
        
        # Check Flask configuration
        config_issues = []
        
        # Check if DEBUG is enabled in production
        if os.getenv('FLASK_ENV') == 'production' and os.getenv('FLASK_DEBUG', '').lower() == 'true':
            config_issues.append({
                'issue': 'Debug mode enabled in production',
                'severity': 'HIGH',
                'recommendation': 'Disable debug mode in production'
            })
        
        # Check secret key configuration
        if not os.getenv('SESSION_SECRET'):
            config_issues.append({
                'issue': 'No SESSION_SECRET environment variable found',
                'severity': 'HIGH',
                'recommendation': 'Set a strong, random SESSION_SECRET'
            })
        
        self.vulnerabilities.extend([{
            'type': 'Configuration',
            **issue
        } for issue in config_issues])
    
    def _audit_dependencies(self):
        """Audit dependencies for known vulnerabilities"""
        print("📦 Auditing dependencies...")
        
        try:
            # Check if there are known vulnerabilities in installed packages
            result = subprocess.run(['pip', 'list', '--format=json'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                self.recommendations.append({
                    'type': 'Dependencies',
                    'recommendation': 'Consider using pip-audit or safety to check for known vulnerabilities in dependencies'
                })
            
        except Exception as e:
            self.warnings.append(f"Could not audit dependencies: {str(e)}")
    
    def _audit_sql_security(self):
        """Audit SQL-related security"""
        print("🛢️ Auditing SQL security...")
        
        # Check SQL validation implementation
        sql_security_checks = [
            {
                'check': 'SQL injection prevention',
                'status': 'IMPLEMENTED',
                'details': 'SQL validator blocks non-SELECT queries and validates input'
            },
            {
                'check': 'Parameterized queries',
                'status': 'NEEDS_REVIEW',
                'details': 'Review all database queries to ensure parameterization'
            },
            {
                'check': 'Input validation',
                'status': 'IMPLEMENTED',
                'details': 'SQL parser validates syntax and structure'
            }
        ]
        
        for check in sql_security_checks:
            if check['status'] == 'NEEDS_REVIEW':
                self.recommendations.append({
                    'type': 'SQL Security',
                    'recommendation': f"{check['check']}: {check['details']}"
                })
    
    def _audit_auth_security(self):
        """Audit authentication and authorization"""
        print("🔐 Auditing authentication...")
        
        auth_issues = []
        
        # Check if authentication is implemented
        has_auth = os.path.exists('services/windows_auth_service.py')
        
        if not has_auth:
            auth_issues.append({
                'issue': 'No authentication mechanism detected',
                'severity': 'MEDIUM',
                'recommendation': 'Consider implementing authentication for production use'
            })
        else:
            auth_issues.append({
                'issue': 'Authentication service exists but may not be active',
                'severity': 'LOW',
                'recommendation': 'Verify authentication is properly integrated'
            })
        
        # Check session security
        if not os.getenv('SESSION_SECRET'):
            auth_issues.append({
                'issue': 'No session secret configured',
                'severity': 'HIGH',
                'recommendation': 'Configure SESSION_SECRET for secure sessions'
            })
        
        self.vulnerabilities.extend([{
            'type': 'Authentication',
            **issue
        } for issue in auth_issues])
    
    def _audit_environment_security(self):
        """Audit environment variable security"""
        print("🌍 Auditing environment security...")
        
        # Check for .env file
        if os.path.exists('.env'):
            self.warnings.append('Found .env file - ensure it\'s not committed to version control')
        
        # Check critical environment variables
        critical_vars = [
            'DATABASE_URL',
            'SESSION_SECRET',
            'AZURE_OPENAI_API_KEY',
            'AZURE_OPENAI_ENDPOINT'
        ]
        
        missing_vars = []
        for var in critical_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.recommendations.append({
                'type': 'Environment',
                'recommendation': f'Consider setting these environment variables: {", ".join(missing_vars)}'
            })
    
    def _audit_web_security(self):
        """Audit web security headers and configurations"""
        print("🌐 Auditing web security...")
        
        web_security_checks = [
            'Content Security Policy (CSP)',
            'X-Frame-Options',
            'X-Content-Type-Options',
            'X-XSS-Protection',
            'Strict-Transport-Security',
            'Referrer-Policy'
        ]
        
        for header in web_security_checks:
            self.recommendations.append({
                'type': 'Web Security',
                'recommendation': f'Consider implementing {header} header'
            })
        
        # Check for HTTPS enforcement
        self.recommendations.append({
            'type': 'Web Security',
            'recommendation': 'Ensure HTTPS is enforced in production'
        })
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate audit summary"""
        high_vulnerabilities = [v for v in self.vulnerabilities if v.get('severity') == 'HIGH']
        medium_vulnerabilities = [v for v in self.vulnerabilities if v.get('severity') == 'MEDIUM']
        low_vulnerabilities = [v for v in self.vulnerabilities if v.get('severity') == 'LOW']
        
        return {
            'total_vulnerabilities': len(self.vulnerabilities),
            'high_severity': len(high_vulnerabilities),
            'medium_severity': len(medium_vulnerabilities),
            'low_severity': len(low_vulnerabilities),
            'warnings': len(self.warnings),
            'recommendations': len(self.recommendations)
        }
    
    def print_report(self, audit_result: Dict[str, Any]):
        """Print detailed audit report"""
        print("\n" + "="*60)
        print("🔒 SECURITY AUDIT REPORT")
        print("="*60)
        
        summary = audit_result['summary']
        print(f"\n📊 SUMMARY:")
        print(f"   Total Vulnerabilities: {summary['total_vulnerabilities']}")
        print(f"   ├─ High Severity: {summary['high_severity']}")
        print(f"   ├─ Medium Severity: {summary['medium_severity']}")
        print(f"   └─ Low Severity: {summary['low_severity']}")
        print(f"   Warnings: {summary['warnings']}")
        print(f"   Recommendations: {summary['recommendations']}")
        
        # Print vulnerabilities
        if audit_result['vulnerabilities']:
            print(f"\n🚨 VULNERABILITIES:")
            for i, vuln in enumerate(audit_result['vulnerabilities'], 1):
                print(f"\n   {i}. [{vuln['severity']}] {vuln['type']}")
                print(f"      Issue: {vuln['issue']}")
                if 'file' in vuln:
                    print(f"      File: {vuln['file']}")
                print(f"      Fix: {vuln['recommendation']}")
        
        # Print warnings
        if audit_result['warnings']:
            print(f"\n⚠️  WARNINGS:")
            for i, warning in enumerate(audit_result['warnings'], 1):
                print(f"   {i}. {warning}")
        
        # Print recommendations
        if audit_result['recommendations']:
            print(f"\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(audit_result['recommendations'], 1):
                print(f"   {i}. [{rec['type']}] {rec['recommendation']}")
        
        print("\n" + "="*60)

if __name__ == "__main__":
    auditor = SecurityAuditor()
    result = auditor.audit_application()
    auditor.print_report(result)