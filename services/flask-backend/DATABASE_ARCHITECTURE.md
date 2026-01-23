# Database Architecture - Dual Layer Approach

## Overview

This application uses a **dual-layer database architecture**:

1. **SQLAlchemy + Alembic**: Schema management, migrations, and database initialization
2. **PyDAL**: Runtime database operations (queries, inserts, updates, deletes)

This approach provides the best of both worlds:
- **SQLAlchemy**: Industry-standard migrations, type safety, and schema versioning
- **PyDAL**: Cross-database compatibility and simplified runtime queries

## Architecture Components

### Layer 1: SQLAlchemy (Schema Management)

**Location**: `app/db/`

**Purpose**:
- Define database schema
- Create/modify tables via migrations
- Version control for database changes

**Files**:
- `app/db/models.py` - SQLAlchemy model definitions
- `app/db/base.py` - Base configuration
- `alembic/` - Migration scripts
- `alembic.ini` - Alembic configuration

**Usage**: NEVER use SQLAlchemy models for runtime queries. They are for schema definition only.

### Layer 2: PyDAL (Runtime Operations)

**Location**: `app/models.py`

**Purpose**:
- Runtime database queries
- CRUD operations
- Transaction management
- Cross-database support (PostgreSQL, MySQL, SQLite)

**Configuration**:
```python
db = DAL(
    db_uri,
    migrate=False,  # Migrations disabled - handled by Alembic
    fake_migrate_all=True,  # Map to existing schema
)
```

## Workflow

### 1. Making Schema Changes

When you need to change the database schema:

1. **Update SQLAlchemy models** in `app/db/models.py`:
   ```python
   # Add a new column
   class User(Base):
       __tablename__ = "users"
       new_field = Column(String(255))
   ```

2. **Create migration**:
   ```bash
   cd services/flask-backend
   alembic revision --autogenerate -m "Add new_field to users"
   ```

3. **Review the generated migration** in `alembic/versions/`:
   - Verify the upgrade() function
   - Verify the downgrade() function
   - Make manual adjustments if needed

4. **Update PyDAL definitions** in `app/models.py` to match:
   ```python
   db.define_table(
       "users",
       Field("new_field", "string", length=255),
       # ... other fields
   )
   ```

5. **Apply migration** (happens automatically on container start):
   ```bash
   alembic upgrade head
   ```

### 2. Runtime Database Operations

Use PyDAL helper functions from `app/models.py`:

```python
# Create user
from app.models import create_user
user = create_user(
    email="test@example.com",
    password_hash=hashed_password,
    full_name="Test User",
    role="viewer"
)

# Query users
from app.models import get_user_by_email
user = get_user_by_email("test@example.com")

# Update user
from app.models import update_user
update_user(user_id, full_name="Updated Name")
```

## Migration Commands

### Create a new migration
```bash
cd services/flask-backend
alembic revision --autogenerate -m "Description of changes"
```

### Apply migrations
```bash
alembic upgrade head
```

### Rollback last migration
```bash
alembic downgrade -1
```

### View migration history
```bash
alembic history
```

### View current version
```bash
alembic current
```

## Development Workflow

### Initial Setup

1. **Database must exist** before running migrations:
   ```sql
   CREATE DATABASE darwin;
   ```

2. **Run initial migration** (happens automatically):
   ```bash
   alembic upgrade head
   ```

3. **Start application** - PyDAL will map to existing schema

### Adding a New Table

1. **Create SQLAlchemy model**:
   ```python
   # app/db/models.py
   class NewTable(Base):
       __tablename__ = "new_table"
       id = Column(Integer, primary_key=True)
       name = Column(String(255))
   ```

2. **Generate migration**:
   ```bash
   alembic revision --autogenerate -m "Add new_table"
   ```

3. **Add PyDAL definition**:
   ```python
   # app/models.py
   db.define_table(
       "new_table",
       Field("id", "id"),
       Field("name", "string", length=255),
   )
   ```

4. **Create helper functions**:
   ```python
   # app/models.py
   def create_new_table_record(name: str) -> dict:
       db = get_db()
       record_id = db.new_table.insert(name=name)
       db.commit()
       return db(db.new_table.id == record_id).select().first().as_dict()
   ```

## Important Notes

### DO NOT:
- ❌ Use SQLAlchemy models for runtime queries
- ❌ Enable PyDAL migrations (`migrate=True`)
- ❌ Manually modify database schema without migrations
- ❌ Skip updating PyDAL definitions after schema changes

### DO:
- ✅ Use SQLAlchemy for all schema changes
- ✅ Create migrations for every schema modification
- ✅ Use PyDAL for all runtime operations
- ✅ Keep SQLAlchemy and PyDAL definitions in sync
- ✅ Review generated migrations before applying

## Troubleshooting

### Migration fails with "relation already exists"
The table was created manually or by PyDAL migrations. Options:
1. Drop the table and re-run migration
2. Create a fake migration: `alembic stamp head`

### PyDAL can't find table
Ensure:
1. Migration ran successfully (`alembic current`)
2. PyDAL definition matches SQLAlchemy schema
3. `fake_migrate_all=True` is set

### Column mismatch errors
PyDAL and SQLAlchemy definitions are out of sync:
1. Check SQLAlchemy model in `app/db/models.py`
2. Check PyDAL definition in `app/models.py`
3. Ensure field names and types match

## Testing

### Test migrations
```bash
# Apply all migrations
alembic upgrade head

# Test rollback
alembic downgrade -1
alembic upgrade +1
```

### Test PyDAL operations
```python
# In Python shell
from app.models import get_db, create_user
db = get_db()

# Test query
users = db(db.users).select()
print(users)
```

## Benefits of This Approach

1. **Type Safety**: SQLAlchemy provides compile-time type checking
2. **Migration Management**: Alembic tracks all schema changes with version control
3. **Cross-Database Support**: PyDAL works with PostgreSQL, MySQL, MariaDB, SQLite
4. **Performance**: PyDAL optimized for runtime queries
5. **Maintainability**: Clear separation of concerns
6. **Rollback Capability**: Easy to revert schema changes

## References

- SQLAlchemy: https://docs.sqlalchemy.org/
- Alembic: https://alembic.sqlalchemy.org/
- PyDAL: https://github.com/web2py/pydal
