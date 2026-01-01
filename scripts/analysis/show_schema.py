#!/usr/bin/env python3
"""
Display detailed database schema information
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import inspect, text
from src.models.base import engine

inspector = inspect(engine)

print("=" * 70)
print("DATABASE SCHEMA DETAILS")
print("=" * 70)

for table_name in ["documents", "langchain_pg_collection", "langchain_pg_embedding"]:
    print(f"\n📋 TABLE: {table_name}")
    print("-" * 70)

    # Columns
    columns = inspector.get_columns(table_name)
    print(f"\n  COLUMNS ({len(columns)}):")
    for col in columns:
        nullable = "NULL" if col["nullable"] else "NOT NULL"
        default_val = col.get("server_default", None)
        default = f" DEFAULT {default_val}" if default_val else ""
        comment = col.get("comment", "")
        comment_str = f" -- {comment}" if comment else ""
        print(
            f'    • {col["name"]:<20} {str(col["type"]):<30} {nullable}{default}{comment_str}'
        )

    # Indexes
    indexes = inspector.get_indexes(table_name)
    print(f"\n  INDEXES ({len(indexes)}):")
    for idx in indexes:
        unique = "UNIQUE" if idx.get("unique") else "NON-UNIQUE"
        cols = ", ".join(idx["column_names"])
        print(f'    • {idx["name"]:<45} {unique:<12} ON ({cols})')

    # Constraints
    pk = inspector.get_pk_constraint(table_name)
    if pk and pk.get("constrained_columns"):
        print(f"\n  PRIMARY KEY:")
        pk_cols = ", ".join(pk["constrained_columns"])
        print(f'    • {pk["name"]:<45} ON ({pk_cols})')

    fks = inspector.get_foreign_keys(table_name)
    if fks:
        print(f"\n  FOREIGN KEYS ({len(fks)}):")
        for fk in fks:
            cols = ", ".join(fk["constrained_columns"])
            ref_cols = ", ".join(fk["referred_columns"])
            print(f'    • {fk["name"]:<45} {cols} -> {fk["referred_table"]}.{ref_cols}')

    print()

print("=" * 70)
print("\nSCHEMA STATISTICS:")
print("=" * 70)

with engine.connect() as conn:
    # Table sizes
    result = conn.execute(
        text(
            """
        SELECT 
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
            pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY size_bytes DESC
    """
        )
    )

    print("\nTable Sizes:")
    for row in result:
        print(f"  • {row[1]:<35} {row[2]:>12}")

    # Row counts
    print("\nRow Counts:")
    for table in ["documents", "langchain_pg_collection", "langchain_pg_embedding"]:
        count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
        count = count_result.scalar()
        print(f"  • {table:<35} {count:>12,} rows")

    # Index usage (top 10)
    result = conn.execute(
        text(
            """
        SELECT 
            schemaname,
            tablename,
            indexname,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch
        FROM pg_stat_user_indexes
        WHERE schemaname = 'public'
        ORDER BY idx_scan DESC
        LIMIT 10
    """
        )
    )

    print("\nMost Used Indexes (Top 10):")
    for row in result:
        print(f"  • {row[2]:<50} scans: {row[3]:>8,}")

print("\n" + "=" * 70)
