#!/usr/bin/env python3
"""
Convert SQL schema extraction results to JSON format
Usage: python sql_to_json_converter.py schema_data.csv output_schema_name
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

def convert_sql_results_to_json(csv_file, schema_name):
    """Convert SQL schema extraction results to JSON format"""
    
    schema_data = {
        "schema_name": schema_name,
        "description": f"Database schema for {schema_name}",
        "tables": {}
    }
    
    # Read the CSV file with schema information
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            table_name = row['table_name']
            
            # Initialize table if not exists
            if table_name not in schema_data['tables']:
                schema_data['tables'][table_name] = {
                    "description": f"Table: {table_name}",
                    "columns": {}
                }
            
            # Add column information
            column_name = row['column_name']
            schema_data['tables'][table_name]['columns'][column_name] = {
                "type": row['full_data_type'],
                "nullable": row['is_nullable'].lower() == 'true',
                "primary_key": row['is_primary_key'].lower() == 'true',
                "description": f"{column_name} column"
            }
            
            # Add foreign key if exists
            if row.get('referenced_table') and row.get('referenced_column'):
                schema_data['tables'][table_name]['columns'][column_name]['foreign_key'] = {
                    "table": row['referenced_table'],
                    "column": row['referenced_column']
                }
    
    return schema_data

def create_json_from_manual_input():
    """Interactive JSON creation for manual input"""
    
    schema_name = input("Enter schema name: ").strip()
    if not schema_name:
        print("Schema name is required!")
        return
    
    schema_data = {
        "schema_name": schema_name,
        "description": f"Database schema for {schema_name}",
        "tables": {}
    }
    
    print(f"\nCreating schema: {schema_name}")
    print("Enter table information (press Enter with empty table name to finish)")
    
    while True:
        table_name = input("\nTable name: ").strip()
        if not table_name:
            break
        
        table_desc = input(f"Table description (optional): ").strip()
        if not table_desc:
            table_desc = f"Table: {table_name}"
        
        schema_data['tables'][table_name] = {
            "description": table_desc,
            "columns": {}
        }
        
        print(f"Adding columns for table '{table_name}' (press Enter with empty column name to finish)")
        
        while True:
            col_name = input("  Column name: ").strip()
            if not col_name:
                break
            
            col_type = input(f"  Data type for {col_name}: ").strip()
            if not col_type:
                col_type = "varchar(255)"
            
            nullable = input(f"  Nullable? (y/n, default=y): ").strip().lower()
            is_nullable = nullable != 'n'
            
            primary_key = input(f"  Primary key? (y/n, default=n): ").strip().lower()
            is_primary = primary_key == 'y'
            
            col_desc = input(f"  Description for {col_name} (optional): ").strip()
            if not col_desc:
                col_desc = f"{col_name} column"
            
            schema_data['tables'][table_name]['columns'][col_name] = {
                "type": col_type,
                "nullable": is_nullable,
                "primary_key": is_primary,
                "description": col_desc
            }
            
            # Ask about foreign key
            fk = input(f"  Foreign key? (y/n, default=n): ").strip().lower()
            if fk == 'y':
                ref_table = input(f"    Referenced table: ").strip()
                ref_column = input(f"    Referenced column: ").strip()
                if ref_table and ref_column:
                    schema_data['tables'][table_name]['columns'][col_name]['foreign_key'] = {
                        "table": ref_table,
                        "column": ref_column
                    }
    
    # Save to JSON file
    output_file = f"services/schemas/{schema_name}.json"
    Path("services/schemas").mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(schema_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ JSON schema saved to: {output_file}")
    print(f"✓ Schema '{schema_name}' will automatically appear in the dropdown")

def main():
    if len(sys.argv) == 1:
        print("JSON Schema Creator")
        print("=" * 50)
        print("1. Convert from CSV file (from SQL extraction)")
        print("2. Create manually (interactive)")
        
        choice = input("\nChoose option (1 or 2): ").strip()
        
        if choice == "1":
            csv_file = input("Enter CSV file path: ").strip()
            schema_name = input("Enter schema name: ").strip()
            
            if not csv_file or not schema_name:
                print("Both CSV file and schema name are required!")
                return
            
            try:
                schema_data = convert_sql_results_to_json(csv_file, schema_name)
                output_file = f"services/schemas/{schema_name}.json"
                Path("services/schemas").mkdir(exist_ok=True)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(schema_data, f, indent=2, ensure_ascii=False)
                
                print(f"\n✓ JSON schema saved to: {output_file}")
                print(f"✓ Schema '{schema_name}' will automatically appear in the dropdown")
                
            except Exception as e:
                print(f"Error: {str(e)}")
        
        elif choice == "2":
            create_json_from_manual_input()
        
        else:
            print("Invalid choice!")
    
    elif len(sys.argv) == 3:
        csv_file, schema_name = sys.argv[1], sys.argv[2]
        schema_data = convert_sql_results_to_json(csv_file, schema_name)
        
        output_file = f"services/schemas/{schema_name}.json"
        Path("services/schemas").mkdir(exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(schema_data, f, indent=2, ensure_ascii=False)
        
        print(f"JSON schema saved to: {output_file}")
    
    else:
        print("Usage: python sql_to_json_converter.py [csv_file schema_name]")
        print("Or run without arguments for interactive mode")

if __name__ == "__main__":
    main()