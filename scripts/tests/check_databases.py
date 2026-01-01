#!/usr/bin/env python3
"""
Script để kiểm tra tất cả PostgreSQL databases và tables
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import psycopg
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_databases():
    """List tất cả databases"""
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    
    # Connect to postgres database to list all databases
    conn_string = f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/postgres"
    
    try:
        engine = create_engine(conn_string)
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT datname, pg_size_pretty(pg_database_size(datname)) as size
                FROM pg_database 
                WHERE datistemplate = false 
                ORDER BY datname;
            """))
            
            print("\n" + "="*80)
            print("📊 DANH SÁCH POSTGRESQL DATABASES")
            print("="*80)
            print(f"{'Database Name':<30} {'Size':<20}")
            print("-"*80)
            
            databases = []
            for row in result:
                databases.append(row[0])
                print(f"{row[0]:<30} {row[1]:<20}")
            
            print("="*80)
            print(f"✅ Tổng số databases: {len(databases)}\n")
            
            return databases
            
    except Exception as e:
        print(f"❌ Lỗi khi kết nối database: {e}")
        return []

def check_tables_in_database(db_name):
    """List tất cả tables trong một database"""
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    
    conn_string = f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    try:
        engine = create_engine(conn_string)
        inspector = inspect(engine)
        
        # Get all tables
        tables = inspector.get_table_names()
        
        print("\n" + "="*80)
        print(f"📋 TABLES TRONG DATABASE: {db_name}")
        print("="*80)
        
        if not tables:
            print("⚠️  Không có table nào trong database này")
            return
        
        for table_name in sorted(tables):
            # Get columns info
            columns = inspector.get_columns(table_name)
            
            # Get row count
            with engine.connect() as conn:
                result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                row_count = result.scalar()
            
            print(f"\n📊 Table: {table_name}")
            print(f"   Số dòng: {row_count:,}")
            print(f"   Columns ({len(columns)}):")
            
            for col in columns:
                col_type = str(col['type'])
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                print(f"      - {col['name']:<30} {col_type:<20} {nullable}")
        
        print("\n" + "="*80)
        print(f"✅ Tổng số tables: {len(tables)}")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"❌ Lỗi khi kiểm tra tables trong {db_name}: {e}\n")

def main():
    print("\n🔍 KIỂM TRA POSTGRESQL DATABASES VÀ TABLES")
    print("="*80)
    
    # List all databases
    databases = check_databases()
    
    if not databases:
        print("❌ Không tìm thấy database nào hoặc không thể kết nối")
        return
    
    # Check tables in main database
    main_db = os.getenv("DB_NAME", "rag_bidding_v2")
    
    if main_db in databases:
        check_tables_in_database(main_db)
    else:
        print(f"\n⚠️  Database chính '{main_db}' không tồn tại!")
        print(f"   Các databases có sẵn: {', '.join(databases)}")
    
    # Ask if want to check other databases
    print("\n💡 Để kiểm tra database khác, chạy:")
    for db in databases:
        if db not in ['postgres', 'template0', 'template1', main_db]:
            print(f"   python scripts/tests/check_databases.py {db}")

if __name__ == "__main__":
    main()
