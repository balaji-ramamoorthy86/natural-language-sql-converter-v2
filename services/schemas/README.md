# Database Schema JSON Files

This directory contains JSON files that define database schemas for the Natural Language to SQL converter. Each JSON file automatically creates a corresponding option in the schema dropdown.

## How It Works

1. **Automatic Discovery**: The application automatically scans this directory for `.json` files
2. **Dynamic Dropdown**: Each JSON file creates a dropdown option (filename without extension)
3. **No Hardcoding**: No need to modify code to add new schemas
4. **Easy Management**: Simply add, remove, or edit JSON files to manage schemas

## JSON Schema Format

Each JSON file must follow this structure:

```json
{
  "schema_name": "your_schema_name",
  "description": "Description of your database schema",
  "tables": {
    "table_name": {
      "description": "Description of this table",
      "columns": {
        "column_name": {
          "type": "data_type",
          "nullable": true/false,
          "primary_key": true/false,
          "description": "Column description",
          "foreign_key": {
            "table": "referenced_table",
            "column": "referenced_column"
          }
        }
      }
    }
  }
}
```

## Supported Data Types

- `int` - Integer numbers
- `varchar(n)` - Variable length text (n = max length)
- `text` - Large text fields
- `decimal(p,s)` - Decimal numbers (p = precision, s = scale)
- `datetime` - Date and time
- `date` - Date only
- `bit` - Boolean values
- `float` - Floating point numbers

## Column Properties

- **type**: Required. The SQL data type
- **nullable**: Optional. Default is `true`
- **primary_key**: Optional. Default is `false`
- **description**: Optional. Column description for AI context
- **foreign_key**: Optional. Object with `table` and `column` properties

## Examples

### Simple Table
```json
{
  "schema_name": "simple",
  "description": "Simple database example",
  "tables": {
    "users": {
      "description": "User accounts",
      "columns": {
        "id": {
          "type": "int",
          "nullable": false,
          "primary_key": true,
          "description": "User ID"
        },
        "name": {
          "type": "varchar(100)",
          "nullable": false,
          "description": "User name"
        },
        "email": {
          "type": "varchar(255)",
          "nullable": false,
          "description": "Email address"
        }
      }
    }
  }
}
```

### With Foreign Keys
```json
{
  "schema_name": "blog",
  "description": "Blog database schema",
  "tables": {
    "authors": {
      "description": "Blog authors",
      "columns": {
        "id": {
          "type": "int",
          "nullable": false,
          "primary_key": true,
          "description": "Author ID"
        },
        "name": {
          "type": "varchar(100)",
          "nullable": false,
          "description": "Author name"
        }
      }
    },
    "posts": {
      "description": "Blog posts",
      "columns": {
        "id": {
          "type": "int",
          "nullable": false,
          "primary_key": true,
          "description": "Post ID"
        },
        "title": {
          "type": "varchar(200)",
          "nullable": false,
          "description": "Post title"
        },
        "content": {
          "type": "text",
          "nullable": false,
          "description": "Post content"
        },
        "author_id": {
          "type": "int",
          "nullable": false,
          "foreign_key": {
            "table": "authors",
            "column": "id"
          },
          "description": "Reference to author"
        }
      }
    }
  }
}
```

## Adding New Schemas

To add a new database schema:

1. Create a new `.json` file in this directory
2. Follow the JSON format above
3. Save the file with a descriptive name (e.g., `inventory.json`)
4. The schema will automatically appear in the dropdown

## Existing Schemas

- **ecommerce.json**: E-commerce database with customers, products, orders
- **inventory.json**: Inventory management with products, warehouses, stock movements
- **financial.json**: Financial system with accounts, transactions, invoices
- **template.json**: Template showing all supported features and data types

## Tips

1. **Clear Descriptions**: Good column descriptions help the AI generate better SQL
2. **Consistent Naming**: Use consistent naming conventions across your schema
3. **Foreign Keys**: Always define foreign key relationships for better query generation
4. **Data Types**: Choose appropriate data types for better SQL optimization
5. **Validation**: The application validates JSON format and required fields

## Troubleshooting

- **Schema not appearing**: Check JSON syntax and ensure file has `.json` extension
- **Invalid format**: Ensure required fields (`schema_name`, `tables`) are present
- **Caching**: Restart the application or refresh schema cache if changes don't appear

## Live Database Integration

The system also supports connecting to live SQL Server databases through environment variables:
- `SQL_SERVER_HOST`
- `SQL_SERVER_USERNAME`
- `SQL_SERVER_PASSWORD`
- `SQL_SERVER_DATABASE`

When configured, live schemas take precedence over JSON files.