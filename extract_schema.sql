-- SQL Server Schema Extraction Script
-- Run this on your SQL Server database to get schema information

-- Get all tables and columns with detailed information
SELECT 
    t.TABLE_SCHEMA as schema_name,
    t.TABLE_NAME as table_name,
    c.COLUMN_NAME as column_name,
    c.DATA_TYPE as data_type,
    CASE 
        WHEN c.CHARACTER_MAXIMUM_LENGTH IS NOT NULL 
        THEN c.DATA_TYPE + '(' + CAST(c.CHARACTER_MAXIMUM_LENGTH AS VARCHAR) + ')'
        WHEN c.NUMERIC_PRECISION IS NOT NULL AND c.NUMERIC_SCALE IS NOT NULL
        THEN c.DATA_TYPE + '(' + CAST(c.NUMERIC_PRECISION AS VARCHAR) + ',' + CAST(c.NUMERIC_SCALE AS VARCHAR) + ')'
        ELSE c.DATA_TYPE
    END as full_data_type,
    CASE WHEN c.IS_NULLABLE = 'YES' THEN 'true' ELSE 'false' END as is_nullable,
    CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 'true' ELSE 'false' END as is_primary_key,
    fk.REFERENCED_TABLE_NAME as referenced_table,
    fk.REFERENCED_COLUMN_NAME as referenced_column,
    c.COLUMN_DEFAULT as default_value,
    c.ORDINAL_POSITION as column_order
FROM INFORMATION_SCHEMA.TABLES t
INNER JOIN INFORMATION_SCHEMA.COLUMNS c ON t.TABLE_NAME = c.TABLE_NAME
LEFT JOIN (
    SELECT 
        ku.TABLE_NAME,
        ku.COLUMN_NAME
    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS AS tc
    INNER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE AS ku
        ON tc.CONSTRAINT_TYPE = 'PRIMARY KEY' 
        AND tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
) pk ON c.TABLE_NAME = pk.TABLE_NAME AND c.COLUMN_NAME = pk.COLUMN_NAME
LEFT JOIN (
    SELECT 
        ku.TABLE_NAME,
        ku.COLUMN_NAME,
        ku.REFERENCED_TABLE_NAME,
        ku.REFERENCED_COLUMN_NAME
    FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS AS rc
    INNER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE AS ku
        ON rc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
) fk ON c.TABLE_NAME = fk.TABLE_NAME AND c.COLUMN_NAME = fk.COLUMN_NAME
WHERE t.TABLE_TYPE = 'BASE TABLE'
    AND t.TABLE_SCHEMA NOT IN ('sys', 'INFORMATION_SCHEMA')
ORDER BY t.TABLE_NAME, c.ORDINAL_POSITION;

-- Get table descriptions (if available)
SELECT 
    t.name AS table_name,
    ep.value AS table_description
FROM sys.tables t
LEFT JOIN sys.extended_properties ep ON ep.major_id = t.object_id 
    AND ep.minor_id = 0 
    AND ep.name = 'MS_Description'
ORDER BY t.name;

-- Get column descriptions (if available)
SELECT 
    t.name AS table_name,
    c.name AS column_name,
    ep.value AS column_description
FROM sys.tables t
INNER JOIN sys.columns c ON c.object_id = t.object_id
LEFT JOIN sys.extended_properties ep ON ep.major_id = t.object_id 
    AND ep.minor_id = c.column_id 
    AND ep.name = 'MS_Description'
WHERE ep.value IS NOT NULL
ORDER BY t.name, c.column_id;