#!/bin/bash

# RAG Database Export Script
# Export database với multiple formats để dễ dàng migrate

set -e  # Exit on error

# Configuration
DB_NAME="rag_bidding_v2"
DB_USER="sakana"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
EXPORT_DIR="backup/exports/$TIMESTAMP"

echo "🚀 Starting RAG Database Export"
echo "================================"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Export Directory: $EXPORT_DIR"
echo "Timestamp: $TIMESTAMP"
echo ""

# Create export directory
mkdir -p "$EXPORT_DIR"

echo "📊 Database Information:"
echo "------------------------"
psql -d $DB_NAME -U $DB_USER -c "
SELECT 
    c.name as collection,
    COUNT(e.id) as embeddings,
    vector_dims(e.embedding) as dimensions,
    pg_size_pretty(pg_total_relation_size('langchain_pg_embedding')) as table_size
FROM langchain_pg_collection c 
LEFT JOIN langchain_pg_embedding e ON c.uuid = e.collection_id 
GROUP BY c.name, vector_dims(e.embedding);
"

echo ""
echo "📦 Exporting Database..."
echo "------------------------"

# 1. Full database dump (binary format - best for restoration)
echo "1️⃣  Creating full database dump (binary format)..."
pg_dump -U $DB_USER -d $DB_NAME -F c -f "$EXPORT_DIR/rag_bidding_full_${TIMESTAMP}.dump"
echo "   ✅ Binary dump created: $(du -h $EXPORT_DIR/rag_bidding_full_${TIMESTAMP}.dump | cut -f1)"

# 2. SQL dump (human readable)
echo "2️⃣  Creating SQL dump..."
pg_dump -U $DB_USER -d $DB_NAME -f "$EXPORT_DIR/rag_bidding_full_${TIMESTAMP}.sql"
echo "   ✅ SQL dump created: $(du -h $EXPORT_DIR/rag_bidding_full_${TIMESTAMP}.sql | cut -f1)"

# 3. Schema only
echo "3️⃣  Creating schema-only dump..."
pg_dump -U $DB_USER -d $DB_NAME -s -f "$EXPORT_DIR/rag_bidding_schema_${TIMESTAMP}.sql"
echo "   ✅ Schema dump created: $(du -h $EXPORT_DIR/rag_bidding_schema_${TIMESTAMP}.sql | cut -f1)"

# 4. Data only (without schema)
echo "4️⃣  Creating data-only dump..."
pg_dump -U $DB_USER -d $DB_NAME -a -f "$EXPORT_DIR/rag_bidding_data_${TIMESTAMP}.sql"
echo "   ✅ Data dump created: $(du -h $EXPORT_DIR/rag_bidding_data_${TIMESTAMP}.sql | cut -f1)"

# 5. Export embeddings to CSV (metadata only, vectors are too large for CSV)
echo "5️⃣  Exporting embeddings metadata to CSV..."
psql -d $DB_NAME -U $DB_USER -c "
COPY (
    SELECT 
        e.id,
        e.custom_id,
        LEFT(e.document, 200) as document_preview,
        e.cmetadata,
        c.name as collection_name
    FROM langchain_pg_embedding e
    JOIN langchain_pg_collection c ON e.collection_id = c.uuid
    ORDER BY e.id
) TO STDOUT WITH CSV HEADER
" > "$EXPORT_DIR/embeddings_metadata_${TIMESTAMP}.csv"
echo "   ✅ CSV metadata created: $(du -h $EXPORT_DIR/embeddings_metadata_${TIMESTAMP}.csv | cut -f1)"

# 6. Export collections info
echo "6️⃣  Exporting collections information..."
psql -d $DB_NAME -U $DB_USER -c "
COPY (
    SELECT 
        uuid,
        name,
        cmetadata
    FROM langchain_pg_collection
) TO STDOUT WITH CSV HEADER
" > "$EXPORT_DIR/collections_${TIMESTAMP}.csv"
echo "   ✅ Collections info created: $(du -h $EXPORT_DIR/collections_${TIMESTAMP}.csv | cut -f1)"

# 7. Create summary report
echo "7️⃣  Creating export summary..."
cat > "$EXPORT_DIR/EXPORT_SUMMARY.md" << EOF
# RAG Database Export Summary

**Export Date**: $(date)  
**Database**: $DB_NAME  
**User**: $DB_USER  
**Export Directory**: $EXPORT_DIR  

## Database Statistics

$(psql -d $DB_NAME -U $DB_USER -t -c "
SELECT 
    '- **Total Collections**: ' || COUNT(DISTINCT c.name) || '  
- **Total Embeddings**: ' || COALESCE(SUM(embedding_count), 0) || '  
- **Embedding Dimensions**: ' || COALESCE(MAX(dimensions), 0) || '  
- **Database Size**: ' || pg_size_pretty(pg_database_size('$DB_NAME'))
FROM (
    SELECT 
        c.name,
        COUNT(e.id) as embedding_count,
        vector_dims(e.embedding) as dimensions
    FROM langchain_pg_collection c 
    LEFT JOIN langchain_pg_embedding e ON c.uuid = e.collection_id 
    GROUP BY c.name, vector_dims(e.embedding)
) stats
RIGHT JOIN langchain_pg_collection c ON true;
")

## Exported Files

$(ls -lh $EXPORT_DIR | grep -v ^total | awk '{printf "- **%s** (%s): %s\n", $9, $5, $9}' | grep -v EXPORT_SUMMARY.md)

## File Descriptions

- **\`*_full_*.dump\`**: Complete database in PostgreSQL binary format (best for restoration)
- **\`*_full_*.sql\`**: Complete database in SQL format (human-readable)
- **\`*_schema_*.sql\`**: Database schema only (table structures, indexes, etc.)
- **\`*_data_*.sql\`**: Data only without schema
- **\`embeddings_metadata_*.csv\`**: Embeddings metadata (without vectors due to size)
- **\`collections_*.csv\`**: Collection information

## Restoration Commands

### Restore Full Database (Binary)
\`\`\`bash
# Create new database
createdb -U postgres new_rag_db

# Restore from binary dump
pg_restore -U postgres -d new_rag_db -c rag_bidding_full_${TIMESTAMP}.dump
\`\`\`

### Restore Full Database (SQL)
\`\`\`bash
# Create new database
createdb -U postgres new_rag_db

# Restore from SQL dump
psql -U postgres -d new_rag_db -f rag_bidding_full_${TIMESTAMP}.sql
\`\`\`

### Restore Schema Only
\`\`\`bash
psql -U postgres -d target_db -f rag_bidding_schema_${TIMESTAMP}.sql
\`\`\`

### Restore Data Only
\`\`\`bash
psql -U postgres -d target_db -f rag_bidding_data_${TIMESTAMP}.sql
\`\`\`

## Migration Notes

1. **pgvector Extension**: Ensure target database has pgvector extension installed
2. **Vector Dimensions**: All embeddings use 3072 dimensions (text-embedding-3-large native)
3. **Langchain Tables**: Uses langchain_pg_collection and langchain_pg_embedding tables
4. **Permissions**: Ensure target user has appropriate permissions

## Verification

After restoration, verify with:
\`\`\`sql
-- Check collections
SELECT name, COUNT(*) FROM langchain_pg_collection GROUP BY name;

-- Check embeddings
SELECT c.name, COUNT(e.id), vector_dims(e.embedding) 
FROM langchain_pg_collection c 
LEFT JOIN langchain_pg_embedding e ON c.uuid = e.collection_id 
GROUP BY c.name, vector_dims(e.embedding);

-- Check extension
SELECT * FROM pg_extension WHERE extname = 'vector';
\`\`\`
EOF

echo "   ✅ Export summary created: $EXPORT_DIR/EXPORT_SUMMARY.md"

# 8. Create archive
echo "8️⃣  Creating compressed archive..."
cd backup/exports
tar -czf "rag_bidding_export_${TIMESTAMP}.tar.gz" "$TIMESTAMP/"
cd - > /dev/null
echo "   ✅ Archive created: backup/exports/rag_bidding_export_${TIMESTAMP}.tar.gz"

# Final summary
echo ""
echo "🎉 Export Complete!"
echo "=================="
echo "📁 Export Directory: $(realpath $EXPORT_DIR)"
echo "📦 Archive File: $(realpath backup/exports/rag_bidding_export_${TIMESTAMP}.tar.gz)"
echo "📊 Archive Size: $(du -h backup/exports/rag_bidding_export_${TIMESTAMP}.tar.gz | cut -f1)"
echo ""
echo "📋 Files exported:"
ls -lh "$EXPORT_DIR" | grep -v ^total
echo ""
echo "✨ Ready to transfer to another system!"
echo "💡 Read EXPORT_SUMMARY.md for restoration instructions"
EOF