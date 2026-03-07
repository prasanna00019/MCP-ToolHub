# Testing Guide - Optimized PostgreSQL MCP Server

## ✅ What Changed

**Optimized from 38 → 19 tools (50% reduction)**

### Tool Consolidation Details

| Category | Old Tools | New Tools | Names |
|----------|-----------|-----------|-------|
| **Analysis** | 6 | 5 | analyze_database, explain_database, get_table_details, **get_database_info** (new), render_database_diagrams |
| **CRUD Create** | 5 | 4 | **crud_insert** (merged), crud_create_table, crud_create_view, crud_create_index |
| **CRUD Read** | 5 | 2 | **crud_query** (merged), **crud_get** (unified) |
| **CRUD Update** | 5 | 2 | **crud_update** (unified), **crud_rename** (unified) |
| **CRUD Delete** | 4 | 1 | **crud_delete** (unified) |
| **Schema Mod** | 13 | 5 | **mod_column**, **mod_index**, **mod_constraint**, **mod_add_constraint**, **mod_view** |

**Bold** = New consolidated tools

---

## 🧪 Testing Methods

### Method 1: MCP Inspector (Recommended)

#### Step 1: Start MCP Inspector
```powershell
# Open a new PowerShell terminal
npx @modelcontextprotocol/inspector
```

This will:
- Start MCP Inspector on http://localhost:5173
- Open automatically in your browser

#### Step 2: Connect to Your PostgreSQL MCP Server

In the MCP Inspector UI:

1. **Server Configuration**: Add your PostgreSQL MCP server
   ```json
   {
     "command": "uv",
     "args": [
       "--directory",
       "C:\\Users\\Prasanna\\OneDrive\\Desktop\\MCP-ToolHub\\PostgreSQL-MCP",
       "run",
       "postgresql_server.py"
     ],
     "env": {
       "DB_HOST": "localhost",
       "DB_PORT": "5432",
       "DB_NAME": "your_database",
       "DB_USER": "postgres",
       "DB_PASSWORD": "your_password"
     }
   }
   ```

2. **Click "Connect"** - Inspector will launch your MCP server

3. **Verify Tool Count**: 
   - Look at the "Tools" tab
   - Should show **19 tools** (down from 38)

#### Step 3: Test Each Tool Category

**Test 1: Database Info (NEW unified tool)**
```json
Tool: get_database_info
Parameters:
{
  "info_type": "tables"
}
```
Expected: List of all tables with count

```json
{
  "info_type": "ollama"
}
```
Expected: Ollama service status

---

**Test 2: Consolidated Insert (crud_insert)**
```json
Tool: crud_insert
Parameters - Single Record:
{
  "table_name": "test_table",
  "data": {
    "name": "Test User",
    "email": "test@example.com"
  }
}
```

```json
Parameters - Batch Insert:
{
  "table_name": "test_table",
  "data": [
    {"name": "User 1", "email": "user1@example.com"},
    {"name": "User 2", "email": "user2@example.com"}
  ]
}
```
Expected: Automatic detection and appropriate insert

---

**Test 3: Unified Read (crud_get)**
```json
Tool: crud_get
Parameters - Get Records:
{
  "table_name": "test_table",
  "mode": "records",
  "options": {
    "limit": 10,
    "order_by": "id DESC"
  }
}
```

```json
Parameters - Count Records:
{
  "table_name": "test_table",
  "mode": "count"
}
```

```json
Parameters - Distinct Values:
{
  "table_name": "test_table",
  "mode": "distinct",
  "options": {
    "column_name": "email"
  }
}
```

```json
Parameters - Paginate:
{
  "table_name": "test_table",
  "mode": "paginate",
  "options": {
    "page": 1,
    "page_size": 10
  }
}
```
Expected: Different results based on mode

---

**Test 4: Unified Update (crud_update)**
```json
Tool: crud_update
Parameters - Single Record:
{
  "table_name": "test_table",
  "record_id": 1,
  "id_column": "id",
  "values": {
    "name": "Updated Name"
  }
}
```

```json
Parameters - Batch Update:
{
  "table_name": "test_table",
  "where_clause": "created_at < %s",
  "where_params": ["2024-01-01"],
  "values": {
    "status": "archived"
  }
}
```
Expected: Single or batch update based on parameters

---

**Test 5: Unified Delete (crud_delete)**
```json
Tool: crud_delete
Parameters - Delete Single Record:
{
  "table_name": "test_table",
  "mode": "records",
  "record_id": 5,
  "id_column": "id"
}
```

```json
Parameters - Delete Multiple:
{
  "table_name": "test_table",
  "mode": "records",
  "where_clause": "status = %s",
  "where_params": ["inactive"]
}
```

```json
Parameters - Truncate:
{
  "table_name": "test_table",
  "mode": "truncate"
}
```
Expected: Different deletion scopes based on mode

---

**Test 6: Unified Column Management (mod_column)**
```json
Tool: mod_column
Parameters - Add Column:
{
  "table_name": "test_table",
  "action": "add",
  "column_name": "",
  "column_spec": {
    "name": "status",
    "type": "VARCHAR(50)",
    "nullable": true
  }
}
```

```json
Parameters - Modify Type:
{
  "table_name": "test_table",
  "action": "modify_type",
  "column_name": "age",
  "column_spec": {
    "new_type": "BIGINT"
  }
}
```

```json
Parameters - Drop Column:
{
  "table_name": "test_table",
  "action": "drop",
  "column_name": "old_field",
  "cascade": false
}
```

```json
Parameters - Set Nullable:
{
  "table_name": "test_table",
  "action": "set_nullable",
  "column_name": "email",
  "column_spec": {
    "is_nullable": true
  }
}
```
Expected: All 4 column operations via single tool

---

**Test 7: Index & Constraint Management**
```json
Tool: mod_index
Parameters:
{
  "action": "list"
}
```

```json
Tool: mod_constraint
Parameters:
{
  "action": "list",
  "table_name": "test_table"
}
```

```json
Tool: mod_add_constraint
Parameters - Primary Key:
{
  "constraint_type": "primary_key",
  "table_name": "test_table",
  "spec": {
    "columns": ["id"]
  }
}
```

```json
Parameters - Foreign Key:
{
  "constraint_type": "foreign_key",
  "table_name": "orders",
  "spec": {
    "columns": ["user_id"],
    "ref_table": "users",
    "ref_columns": ["id"],
    "on_delete": "CASCADE"
  }
}
```
Expected: Unified constraint management

---

**Test 8: View Management (mod_view)**
```json
Tool: mod_view
Parameters - List Views:
{
  "action": "list"
}
```

```json
Parameters - Get Definition:
{
  "action": "get",
  "view_name": "active_users"
}
```

```json
Parameters - Drop View:
{
  "action": "drop",
  "view_name": "old_view",
  "cascade": false
}
```
Expected: All view operations via single tool

---

### Method 2: Claude Desktop / AI Agent Testing

#### Configuration File
Add to your MCP settings (Claude Desktop, VS Code, etc.):

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "postgresql": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\Prasanna\\OneDrive\\Desktop\\MCP-ToolHub\\PostgreSQL-MCP",
        "run",
        "postgresql_server.py"
      ],
      "env": {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "your_database",
        "DB_USER": "postgres",
        "DB_PASSWORD": "your_password"
      }
    }
  }
}
```

#### Test Queries for AI Agent

1. **"List all tables in my database"**
   - Should use: `get_database_info(info_type="tables")`

2. **"Insert a new user with name 'John Doe' and email 'john@example.com'"**
   - Should use: `crud_insert(data={...})`

3. **"Get all users and count how many there are"**
   - Should use: `crud_get(mode="records")` + `crud_get(mode="count")`

4. **"Add a 'phone' column to the users table (VARCHAR 20)"**
   - Should use: `mod_column(action="add", ...)`

5. **"Show me all foreign key constraints in the database"**
   - Should use: `mod_constraint(action="list")`

6. **"Delete all records where status is 'deleted'"**
   - Should use: `crud_delete(mode="records", where_clause=...)`

---

### Method 3: Python Client Testing

Use the included `client.py`:

```powershell
# Activate your virtual environment
.\.venv\Scripts\Activate.ps1

# Run the client
uv run client.py postgresql_server.py
```

#### Interactive Testing
```python
# In client prompt, test tools individually:
> list_tools
# Should show 19 tools (was 38 before)

> call_tool get_database_info info_type="tables"
> call_tool crud_insert table_name="test" data='{"name":"test"}'
> call_tool crud_get table_name="test" mode="records"
```

---

## 📊 Verification Checklist

### ✅ Pre-deployment Checks

- [ ] **Tool count**: Exactly 19 tools visible in MCP Inspector
- [ ] **No old tools**: Verify old tools like `crud_create_record`, `crud_get_records`, `list_tables` are gone
- [ ] **All new tools present**: Check all tools from the list above exist
- [ ] **Database connection**: Ensure .env file is configured correctly
- [ ] **No errors on startup**: Server starts without Python errors

### ✅ Functional Tests

- [ ] **Analysis tools**: `analyze_database()` returns full schema
- [ ] **Unified info**: `get_database_info()` works with all 3 modes (tables, ollama, summary)
- [ ] **Smart insert**: `crud_insert()` handles both Dict and List[Dict]
- [ ] **Multi-mode read**: `crud_get()` works with all 4 modes (records, count, distinct, paginate)
- [ ] **Unified update**: `crud_update()` handles single record, batch, and column updates
- [ ] **Flexible delete**: `crud_delete()` supports records, truncate, and drop modes
- [ ] **Column ops**: `mod_column()` handles add, modify_type, drop, set_nullable
- [ ] **Constraint mgmt**: `mod_constraint()` + `mod_add_constraint()` work correctly
- [ ] **View operations**: `mod_view()` handles list, get, drop

---

## 🎯 Expected Results

### Token Savings Estimate

**Before**: 38 tool definitions × ~150 tokens/tool = ~5,700 tokens per request
**After**: 19 tool definitions × ~200 tokens/tool = ~3,800 tokens per request

**Savings**: ~1,900 tokens per request (~33% reduction)

*Note: Consolidated tools have slightly longer descriptions but still result in major savings*

### Performance Improvements

- **Faster Agent Decision-Making**: 50% fewer options to evaluate
- **Cleaner Logs**: Easier to debug with fewer tool calls
- **Better Context Usage**: More room for actual data and responses

---

## 🐛 Troubleshooting

### Issue: "Tool not found" error
**Solution**: 
- Restart the MCP server
- Clear MCP Inspector cache
- Verify `postgresql_server.py` has no syntax errors

### Issue: Old tool names still showing
**Solution**:
- Restart Claude Desktop or your MCP client
- Check you're running the updated `postgresql_server.py`
- Delete any cached MCP configurations

### Issue: "Missing required parameter" error
**Solution**:
- Review the new parameter structure in this guide
- Old tools had different signatures, update your calls
- Use MCP Inspector to see exact parameter schemas

### Issue: Database connection fails
**Solution**:
- Verify `.env` file has correct credentials
- Test PostgreSQL connection with `psql` or pgAdmin
- Check firewall/network access to database

---

## 📝 Migration Notes

### If you have existing code calling old tools:

**Old → New Mappings:**

```python
# Old: crud_create_record(table, values)
# New: crud_insert(table, data=values)

# Old: crud_create_records_batch(table, records)
# New: crud_insert(table, data=records)

# Old: crud_get_records(table, where_clause, ...)
# New: crud_get(table, mode="records", where_clause, ...)

# Old: crud_get_record_count(table, where_clause)
# New: crud_get(table, mode="count", where_clause)

# Old: crud_distinct_values(table, column)
# New: crud_get(table, mode="distinct", options={"column_name": column})

# Old: crud_paginate_data(table, page, page_size, ...)
# New: crud_get(table, mode="paginate", options={"page": page, "page_size": page_size}, ...)

# Old: crud_update_record(table, id, id_col, values)
# New: crud_update(table, values, record_id=id, id_column=id_col)

# Old: crud_update_records_batch(table, where, params, values)
# New: crud_update(table, values, where_clause=where, where_params=params)

# Old: crud_delete_record(table, id, id_col)
# New: crud_delete(table, mode="records", record_id=id, id_column=id_col)

# Old: crud_delete_records(table, where, params)
# New: crud_delete(table, mode="records", where_clause=where, where_params=params)

# Old: crud_truncate_table(table)
# New: crud_delete(table, mode="truncate")

# Old: crud_drop_table(table, cascade)
# New: crud_delete(table, mode="drop", cascade=cascade)

# Old: list_tables()
# New: get_database_info(info_type="tables")

# Old: check_ollama_status()
# New: get_database_info(info_type="ollama")
```

---

## ✨ Success Indicators

You'll know the optimization is working when:

1. ✅ MCP Inspector shows **19 tools** (not 38)
2. ✅ All test queries above work correctly
3. ✅ AI agents make faster decisions
4. ✅ Token usage in logs shows ~30-50% reduction
5. ✅ No functionality is lost - all operations still work

---

**Need Help?** Check the updated README.md for detailed tool documentation and usage examples.
