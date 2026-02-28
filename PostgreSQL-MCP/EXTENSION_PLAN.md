# PostgreSQL MCP Extension Plan: Complete CRUD & Operations

## Overview
Extend the existing SchemaIntelligence MCP server to include comprehensive CRUD operations and advanced PostgreSQL features beyond schema analysis.

## Current Implementation Status
- ✅ **analyze_database()** - Full schema extraction and analysis
- ✅ **explain_database()** - LLM-powered database explanation
- ✅ **get_table_details()** - Detailed table information
- ✅ **list_tables()** - List all tables
- ✅ **check_ollama_status()** - Ollama service verification
- ✅ **render_database_diagrams()** - SVG/PNG diagram rendering

---

## Extension Plan: 6 New Modules with 40+ Operations

### 📋 **PHASE 1: CRUD Operations Module** (`src/crud/crud_manager.py`)
Core data manipulation operations

#### Create Operations
- `create_record()` - Insert a single record (parameterized)
- `create_records_batch()` - Insert multiple records (batch insert)
- `create_table()` - Create new table with column definitions and constraints
- `create_view()` - Create database view with auto-formatting
- `create_index()` - Create single or composite index
- `create_unique_index()` - Create unique index
- `create_schema()` - Create new schema

#### Read Operations
- `query_data()` - Execute SELECT queries with filtering, sorting, pagination
- `query_with_joins()` - Execute JOINs with auto-suggestion from schema
- `get_records()` - Get records with WHERE conditions (parameterized)
- `get_record_count()` - Count records with conditional logic
- `distinct_values()` - Get distinct values for a column
- `paginate_data()` - Get paginated results (offset/limit)

#### Update Operations
- `update_record()` - Update single record (parameterized)
- `update_records_batch()` - Batch update with WHERE clause
- `update_column()` - Bulk update specific column
- `rename_table()` - Rename table safely
- `rename_column()` - Rename column with dependency checks

#### Delete Operations
- `delete_record()` - Delete single record with confirmation
- `delete_records()` - Delete multiple records with WHERE clause
- `truncate_table()` - Clear all data from table
- `drop_table()` - Drop table with cascade option

---

### 🔧 **PHASE 2: Schema Modification Module** (`src/schema/schema_manager.py`)
Advanced schema operations

#### Column Management
- `add_column()` - Add column with type and constraints
- `modify_column()` - Alter column type/constraints
- `drop_column()` - Remove column with cascade option
- `add_default_value()` - Set column defaults
- `set_nullable()` - Make column nullable/not-null
- `add_column_comment()` - Add documentation to column

#### Index Operations
- `list_indexes()` - List all indexes with usage info
- `get_index_info()` - Detailed index information
- `drop_index()` - Drop index safely
- `analyze_index_usage()` - Check if index is being used
- `rebuild_index()` - Rebuild fragmented index

#### Constraint Operations
- `list_constraints()` - List all constraints by type
- `add_primary_key()` - Add primary key constraint
- `add_foreign_key()` - Add foreign key with cascade rules
- `add_unique_constraint()` - Add unique constraint
- `add_check_constraint()` - Add check constraint
- `drop_constraint()` - Remove constraint safely
- `list_foreign_keys()` - List all foreign key relationships

#### View Operations
- `list_views()` - List all views
- `get_view_definition()` - Get view SQL definition
- `drop_view()` - Drop view with cascade option

---

### 📊 **PHASE 3: Query Analysis & Optimization Module** (`src/analysis/query_analyzer.py`)
Performance analysis and optimization recommendations

#### Query Analysis
- `explain_query()` - Get EXPLAIN output (textual)
- `explain_query_analyze()` - Get EXPLAIN ANALYZE (with actual execution)
- `get_query_plan()` - Structured query execution plan
- `analyze_slow_query()` - Identify slow query issues
- `compare_query_plans()` - Compare plans for two query variants

#### Statistics & Suggestions
- `suggest_indexes()` - Recommend indexes based on queries
- `get_missing_indexes()` - Detect missing indexes
- `analyze_table_statistics()` - Column distribution, NULL counts, etc.
- `get_table_size_info()` - Table, index, and toast sizes
- `analyze_column_statistics()` - Histograms, correlations
- `suggest_query_optimization()` - Rewrite suggestions

#### Locking & Performance
- `find_long_running_queries()` - Identify slow/blocking queries
- `detect_deadlocks()` - Check deadlock conditions
- `analyze_index_fragmentation()` - Index bloat analysis
- `find_unused_indexes()` - Identify redundant indexes

---

### 💾 **PHASE 4: Data Management Module** (`src/data/data_manager.py`)
Import/export and data manipulation

#### Data Export
- `export_table_csv()` - Export table to CSV file
- `export_table_json()` - Export table to JSON file
- `export_table_sql()` - Generate INSERT statements
- `export_schema_sql()` - Full schema SQL dump
- `export_all_tables()` - Batch export all tables

#### Data Import
- `import_csv()` - Import CSV into table
- `import_json()` - Import JSON into table
- `import_sql()` - Execute SQL import script
- `copy_table_structure()` - Clone table without data
- `copy_table_data()` - Duplicate table with data

#### Data Search & Analysis
- `search_data()` - Full-text search across columns
- `find_duplicate_records()` - Identify duplicates
- `find_null_values()` - Find NULL occurrences
- `find_orphaned_records()` - Records with missing FK references
- `validate_foreign_keys()` - Check FK integrity
- `get_data_sample()` - Get representative sample

#### Data Cleanup
- `remove_duplicates()` - Clean duplicate data
- `fill_NULL_values()` - Replace NULLs with defaults
- `trim_whitespace()` - Clean text columns
- `normalize_case()` - Standardize case (upper/lower/title)

---

### ⚙️ **PHASE 5: Transaction & Advanced Operations Module** (`src/operations/transaction_manager.py`)
Transaction management and advanced features

#### Transaction Control
- `begin_transaction()` - Start transaction explicitly
- `commit_transaction()` - Commit current transaction
- `rollback_transaction()` - Rollback current transaction
- `execute_transaction()` - Execute multiple queries as transaction
- `set_isolation_level()` - Configure transaction isolation

#### Backup & Restore
- `create_checkpoint()` - Create recovery point
- `backup_table_snapshot()` - Create table backup
- `restore_table_snapshot()` - Restore from backup
- `list_backups()` - Show available backups
- `export_schema_backup()` - Full schema backup

#### Advanced Operations
- `execute_raw_sql()` - Execute arbitrary SQL with warnings
- `explain_ddl()` - Explain DDL operation impact
- `estimate_operation_cost()` - Estimate operation impact
- `validate_sql_syntax()` - Check SQL validity before execution
- `get_connection_info()` - Current connection details

---

### 📈 **PHASE 6: Monitoring & Statistics Module** (`src/monitoring/stats_collector.py`)
Database health and performance monitoring

#### Database Statistics
- `get_database_size()` - Total database size with breakdown
- `get_table_stats()` - Row count, dead tuple ratio, last vacuum
- `get_column_stats()` - Column-level statistics
- `get_connection_stats()` - Active connections count
- `monitor_table_growth()` - Track size over time
- `get_cache_hit_ratio()` - Buffer cache efficiency

#### Health Checks
- `vacuum_status()` - Identify tables needing vacuum
- `analyze_bloat()` - Detect table/index bloat
- `check_autovacuum_config()` - Verify autovacuum settings
- `list_locks()` - Currently held locks
- `detect_idle_transactions()` - Long-running idle connections
- `check_disk_space()` - Available disk space

#### Activity Monitoring
- `get_active_queries()` - Currently executing queries
- `get_slow_queries_log()` - Recent slow queries
- `get_session_info()` - Session statistics
- `get_replication_status()` - If applicable
- `check_query_cache()` - Query performance cache

---

## Implementation Architecture

### Directory Structure (New)
```
PostgreSQL-MCP/
├── src/
│   ├── crud/
│   │   ├── __init__.py
│   │   ├── crud_manager.py          # CRUD operations
│   │   └── crud_validator.py        # Input validation
│   ├── schema/
│   │   ├── schema_manager.py        # Schema modification
│   │   └── constraint_manager.py    # Constraint operations
│   ├── analysis/
│   │   ├── detector.py              # Existing
│   │   └── query_analyzer.py        # Query analysis
│   ├── data/
│   │   ├── __init__.py
│   │   ├── data_manager.py          # Import/export
│   │   ├── search_engine.py         # Data search
│   │   └── cleaner.py               # Data cleanup
│   ├── operations/
│   │   ├── __init__.py
│   │   ├── transaction_manager.py   # Transaction control
│   │   └── backup_manager.py        # Backup/restore
│   └── monitoring/
│       ├── __init__.py
│       └── stats_collector.py       # Statistics & health
├── postgresql_server.py             # MCP server (extend with new tools)
└── tests/                           # Test suite (optional)
```

### Safety & Security Features
- **SQL Injection Prevention**: Parameterized queries for all user inputs
- **Confirmation Prompts**: For destructive operations (DROP, TRUNCATE, DELETE)
- **Dry-Run Mode**: Preview operations before execution
- **Audit Logging**: Log all modifications with user/timestamp
- **Transaction Rollback**: Automatic rollback on errors
- **Input Validation**: Type checking and constraint validation
- **Constraint Checking**: FK/unique constraint verification before operations

### Return Format (Standardized)
```python
{
    "status": "success|error|warning",
    "operation": "operation_name",
    "duration_ms": 123,
    "rows_affected": 5,
    "result": {...},  # Operation-specific result
    "message": "Human-readable message",
    "warnings": [...],
    "metadata": {...}
}
```

---

## Implementation Phases

### 🎯 **Phase 1: CRUD Operations** (Recommended First)
- Most frequently used
- Foundation for other modules
- Duration: 2-3 days

### 🎯 **Phase 2: Schema Modification** (Recommended Second)
- Essential for database design changes
- Build on Phase 1
- Duration: 2-3 days

### 🎯 **Phase 3: Query Analysis** (Recommended Third)
- Performance optimization focus
- Complete analysis toolkit
- Duration: 2-3 days

### 🎯 **Phase 4: Data Management** (Recommended Fourth)
- Data migration workflows
- Import/export functionality
- Duration: 2-3 days

### 🎯 **Phase 5: Advanced Operations** (Recommended Fifth)
- Transaction control
- Safety features
- Duration: 1-2 days

### 🎯 **Phase 6: Monitoring** (Recommended Sixth)
- Database health
- Performance tracking
- Duration: 1-2 days

---

## Key Features by Phase

### Cross-Cutting Concerns
- **Error Handling**: Comprehensive error messages with suggestions
- **Type Safety**: Type hints throughout codebase
- **Logging**: Detailed operation logging for debugging
- **Testing**: Unit tests for all major functions
- **Documentation**: Docstrings and usage examples
- **Caching**: Cache schema info for performance
- **Connection Pooling**: Reuse connections where possible

### Integration with Existing Code
- Use existing `extract_schema()` for dependency checks
- Leverage `OllamaAnalyzer` for optimization suggestions
- Build on `DatabaseConfig` for connection management
- Enhance with analysis from `detector.py`
- Export using `DiagramRenderer` where applicable

---

## Success Criteria

✅ All CRUD operations work safely (parameterized, validated)
✅ Schema modifications checked for dependencies
✅ Query analysis provides actionable insights
✅ Import/export handles multiple formats
✅ Transaction control robust and documented
✅ Monitoring gives real-time database health
✅ All operations have comprehensive error handling
✅ Performance acceptable for large datasets
✅ MCP tools properly exposed with clear documentation
✅ Code is maintainable and well-tested

---

## Next Steps (After Approval)

1. **Review & Approve** - Confirm if plan scope is acceptable
2. **Prioritize** - If needed, reduce scope to specific phases
3. **Implementation** - Build Phase 1-6 modules
4. **Integration** - Expose 40+ operations via MCP server
5. **Testing** - Unit and integration tests
6. **Documentation** - Full API documentation
7. **Optimization** - Performance tuning and caching

---

## Questions for User

1. Should we implement all 6 phases or prioritize specific ones?
2. Any specific operations that are high-priority?
3. Should we include data backup/restore with versioning?
4. Do you need real-time monitoring/dashboards?
5. Should we add support for PostgreSQL-specific features (JSONB, Arrays, Ranges)?
6. Do you want to integrate with existing database tools (pgAdmin, DBeaver)?
