# Natural Language to SQL Converter

A secure Flask web application that converts natural language descriptions into optimized SQL Server queries using Azure OpenAI services.

## Features

- **Natural Language Processing**: Convert plain English to SQL queries using Azure OpenAI
- **Security First**: SELECT-only queries with comprehensive SQL injection protection
- **Schema Management**: Upload and analyze database schemas with AI-powered descriptions
- **Multi-Database Support**: Works with SQL Server, PostgreSQL, MySQL
- **Real-time Validation**: SQL syntax checking and optimization suggestions
- **Query History**: Track and review past conversions

## Security

This application implements multiple security layers:
- SQL injection prevention with parameterized queries
- SELECT-only query enforcement
- Input validation and sanitization
- Secure session management
- Identifier validation for table/column names

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd natural-language-sql
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**
   ```bash
   export SESSION_SECRET="your-secure-session-secret"
   export DATABASE_URL="your-database-url"
   export AZURE_OPENAI_ENDPOINT="your-azure-endpoint"
   export AZURE_OPENAI_API_KEY="your-api-key"
   export AZURE_OPENAI_DEPLOYMENT_NAME="your-deployment"
   ```

4. **Run the application**
   ```bash
   gunicorn --bind 0.0.0.0:5000 main:app
   ```

5. **Access the application**
   Open your browser to `http://localhost:5000`

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SESSION_SECRET` | Secure session encryption key | Yes |
| `DATABASE_URL` | Application database connection | Yes |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI service endpoint | Optional* |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | Optional* |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Model deployment name | Optional* |

*If Azure OpenAI credentials are not provided, the application uses a fallback service for demonstration.

## Architecture

- **Backend**: Flask with SQLAlchemy ORM
- **Frontend**: Bootstrap 5 with dark theme
- **AI Service**: Azure OpenAI for natural language processing
- **Database**: PostgreSQL (configurable)
- **Security**: Multi-layer validation and sanitization

## Security Audit

The application has undergone comprehensive security testing:
- **Risk Level**: LOW (suitable for production with authentication)
- **High Priority Issues**: 0 (all resolved)
- **SQL Injection Protection**: Comprehensive
- **Session Security**: Secure with proper secret management

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions, please use the GitHub issue tracker.