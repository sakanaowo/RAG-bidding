# 🧪 PERFORMANCE TESTING GUIDE

**Comprehensive performance testing suite cho RAG Bidding System**

---

## 📋 OVERVIEW

Test suite này đánh giá 3 khía cạnh quan trọng của hệ thống:

1. **Query Latency** - Response time của các RAG modes
2. **Cache Effectiveness** - Hiệu quả của caching system  
3. **Multi-User Load** - Khả năng xử lý concurrent users

---

## 🚀 QUICK START

### **Prerequisites**
```bash
# Ensure server is running
./start_server.sh

# Install required packages (if not already installed)
conda activate venv
pip install aiohttp requests
```

### **Run All Tests**
```bash
# Full test suite (15-25 minutes)
python scripts/tests/performance/run_performance_tests.py

# Quick test mode (5-10 minutes)  
python scripts/tests/performance/run_performance_tests.py --quick

# Custom configuration
python scripts/tests/performance/run_performance_tests.py \
  --query-runs 5 \
  --max-users 20 \
  --output logs/my_performance_report.json
```

---

## 📊 INDIVIDUAL TESTS

### **1. Query Latency Test**
```bash
python scripts/tests/performance/test_query_latency.py --runs 3
```

**What it tests:**
- Response time của fast/balanced/quality/adaptive modes
- Performance consistency across different query types
- System stability under sequential queries

**Expected Results:**
- Fast mode: <1s average
- Balanced mode: 1-3s average  
- Quality mode: 2-5s average
- Adaptive mode: Variable based on query complexity

### **2. Cache Effectiveness Test**
```bash
python scripts/tests/performance/test_cache_effectiveness.py --threads 4
```

**What it tests:**
- Cold vs warm cache performance
- Cache hit patterns với similar queries
- Concurrent cache access performance

**Expected Results:**
- Cache speedup: 2-5x faster for repeated queries
- Cache effectiveness: >70% of queries benefit
- No cache contention under concurrent load

### **3. Multi-User Load Test**
```bash
# Escalating load test
python scripts/tests/performance/test_multi_user_queries.py --escalating --max-users 20

# Fixed load test
python scripts/tests/performance/test_multi_user_queries.py --users 10 --queries 3
```

**What it tests:**
- Maximum concurrent user capacity
- System breaking point identification
- Throughput và error rates under load

**Expected Results:**
- Stable performance: 10+ concurrent users
- Breaking point: >15 users (depends on hardware)
- Throughput: 5+ queries/second under load

---

## 📈 INTERPRETING RESULTS

### **Performance Indicators**

| Metric | Good | Acceptable | Poor |
|--------|------|------------|------|
| **Avg Response Time** | <2s | 2-5s | >5s |
| **Cache Speedup** | >3x | 1.5-3x | <1.5x |
| **Concurrent Users** | >15 | 10-15 | <10 |
| **Success Rate** | >99% | 95-99% | <95% |
| **Throughput** | >10 qps | 5-10 qps | <5 qps |

### **Status Classifications**

**✅ PERFORMING_WELL:**
- All metrics within "Good" range
- No critical bottlenecks identified
- System ready for production load

**⚠️ OPTIMIZATION_NEEDED:**
- Some metrics in "Acceptable" range
- Minor bottlenecks identified
- Performance tuning recommended

**❌ CRITICAL_ISSUES_FOUND:**
- Multiple metrics in "Poor" range
- Major bottlenecks blocking scalability
- Immediate fixes required

---

## 🔧 TROUBLESHOOTING

### **Common Issues**

**Server Connection Errors:**
```bash
# Check server status
curl http://localhost:8000/health

# Restart server if needed
./start_server.sh
```

**Test Timeout Issues:**
```bash
# Use smaller test parameters
python run_performance_tests.py --quick --max-users 5
```

**Memory/Resource Issues:**
```bash
# Monitor system resources
htop

# Reduce concurrent load
python test_multi_user_queries.py --users 5 --queries 2
```

### **Performance Debugging**

**High Response Times:**
- Check database connection pooling
- Review query optimization
- Monitor LLM API latency

**Low Cache Effectiveness:**
- Verify Redis configuration
- Check cache TTL settings
- Review query similarity patterns

**Low Concurrent Capacity:**
- Implement connection pooling (see CONNECTION_POOLING_STRATEGY.md)
- Increase database max_connections
- Optimize resource usage

---

## 📋 TEST SCENARIOS

### **Development Testing**
```bash
# Quick validation during development
python run_performance_tests.py --quick
```

### **Pre-Production Validation**
```bash
# Comprehensive testing before deployment
python run_performance_tests.py --query-runs 5 --max-users 25
```

### **Production Monitoring**
```bash
# Regular performance monitoring
python run_performance_tests.py --max-users 10 --output logs/prod_health_check.json
```

### **Load Testing**
```bash
# Stress testing for capacity planning
python test_multi_user_queries.py --escalating --max-users 50
```

---

## 📊 SAMPLE RESULTS

### **Good Performance Example**
```json
{
  "overall_status": "performing_well",
  "key_metrics": {
    "fastest_query_mode": "fast",
    "best_avg_response_time_ms": 850,
    "avg_cache_speedup": 4.2,
    "cache_hit_effectiveness": 0.85,
    "max_concurrent_users": 18,
    "max_stable_qps": 15.3
  },
  "priority_recommendations": [
    "GOOD: System handles concurrent load well"
  ]
}
```

### **Issues Detected Example**
```json
{
  "overall_status": "critical_issues_found", 
  "bottlenecks_identified": [
    "Low concurrent user capacity - Connection pooling needed",
    "High query latency (>3s) - Database optimization needed"
  ],
  "priority_recommendations": [
    "CRITICAL: Implement database connection pooling",
    "HIGH: Optimize database queries and consider query optimization"
  ]
}
```

---

## 🎯 PERFORMANCE TARGETS

### **Production Targets**

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Response Time** | <2s average | 95th percentile |
| **Throughput** | >10 QPS | Sustained load |
| **Concurrent Users** | >20 users | Stable performance |
| **Uptime** | >99.9% | Error rate |
| **Cache Hit Rate** | >70% | Repeated queries |

### **Scalability Targets**

- **Small Scale**: 5-10 concurrent users
- **Medium Scale**: 20-50 concurrent users  
- **Large Scale**: 100+ concurrent users (với connection pooling)

---

## 🔍 MONITORING RECOMMENDATIONS

### **Regular Testing Schedule**
- **Daily**: Quick health checks
- **Weekly**: Comprehensive performance validation
- **Monthly**: Full load testing và capacity planning
- **Pre-deployment**: Complete test suite execution

### **Alerting Thresholds**
- Response time >3s: Warning
- Response time >5s: Critical
- Success rate <95%: Warning
- Success rate <90%: Critical
- Concurrent capacity <10: Warning

---

## 📚 RELATED DOCUMENTATION

- [Connection Pooling Strategy](../../documents/technical/CONNECTION_POOLING_STRATEGY.md)
- [System Architecture](../../documents/technical/PIPELINE_INTEGRATION_SUMMARY.md)
- [Database Setup](../../documents/setup/DATABASE_SETUP.md)
- [API Documentation](http://localhost:8000/docs)

---

**Version**: 1.0  
**Last Updated**: November 6, 2025  
**Compatibility**: RAG Bidding System v2.0+