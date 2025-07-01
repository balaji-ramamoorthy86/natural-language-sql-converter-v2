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
- **Framework**: Flask with lightweight in-memory storage
- **Pattern**: Service-oriented architecture with dedicated service classes
- **Storage**: In-memory storage for query history (resets on restart)
- **AI Integration**: Azure OpenAI API for natural language processing

## Key Components

### Core Services
1. **AzureOpenAIService** (`services/azure_openai_service.py`)
   - Handles communication with Azure OpenAI API
   - Generates SQL queries from natural language input
   - Includes fallback mechanisms for different OpenAI libraries

2. **SchemaService** (`services/schema_service.py`)
   - Manages database schema information from JSON files
   - Dynamically loads schemas from `services/schemas/` directory
   - Each JSON file automatically creates a dropdown option
   - Supports both JSON file-based and live SQL Server schema discovery

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

### Data Storage
1. **Query History** - Stored in-memory during runtime, resets on application restart
2. **Schema Definitions** - Persistent JSON files in `services/schemas/` directory

### Schema Management
- **JSON-based Schema Storage**: Schemas stored in `services/schemas/` directory
- **Dynamic Discovery**: Each `.json` file automatically appears in dropdown
- **No Hardcoded Data**: All schema definitions externalized to JSON files
- **Template System**: Includes template and example schemas for reference

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
- Azure OpenAI credentials via environment variables
- Session secret configurable for production security
- No database setup required - uses in-memory storage

### Production Considerations
- Lightweight deployment with minimal dependencies
- ProxyFix middleware for proper header handling behind proxies
- Query history resets on application restart (stateless design)

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
- July 1, 2025. Fixed critical application stability issues:
  - Resolved fallback SQL generation service causing mixed success/error messages
  - Fixed undefined variable errors in Azure OpenAI service fallback implementation
  - Implemented comprehensive cache-busting for CSS/JavaScript files to prevent 304 status codes
  - Added proper Flask cache control configuration for development environment
  - Application now successfully generates SQL queries without showing concurrent errors
- July 1, 2025. Implemented JSON-based schema management system:
  - Replaced hardcoded schema definitions with external JSON files
  - Created dynamic schema discovery from services/schemas/ directory
  - Each JSON file automatically creates dropdown option without code changes
  - Added comprehensive documentation and template files for schema format
  - Simplified schema addition process - just add JSON file to schemas directory
- July 1, 2025. Completed automated schema saving workflow:
  - "Analyze Database" button now automatically converts AI analysis to JSON format
  - Schemas are automatically saved to services/schemas/ directory with proper naming
  - New schemas immediately appear in dropdown without restart required
  - Added user notifications and confirmation messages for automatic saving
  - Project committed to GitHub repository with all completed features
- July 1, 2025. Migrated from PostgreSQL to in-memory storage:
  - Removed PostgreSQL and SQLAlchemy dependencies for simplified deployment
  - Implemented lightweight in-memory storage for query history
  - Removed database models and migrations - now stateless architecture
  - Query history resets on application restart but retains functionality during runtime
  - Significantly reduced deployment complexity and resource requirements
- July 1, 2025. Enhanced AI Schema Analyzer with authentication options and UI improvements:
  - Added SQL Server Authentication and Windows Authentication dropdown options
  - Implemented Test Connection button to verify database connectivity before analysis
  - Updated JavaScript to handle authentication type switching and form validation
  - Added backend /test-connection endpoint for connection verification
  - Fixed AI Analysis Results section visibility issues with improved contrast and styling
  - Enhanced modal headers and form styling for better user experience
- July 1, 2025. Implemented comprehensive query feedback loop system:
  - Created QueryFeedbackService for real-time query quality analysis
  - Added automated scoring system: syntax (100%), semantic alignment (100%), performance (100%), security (100%)
  - Integrated user rating system with interactive 5-star interface
  - Built detailed feedback modal with actionable recommendations and execution results
  - Added automatic feedback analysis for every generated SQL query
  - Fixed loading progress bar visibility issues with enhanced state management
  - All feedback data stored in-memory for runtime analysis and improvement recommendations

## User Preferences

Preferred communication style: Simple, everyday language.