# Natural Language to SQL Converter

## Overview

This is a Flask-based web application that converts natural language descriptions into SQL Server queries using Azure OpenAI. The application provides an intuitive interface for users to input natural language requests and receive optimized, validated SQL queries in return.

## System Architecture

The application follows a layered architecture pattern with clear separation of concerns:

### Frontend Architecture
- **Technology**: HTML5, Bootstrap 5 (dark theme), JavaScript ES6, Prism.js for syntax highlighting
- **Design**: Responsive single-page application with modal dialogs
- **Styling**: Custom CSS with Bootstrap framework for consistent dark theme experience

### Backend Architecture
- **Framework**: Flask with SQLAlchemy ORM
- **Pattern**: Service-oriented architecture with dedicated service classes
- **Database**: SQLite for development (configurable to other databases via DATABASE_URL)
- **AI Integration**: Azure OpenAI API for natural language processing

## Key Components

### Core Services
1. **AzureOpenAIService** (`services/azure_openai_service.py`)
   - Handles communication with Azure OpenAI API
   - Generates SQL queries from natural language input
   - Includes fallback mechanisms for different OpenAI libraries

2. **SchemaService** (`services/schema_service.py`)
   - Manages database schema information
   - Provides context for SQL generation
   - Includes sample e-commerce schema for demonstration

3. **SQLValidator** (`services/sql_validator.py`)
   - Validates generated SQL queries
   - Optimizes query performance
   - Performs security checks for SQL injection patterns

4. **SQLServerService** (`services/sqlserver_service.py`)
   - Manages on-premises SQL Server connections
   - Provides database discovery and schema extraction
   - Handles multiple authentication methods (SQL, Windows, Azure AD)
   - Includes SQL Server-specific optimizations and validations

5. **ConnectionAPIService** (`services/connection_api_service.py`)
   - Fetches database connection strings from external configuration API
   - Manages database selection workflow without exposing connection details
   - Provides demo database configurations for testing
   - Handles API authentication and error management

### Data Models
1. **QueryHistory** - Stores conversion history and results
2. **DatabaseSchema** - Maintains database schema metadata
3. **UserFeedback** - Collects user ratings and feedback

### Frontend Components
- Interactive form for natural language input
- Schema context selection
- Real-time SQL syntax highlighting
- Query history management
- Loading states and error handling
- Database selection interface with API-driven connection management
- Automatic schema loading from selected databases

## Data Flow

1. User enters natural language description
2. Optional schema context is selected
3. Request sent to Flask backend
4. AzureOpenAIService processes the request
5. Generated SQL is validated and optimized
6. Results stored in QueryHistory
7. Formatted response returned to frontend
8. SQL displayed with syntax highlighting

## External Dependencies

### AI Services
- **Azure OpenAI**: Primary AI service for natural language processing
- **Configuration**: Requires AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and deployment settings

### Database Dependencies
- **SQLAlchemy**: ORM for database operations
- **pyodbc**: SQL Server connectivity (optional)
- **sqlparse**: SQL parsing and validation

### Frontend Libraries
- **Bootstrap 5**: UI framework with dark theme
- **Prism.js**: Syntax highlighting for SQL
- **Font Awesome**: Icon library

## Deployment Strategy

### Environment Configuration
- Database URL configurable via `DATABASE_URL` environment variable
- Azure OpenAI credentials via environment variables
- Session secret configurable for production security

### Production Considerations
- SQLite for development, easily configurable for PostgreSQL/SQL Server
- ProxyFix middleware for proper header handling behind proxies
- Connection pooling and ping mechanisms for database reliability

### Security Features
- SQL injection pattern detection
- Input validation and sanitization
- Secure session management
- Reserved keyword handling

## Changelog

- June 30, 2025. Initial setup
- June 30, 2025. Implemented critical security fixes:
  - Fixed session secret configuration (no fallback allowed)
  - Enhanced SQL query parameterization in schema analyzer
  - Added identifier validation and SQL injection protection
  - Updated security audit showing LOW risk level
- June 30, 2025. Added comprehensive on-premises SQL Server support:
  - Full connection management with multiple authentication methods
  - Database discovery and schema extraction
  - SQL Server-specific query validation and optimization
  - Integrated frontend interface for connection management
- June 30, 2025. Implemented API-based database connection management:
  - Replaced manual connection forms with database selection interface
  - Added ConnectionAPIService for fetching connection strings from external API
  - Users select databases from dropdown, connection details retrieved automatically
  - Maintains security by not exposing connection credentials in the interface

## User Preferences

Preferred communication style: Simple, everyday language.