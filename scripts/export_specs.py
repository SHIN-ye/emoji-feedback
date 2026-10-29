import json
from pathlib import Path
from sqlalchemy.schema import CreateTable,CreateIndex
from sqlalchemy.dialects import postgresql
from backend.main import app
from backend.models import Base
Path('docs/openapi.json').write_text(json.dumps(app.openapi(),ensure_ascii=False,indent=2),encoding='utf-8')
ddl='-- PostgreSQL schema for a NEW empty database; do not apply to existing tables.\n'
for table in Base.metadata.sorted_tables:
    ddl+=str(CreateTable(table).compile(dialect=postgresql.dialect()))+';\n'
    for index in table.indexes: ddl+=str(CreateIndex(index).compile(dialect=postgresql.dialect()))+';\n'
Path('docs/schema-postgresql.sql').write_text(ddl,encoding='utf-8')
