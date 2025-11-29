-- Cache Hit Rate Analytics for FitFact

-- ============================================
-- 1. Cache Effectiveness Dashboard
-- ============================================
CREATE OR REPLACE VIEW cache_effectiveness AS
SELECT 
    -- Overall metrics
    COUNT(*) as total_queries,
    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as total_hits,
    SUM(CASE WHEN NOT cache_hit THEN 1 ELSE 0 END) as total_misses,
    ROUND(100.0 * SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) as hit_rate_percent,
    
    -- Response time comparison
    AVG(CASE WHEN cache_hit THEN response_time_ms END) as avg_cached_response_ms,
    AVG(CASE WHEN NOT cache_hit THEN response_time_ms END) as avg_uncached_response_ms,
    
    -- Time saved by caching
    SUM(CASE WHEN cache_hit THEN 
        (SELECT AVG(response_time_ms) FROM user_queries WHERE NOT cache_hit) - response_time_ms 
    ELSE 0 END) as total_ms_saved
FROM user_queries;

-- ============================================
-- 2. Cache Miss Pattern Analysis
-- ============================================
CREATE OR REPLACE VIEW cache_miss_patterns AS
WITH miss_analysis AS (
    SELECT 
        query_text,
        normalized_text,
        COUNT(*) as miss_count,
        AVG(response_time_ms) as avg_response_time,
        MAX(timestamp) as last_queried
    FROM user_queries
    WHERE NOT cache_hit
    GROUP BY query_text, normalized_text
)
SELECT 
    query_text,
    normalized_text,
    miss_count,
    ROUND(avg_response_time::numeric, 2) as avg_response_ms,
    last_queried,
    CASE 
        WHEN miss_count >= 5 THEN 'HIGH_PRIORITY_CACHE'
        WHEN miss_count >= 3 THEN 'MEDIUM_PRIORITY_CACHE'
        WHEN miss_count >= 2 THEN 'LOW_PRIORITY_CACHE'
        ELSE 'MONITOR'
    END as cache_recommendation
FROM miss_analysis
ORDER BY miss_count DESC;

-- ============================================
-- 3. Query Similarity Analysis for Cache Optimization
-- ============================================
CREATE OR REPLACE VIEW query_similarity_opportunities AS
WITH query_pairs AS (
    SELECT 
        q1.query_text as query1,
        q2.query_text as query2,
        similarity(q1.query_text, q2.query_text) as similarity_score,
        q1.cache_hit as q1_cached,
        q2.cache_hit as q2_cached
    FROM user_queries q1
    CROSS JOIN user_queries q2
    WHERE q1.query_id < q2.query_id
    AND similarity(q1.query_text, q2.query_text) > 0.5
)
SELECT 
    query1,
    query2,
    ROUND(similarity_score::numeric, 3) as similarity,
    CASE 
        WHEN q1_cached AND NOT q2_cached THEN 'Q2_SHOULD_USE_Q1_CACHE'
        WHEN q2_cached AND NOT q1_cached THEN 'Q1_SHOULD_USE_Q2_CACHE'
        WHEN NOT q1_cached AND NOT q2_cached THEN 'BOTH_SHOULD_BE_CACHED'
        ELSE 'BOTH_CACHED'
    END as optimization_opportunity
FROM query_pairs
WHERE similarity_score > 0.6
ORDER BY similarity_score DESC;

-- ============================================
-- 4. Cache Hit Rate by Time Period
-- ============================================
CREATE OR REPLACE VIEW cache_hit_rate_timeline AS
WITH time_periods AS (
    SELECT 
        DATE_TRUNC('hour', timestamp) as period,
        COUNT(*) as queries,
        SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as hits
    FROM user_queries
    GROUP BY DATE_TRUNC('hour', timestamp)
)
SELECT 
    period,
    queries,
    hits,
    queries - hits as misses,
    ROUND(100.0 * hits / NULLIF(queries, 0), 2) as hit_rate_percent,
    SUM(queries) OVER (ORDER BY period) as cumulative_queries,
    SUM(hits) OVER (ORDER BY period) as cumulative_hits,
    ROUND(100.0 * SUM(hits) OVER (ORDER BY period) / 
          NULLIF(SUM(queries) OVER (ORDER BY period), 0), 2) as cumulative_hit_rate
FROM time_periods
ORDER BY period DESC;

-- ============================================
-- 5. Top Cached Responses Performance
-- ============================================
CREATE OR REPLACE VIEW cached_response_performance AS
SELECT 
    cr.response_id,
    SUBSTRING(cr.response_text, 1, 100) || '...' as response_preview,
    cr.times_served,
    cr.last_served,
    uq.query_text as original_query,
    COUNT(DISTINCT rc.paper_id) as papers_cited,
    ROUND(AVG(uf.rating)::numeric, 2) as avg_user_rating
FROM cached_responses cr
JOIN user_queries uq ON cr.query_id = uq.query_id
LEFT JOIN response_citations rc ON cr.response_id = rc.response_id
LEFT JOIN user_feedback uf ON cr.response_id = uf.response_id
GROUP BY cr.response_id, cr.response_text, cr.times_served, cr.last_served, uq.query_text
ORDER BY cr.times_served DESC;

-- ============================================
-- 6. Cache Memory Usage Analysis
-- ============================================
CREATE OR REPLACE VIEW cache_memory_analysis AS
SELECT 
    COUNT(*) as total_cached_responses,
    SUM(LENGTH(response_text)) as total_bytes,
    ROUND(SUM(LENGTH(response_text)) / 1024.0, 2) as total_kb,
    ROUND(SUM(LENGTH(response_text)) / 1048576.0, 2) as total_mb,
    AVG(LENGTH(response_text)) as avg_response_size_bytes,
    MIN(LENGTH(response_text)) as min_response_size,
    MAX(LENGTH(response_text)) as max_response_size,
    AVG(times_served) as avg_times_served,
    SUM(LENGTH(response_text))::FLOAT / NULLIF(SUM(times_served), 0) as bytes_per_serve
FROM cached_responses;

-- ============================================
-- Function: Get Cache Recommendations
-- ============================================
CREATE OR REPLACE FUNCTION get_cache_recommendations()
RETURNS TABLE(
    recommendation TEXT,
    priority TEXT,
    details TEXT
) AS $$
DECLARE
    current_hit_rate FLOAT;
    stale_count INT;
BEGIN
    -- Calculate current hit rate
    SELECT 100.0 * SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0)
    INTO current_hit_rate
    FROM user_queries
    WHERE timestamp > NOW() - INTERVAL '7 days';
    
    -- Count stale cache entries
    SELECT COUNT(*)
    INTO stale_count
    FROM cached_responses
    WHERE last_served < NOW() - INTERVAL '30 days';
    
    RETURN QUERY
    SELECT 
        'Improve Cache Hit Rate'::TEXT,
        'HIGH'::TEXT,
        ('Current: ' || COALESCE(ROUND(current_hit_rate, 2), 0) || '%. Target: 60%+')::TEXT
    WHERE COALESCE(current_hit_rate, 0) < 60;
    
    RETURN QUERY
    SELECT 
        'Cache Frequently Missed Query'::TEXT,
        'HIGH'::TEXT,
        ('Query "' || SUBSTRING(query_text, 1, 50) || '..." missed ' || COUNT(*)::TEXT || ' times')::TEXT
    FROM user_queries
    WHERE NOT cache_hit
    GROUP BY query_text
    HAVING COUNT(*) >= 3
    LIMIT 5;
    
    RETURN QUERY
    SELECT 
        'Review Stale Cache'::TEXT,
        'MEDIUM'::TEXT,
        (stale_count || ' cached responses unused for 30+ days')::TEXT
    WHERE stale_count > 0;
    
    RETURN;
END;
$$ LANGUAGE plpgsql;