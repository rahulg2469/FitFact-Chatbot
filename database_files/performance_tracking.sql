-- Performance Tracking Queries for FitFact

-- ============================================
-- 1. Real-time System Health Dashboard
-- ============================================
CREATE OR REPLACE VIEW system_health AS
SELECT 
    -- Current performance
    (SELECT COUNT(*) FROM user_queries 
     WHERE timestamp > NOW() - INTERVAL '1 hour') as queries_last_hour,
    
    (SELECT AVG(response_time_ms) FROM user_queries 
     WHERE timestamp > NOW() - INTERVAL '1 hour') as avg_response_time_1h,
    
    (SELECT COUNT(*) FROM api_call_log 
     WHERE timestamp > NOW() - INTERVAL '1 hour') as api_calls_last_hour,
    
    -- Cache performance (fixed)
    (SELECT CASE 
        WHEN COUNT(*) = 0 THEN 0
        ELSE ROUND(100.0 * SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) / COUNT(*), 2)
     END
     FROM user_queries 
     WHERE timestamp > NOW() - INTERVAL '1 hour') as cache_hit_rate_1h,
    
    -- Database size
    (SELECT pg_size_pretty(pg_database_size(current_database()))) as database_size,
    (SELECT COUNT(*) FROM research_papers) as total_papers,
    (SELECT COUNT(*) FROM cached_responses) as total_cached_responses;

-- ============================================
-- 2. Hourly Performance Metrics
-- ============================================
CREATE OR REPLACE VIEW hourly_performance AS
SELECT 
    DATE_TRUNC('hour', timestamp) as hour,
    COUNT(*) as total_queries,
    COUNT(CASE WHEN cache_hit THEN 1 END) as cache_hits,
    ROUND(AVG(response_time_ms)::numeric, 2) as avg_response_ms,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY response_time_ms) as median_response_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms) as p95_response_ms,
    MAX(response_time_ms) as max_response_ms
FROM user_queries
GROUP BY DATE_TRUNC('hour', timestamp)
ORDER BY hour DESC;

-- ============================================
-- 3. Top Slow Queries Analysis
-- ============================================
CREATE OR REPLACE VIEW slow_queries_analysis AS
SELECT 
    query_text,
    response_time_ms,
    cache_hit,
    timestamp,
    CASE 
        WHEN response_time_ms > 5000 THEN 'CRITICAL'
        WHEN response_time_ms > 2000 THEN 'SLOW'
        WHEN response_time_ms > 1000 THEN 'MODERATE'
        ELSE 'FAST'
    END as performance_category
FROM user_queries
WHERE response_time_ms > 1000
ORDER BY response_time_ms DESC
LIMIT 100;

-- ============================================
-- 4. API Usage Patterns
-- ============================================
CREATE OR REPLACE VIEW api_usage_patterns AS
WITH hourly_calls AS (
    SELECT 
        api_name,
        DATE_TRUNC('hour', timestamp) as hour,
        COUNT(*) as calls,
        AVG(response_time_ms) as avg_response_time,
        SUM(tokens_used) as total_tokens,
        SUM(cost_usd) as total_cost
    FROM api_call_log
    GROUP BY api_name, DATE_TRUNC('hour', timestamp)
)
SELECT 
    api_name,
    hour,
    calls,
    ROUND(avg_response_time::numeric, 2) as avg_response_ms,
    total_tokens,
    ROUND(total_cost::numeric, 4) as cost_usd,
    SUM(calls) OVER (PARTITION BY api_name ORDER BY hour 
                     ROWS BETWEEN 23 PRECEDING AND CURRENT ROW) as rolling_24h_calls
FROM hourly_calls
ORDER BY hour DESC, api_name;

-- ============================================
-- 5. Paper Usage Tracking
-- ============================================
CREATE OR REPLACE VIEW paper_usage_metrics AS
SELECT 
    rp.paper_id,
    rp.pmid,
    rp.title,
    rp.times_used,
    rp.quality_score,
    rp.last_accessed,
    COUNT(DISTINCT rc.response_id) as times_cited,
    AVG(cr.times_served) as avg_cache_serves_per_citation,
    CASE 
        WHEN rp.times_used >= 20 THEN 'HOT'
        WHEN rp.times_used >= 10 THEN 'WARM'
        WHEN rp.times_used >= 5 THEN 'COOL'
        ELSE 'COLD'
    END as usage_temperature
FROM research_papers rp
LEFT JOIN response_citations rc ON rp.paper_id = rc.paper_id
LEFT JOIN cached_responses cr ON rc.response_id = cr.response_id
GROUP BY rp.paper_id
ORDER BY rp.times_used DESC;

-- ============================================
-- 6. Performance Trends (7-day moving average)
-- ============================================
CREATE OR REPLACE VIEW performance_trends AS
WITH daily_metrics AS (
    SELECT 
        DATE(timestamp) as date,
        COUNT(*) as queries,
        AVG(response_time_ms) as avg_response_time,
        COUNT(CASE WHEN cache_hit THEN 1 END)::FLOAT / COUNT(*) * 100 as cache_hit_rate
    FROM user_queries
    GROUP BY DATE(timestamp)
)
SELECT 
    date,
    queries,
    ROUND(avg_response_time::numeric, 2) as avg_response_ms,
    ROUND(cache_hit_rate::numeric, 2) as cache_hit_pct,
    ROUND(AVG(queries) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)::numeric, 2) as queries_7d_avg,
    ROUND(AVG(avg_response_time) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)::numeric, 2) as response_ms_7d_avg,
    ROUND(AVG(cache_hit_rate) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)::numeric, 2) as cache_hit_7d_avg
FROM daily_metrics
ORDER BY date DESC;