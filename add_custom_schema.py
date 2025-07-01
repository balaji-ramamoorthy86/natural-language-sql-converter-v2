#!/usr/bin/env python3
"""
Script to manually add a custom database schema to the application
Usage: python add_custom_schema.py
"""

import os
import sys
from app import app, db
from models import DatabaseSchema

def add_custom_schema():
    """Add a custom database schema to the application"""
    
    # Example: Adding a custom "inventory" schema
    custom_schema_data = [
        # Products table
        {
            'schema_name': 'inventory',
            'table_name': 'products',
            'column_name': 'product_id',
            'data_type': 'int',
            'is_nullable': False,
            'is_primary_key': True,
            'column_description': 'Unique product identifier'
        },
        {
            'schema_name': 'inventory',
            'table_name': 'products',
            'column_name': 'product_name',
            'data_type': 'varchar(255)',
            'is_nullable': False,
            'column_description': 'Product name'
        },
        {
            'schema_name': 'inventory',
            'table_name': 'products',
            'column_name': 'sku',
            'data_type': 'varchar(50)',
            'is_nullable': False,
            'column_description': 'Stock keeping unit'
        },
        {
            'schema_name': 'inventory',
            'table_name': 'products',
            'column_name': 'quantity_on_hand',
            'data_type': 'int',
            'is_nullable': False,
            'column_description': 'Current stock quantity'
        },
        {
            'schema_name': 'inventory',
            'table_name': 'products',
            'column_name': 'unit_cost',
            'data_type': 'decimal(10,2)',
            'is_nullable': False,
            'column_description': 'Cost per unit'
        },
        
        # Warehouses table
        {
            'schema_name': 'inventory',
            'table_name': 'warehouses',
            'column_name': 'warehouse_id',
            'data_type': 'int',
            'is_nullable': False,
            'is_primary_key': True,
            'column_description': 'Unique warehouse identifier'
        },
        {
            'schema_name': 'inventory',
            'table_name': 'warehouses',
            'column_name': 'warehouse_name',
            'data_type': 'varchar(100)',
            'is_nullable': False,
            'column_description': 'Warehouse name'
        },
        {
            'schema_name': 'inventory',
            'table_name': 'warehouses',
            'column_name': 'location',
            'data_type': 'varchar(255)',
            'is_nullable': False,
            'column_description': 'Warehouse location'
        },
        
        # Stock_movements table
        {
            'schema_name': 'inventory',
            'table_name': 'stock_movements',
            'column_name': 'movement_id',
            'data_type': 'int',
            'is_nullable': False,
            'is_primary_key': True,
            'column_description': 'Unique movement identifier'
        },
        {
            'schema_name': 'inventory',
            'table_name': 'stock_movements',
            'column_name': 'product_id',
            'data_type': 'int',
            'is_nullable': False,
            'is_foreign_key': True,
            'referenced_table': 'products',
            'referenced_column': 'product_id',
            'column_description': 'Product reference'
        },
        {
            'schema_name': 'inventory',
            'table_name': 'stock_movements',
            'column_name': 'warehouse_id',
            'data_type': 'int',
            'is_nullable': False,
            'is_foreign_key': True,
            'referenced_table': 'warehouses',
            'referenced_column': 'warehouse_id',
            'column_description': 'Warehouse reference'
        },
        {
            'schema_name': 'inventory',
            'table_name': 'stock_movements',
            'column_name': 'movement_type',
            'data_type': 'varchar(20)',
            'is_nullable': False,
            'column_description': 'Type of movement (IN/OUT/TRANSFER)'
        },
        {
            'schema_name': 'inventory',
            'table_name': 'stock_movements',
            'column_name': 'quantity',
            'data_type': 'int',
            'is_nullable': False,
            'column_description': 'Quantity moved'
        },
        {
            'schema_name': 'inventory',
            'table_name': 'stock_movements',
            'column_name': 'movement_date',
            'data_type': 'datetime',
            'is_nullable': False,
            'column_description': 'Date of movement'
        }
    ]
    
    with app.app_context():
        try:
            # Check if schema already exists
            existing = DatabaseSchema.query.filter_by(schema_name='inventory').first()
            if existing:
                print("Schema 'inventory' already exists!")
                return
            
            # Add all schema entries
            for schema_data in custom_schema_data:
                schema_entry = DatabaseSchema(**schema_data)
                db.session.add(schema_entry)
            
            db.session.commit()
            print("✓ Custom 'inventory' schema added successfully!")
            print("  - Tables: products, warehouses, stock_movements")
            print("  - The schema will now appear in the dropdown")
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error adding schema: {str(e)}")

if __name__ == "__main__":
    add_custom_schema()