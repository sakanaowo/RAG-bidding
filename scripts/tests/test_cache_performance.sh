#!/bin/bash
# Test Cache Performance - Verify 3-layer caching works

echo "=========================================="
echo "  CACHE PERFORMANCE TEST"
echo "  Testing: L1 (Memory) → L2 (Redis) → L3 (PostgreSQL)"
echo "=========================================="

API_URL="http://localhost:8000"

# Test query
QUERY="Quy định về đấu thầu công trình xây dựng"

echo ""
echo "🔍 Test Query: $QUERY"
echo ""

# Clear Redis cache trước khi test
echo "🧹 Step 1: Clear Redis cache..."
redis-cli -n 0 FLUSHDB > /dev/null
echo "✅ Redis cache cleared (DBSIZE: $(redis-cli -n 0 DBSIZE))"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 FIRST REQUEST (Cache MISS - all layers)"
echo "Expected: ~3-10s (PostgreSQL + embedding + reranking)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

START1=$(date +%s%3N)
RESPONSE1=$(curl -s -X POST "$API_URL/ask" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"$QUERY\", \"mode\": \"balanced\"}")
END1=$(date +%s%3N)
LATENCY1=$((END1 - START1))

echo "⏱️  Latency: ${LATENCY1}ms"
echo "📦 Redis after request: $(redis-cli -n 0 DBSIZE) keys"
echo ""

# Check if response valid
if echo "$RESPONSE1" | grep -q "answer"; then
    echo "✅ Response valid"
else
    echo "❌ Response invalid:"
    echo "$RESPONSE1" | head -20
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚡ SECOND REQUEST (Cache HIT - L2 Redis)"
echo "Expected: ~100-300ms (no PostgreSQL, no reranking)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

sleep 1  # Đợi Redis write xong

START2=$(date +%s%3N)
RESPONSE2=$(curl -s -X POST "$API_URL/ask" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"$QUERY\", \"mode\": \"balanced\"}")
END2=$(date +%s%3N)
LATENCY2=$((END2 - START2))

echo "⏱️  Latency: ${LATENCY2}ms"
echo "📦 Redis keys: $(redis-cli -n 0 DBSIZE)"
echo ""

if echo "$RESPONSE2" | grep -q "answer"; then
    echo "✅ Response valid"
else
    echo "❌ Response invalid"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔥 THIRD REQUEST (Cache HIT - L1 Memory)"
echo "Expected: ~50-100ms (fastest - in-process memory)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

START3=$(date +%s%3N)
RESPONSE3=$(curl -s -X POST "$API_URL/ask" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"$QUERY\", \"mode\": \"balanced\"}")
END3=$(date +%s%3N)
LATENCY3=$((END3 - START3))

echo "⏱️  Latency: ${LATENCY3}ms"
echo ""

if echo "$RESPONSE3" | grep -q "answer"; then
    echo "✅ Response valid"
else
    echo "❌ Response invalid"
    exit 1
fi

echo ""
echo "=========================================="
echo "  📊 CACHE PERFORMANCE SUMMARY"
echo "=========================================="
echo ""
echo "Request 1 (MISS):       ${LATENCY1}ms  ← L3 PostgreSQL"
echo "Request 2 (L2 HIT):     ${LATENCY2}ms  ← L2 Redis"
echo "Request 3 (L1 HIT):     ${LATENCY3}ms  ← L1 Memory"
echo ""

# Calculate speedup
SPEEDUP_L2=$(awk "BEGIN {printf \"%.1f\", $LATENCY1/$LATENCY2}")
SPEEDUP_L1=$(awk "BEGIN {printf \"%.1f\", $LATENCY1/$LATENCY3}")

echo "🚀 Speedup:"
echo "  - L2 vs L3: ${SPEEDUP_L2}x faster"
echo "  - L1 vs L3: ${SPEEDUP_L1}x faster"
echo ""

# Verify cache working
if [ $LATENCY2 -lt $((LATENCY1 / 2)) ]; then
    echo "✅ CACHE WORKING: L2 Redis significantly faster"
else
    echo "⚠️  WARNING: L2 Redis not much faster (cache may not be working)"
fi

if [ $LATENCY3 -lt $LATENCY2 ]; then
    echo "✅ CACHE WORKING: L1 Memory faster than L2"
else
    echo "⚠️  WARNING: L1 not faster (may need server restart)"
fi

echo ""
echo "🔍 Inspect Redis Cache:"
echo "  redis-cli -n 0 KEYS \"retrieval:*\""
echo "  redis-cli -n 0 TTL <key>"
echo ""
echo "=========================================="
