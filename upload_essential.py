#!/usr/bin/env python3
"""
Upload essential project files to GitHub repository
"""
import os
import base64
import requests

def upload_essential_files():
    """Upload only essential project files to GitHub"""
    
    token = os.environ.get('GITHUB_TOKEN')
    repo_owner = 'balaji-ramamoorthy86'
    repo_name = 'natural-language-sql-converter-v2'
    
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
    }
    
    # Essential files to upload
    essential_files = [
        'app.py',
        'main.py', 
        'models.py',
        'replit.md',
        'README.md',
        'SECURITY_REPORT.md',
        'security_audit.py',
        'pyproject.toml',
        'services/azure_openai_service.py',
        'services/connection_api_service.py',
        'services/schema_analyzer.py',
        'services/schema_service.py',
        'services/sql_validator.py',
        'services/sqlserver_service.py',
        'services/windows_auth_service.py',
        'templates/base.html',
        'templates/index.html',
        'static/css/custom.css',
        'static/js/app.js'
    ]
    
    uploaded_count = 0
    
    for file_path in essential_files:
        if not os.path.exists(file_path):
            print(f"⚠ File not found: {file_path}")
            continue
            
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            encoded_content = base64.b64encode(content).decode('utf-8')
            
            # Check if file exists and get its SHA
            url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}'
            get_response = requests.get(url, headers=headers)
            
            file_data = {
                'message': f'Update {file_path}',
                'content': encoded_content
            }
            
            # If file exists, include the SHA for update
            if get_response.status_code == 200:
                existing_file = get_response.json()
                file_data['sha'] = existing_file['sha']
                file_data['message'] = f'Update {file_path}'
            else:
                file_data['message'] = f'Add {file_path}'
            
            response = requests.put(url, headers=headers, json=file_data)
            
            if response.status_code in [201, 200]:
                print(f"✓ Uploaded: {file_path}")
                uploaded_count += 1
            else:
                print(f"✗ Failed: {file_path} ({response.status_code})")
                try:
                    error_detail = response.json()
                    print(f"  Error: {error_detail.get('message', 'Unknown error')}")
                except:
                    print(f"  Raw response: {response.text[:200]}")
                
        except Exception as e:
            print(f"✗ Error uploading {file_path}: {str(e)}")
    
    print(f"\nUploaded {uploaded_count}/{len(essential_files)} essential files")
    return uploaded_count > 0

if __name__ == '__main__':
    success = upload_essential_files()
    if success:
        print("\n🎉 Essential files uploaded successfully!")
        print("Repository: https://github.com/balaji-ramamoorthy86/natural-language-sql-converter-v2")