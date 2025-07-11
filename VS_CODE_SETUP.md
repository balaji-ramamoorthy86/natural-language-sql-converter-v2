# Running the Natural Language to SQL Converter in VS Code

## Prerequisites

1. **Install VS Code**: Download from [code.visualstudio.com](https://code.visualstudio.com/)
2. **Install Python Extension**: Install the official Python extension by Microsoft
3. **Python 3.11+**: Ensure Python 3.11 or higher is installed on your system

## Project Setup

### 1. Clone the Repository
```bash
git clone https://github.com/balaji-ramamoorthy86/natural-language-sql-converter-v2.git
cd natural-language-sql-converter-v2
```

### 2. Open in VS Code
```bash
code .
```
Or open VS Code and use `File > Open Folder` to select the project directory.

### 3. Set Up Python Environment

#### Option A: Using Python venv (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies (try methods in order)

# Method 1: Using pyproject.toml (after fixing the layout issue)
pip install -e .

# Method 2: If above fails, install all at once
pip install azure-ai-inference azure-core email-validator flask flask-sqlalchemy gunicorn openai psycopg2-binary pyodbc requests sqlalchemy sqlparse werkzeug

# Method 3: Core packages only (if you get dependency conflicts)
pip install flask flask-sqlalchemy requests sqlalchemy sqlparse werkzeug gunicorn

# Method 4: Install one by one (if bulk install fails)
pip install flask
pip install flask-sqlalchemy
pip install requests
pip install sqlalchemy
pip install sqlparse
pip install werkzeug
pip install gunicorn
```

#### Option B: Using Poetry (if you prefer)
```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### 4. Configure Environment Variables

The project includes a `.env` file with default settings. You can customize it for your needs:

```bash
# The .env file is already present with these default settings:
DATABASE_URL=sqlite:///app.db
SESSION_SECRET=change-this-to-a-secure-random-string-for-production-use
FLASK_ENV=development
FLASK_DEBUG=1

# Optional: Add Azure OpenAI credentials for enhanced functionality
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
# AZURE_OPENAI_API_KEY=your-azure-openai-api-key
# AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
```

**Important**: Change the `SESSION_SECRET` to a secure random string in production!

## Running the Application

### Method 1: Using VS Code Debugger (Recommended)

1. **Select Python Interpreter**:
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
   - Type "Python: Select Interpreter"
   - Choose the interpreter from your virtual environment

2. **Start Debugging**:
   - Press `F5` or go to `Run > Start Debugging`
   - Select "Python: Flask App" from the configuration dropdown
   - The app will start with debugging enabled

3. **Access the Application**:
   - Open your browser and go to `http://localhost:5000`
   - The app will be running with full debugging capabilities

### Method 2: Using Integrated Terminal

1. **Open Terminal in VS Code**: `Ctrl+`` (backtick)
2. **Activate Virtual Environment** (if not already active):
   ```bash
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```
3. **Run the Application**:
   ```bash
   python main.py
   ```
   Or using Flask command:
   ```bash
   flask run --debug
   ```

### Method 3: Using Gunicorn (Production-like)

```bash
gunicorn --bind 0.0.0.0:5000 --reload main:app
```

## Debugging Features

### Available Debug Configurations

The project includes 4 pre-configured debug options:

1. **Python: Flask App** - Main application debugging
2. **Python: Current File** - Debug any open Python file
3. **Python: Security Audit** - Run security analysis
4. **Python: Upload to GitHub** - Debug GitHub integration

### Setting Breakpoints

1. Click in the left margin next to line numbers to set breakpoints
2. Use conditional breakpoints by right-clicking on a breakpoint
3. The debugger will pause execution at breakpoints for inspection

### Debug Console

- Access variables and execute Python code while debugging
- Use the debug console to test functions and inspect state
- Available in the bottom panel when debugging is active

## Development Workflow

### 1. File Structure Overview
```
natural-language-sql-converter-v2/
├── app.py                 # Flask application setup
├── main.py               # Application entry point
├── models.py             # Database models
├── services/             # Business logic services
│   ├── azure_openai_service.py
│   ├── sql_validator.py
│   ├── schema_service.py
│   └── ...
├── templates/            # HTML templates
├── static/              # CSS, JS, images
├── .vscode/             # VS Code configuration
│   └── launch.json      # Debug configurations
└── requirements.txt     # Python dependencies
```

### 2. Key Development Tasks

#### Making Code Changes
- Edit files in VS Code with full IntelliSense support
- The Flask development server auto-reloads when files change
- Use the debugger to step through your changes

#### Running Tests
```bash
# Security audit
python security_audit.py

# Manual testing of API endpoints
curl -X POST http://localhost:5000/convert \
  -H "Content-Type: application/json" \
  -d '{"natural_language": "show all users", "schema_context": ""}'
```

#### Database Operations
```bash
# Access Python shell with app context
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

## Troubleshooting

### Common Issues

1. **Pip install errors**:
   - **"Multiple top-level packages discovered in a flat-layout"**: Fixed in latest pyproject.toml - try `pip install -e .` again
   - **"No module named 'pip'"**: Reinstall pip: `python -m ensurepip --upgrade`
   - **Permission denied**: Use `pip install --user` or run as administrator
   - **SSL errors**: Try `pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org <package>`
   - **Dependency conflicts**: Use Method 3 (core packages only) from above
   - **pyodbc errors on Windows**: Install Microsoft Visual C++ Build Tools
   - **psycopg2 errors**: Try `pip install psycopg2-binary` instead

2. **"Module not found" errors**:
   - Ensure virtual environment is activated
   - Check that dependencies are installed: `pip list`
   - Try: `python -m pip install <missing-package>`

3. **Port already in use**:
   - Kill existing processes: `pkill -f python` or `taskkill /f /im python.exe`
   - Use a different port: `flask run --port 5001`

4. **Database errors**:
   - Delete the database file and restart: `rm app.db`
   - Check DATABASE_URL environment variable

5. **Permission errors**:
   - Ensure you have write permissions in the project directory
   - Check file ownership and permissions

### VS Code Extensions (Recommended)

- **Python** (Microsoft) - Essential for Python development
- **Pylance** (Microsoft) - Advanced Python language support
- **Python Docstring Generator** - Auto-generate docstrings
- **GitLens** - Enhanced Git capabilities
- **Thunder Client** - API testing within VS Code

## Production Deployment

### Preparing for Production
1. Set secure environment variables
2. Use a production WSGI server (Gunicorn is already configured)
3. Set up proper database (PostgreSQL recommended)
4. Configure reverse proxy (Nginx)

### Environment Variables for Production
```bash
# Use strong session secret
SESSION_SECRET=very-long-random-string-minimum-32-characters

# Production database
DATABASE_URL=postgresql://user:password@host:port/database

# Azure OpenAI for production
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-production-api-key
```

## Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/balaji-ramamoorthy86/natural-language-sql-converter-v2/issues)
- **Documentation**: Check the project README.md for additional details
- **Security**: Review SECURITY_REPORT.md for security considerations

---

**Happy Coding!** The VS Code setup provides a complete development environment with debugging, IntelliSense, and integrated terminal support for efficient development of the Natural Language to SQL Converter.