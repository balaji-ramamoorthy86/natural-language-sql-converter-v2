#!/usr/bin/env python3
"""
Generate a basic JSON schema template for manual completion
"""

def generate_template(schema_name, table_names):
    """Generate a basic template with specified tables"""
    
    template = {
        "schema_name": schema_name,
        "description": f"Database schema for {schema_name}",
        "tables": {}
    }
    
    for table_name in table_names:
        template["tables"][table_name] = {
            "description": f"TODO: Add description for {table_name} table",
            "columns": {
                "id": {
                    "type": "int",
                    "nullable": False,
                    "primary_key": True,
                    "description": "Primary key identifier"
                },
                "name": {
                    "type": "varchar(255)",
                    "nullable": False,
                    "description": "TODO: Add column description"
                },
                "created_at": {
                    "type": "datetime",
                    "nullable": False,
                    "description": "Record creation timestamp"
                }
            }
        }
    
    return template

# Example usage
if __name__ == "__main__":
    import json
    
    # Create template for common business tables
    schema_name = "my_business_db"
    tables = ["customers", "products", "orders", "employees"]
    
    template = generate_template(schema_name, tables)
    
    # Save template
    with open(f"services/schemas/{schema_name}_template.json", "w") as f:
        json.dump(template, f, indent=2)
    
    print(f"Template created: services/schemas/{schema_name}_template.json")
    print("Edit the file to match your actual database structure.")