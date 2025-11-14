-- Database Optimization & Cleanup Scripts for FitFact
-- Week 3 - Maintenance and Performance
-- Author: Satya Harish

-- ============================================
-- 1. Automated Cleanup Procedures
-- ============================================

-- Function to clean up old data
CREATE OR REPLACE FUNCTION cleanup_old_data(days_to_keep INT DEFAULT 90)
RETURNS TABLE(
    deleted_queries INT,
    deleted_responses INT,
    deleted_papers INT,
    deleted_logs INT
) AS $$
DECLARE
    del_queries INT := 0;
    del_responses INT := 0;
    del_papers INT := 0;
    del_logs INT := 0;
BEGIN
    -- Clean old API logs
    DELETE FROM api_call_log 
    WHERE timestamp < CURRENT_TIMESTAMP - (days_to_keep || ' days')::INTERVAL;
    GET DIAGNOSTICS del_logs = ROW_COUNT;
    
    -- Clean orphaned cached responses
    DELETE FROM cached_responses
    WHERE query_id NOT IN (SELECT query_id FROM user_queries);
    GET DIAGNOSTICS del_responses = ROW_COUNT;
    
    -- Clean unused papers (not cited and not accessed recently)
    DELETE FROM research_papers
    WHERE paper_id NOT IN (SELECT DISTINCT paper_id FROM response_citations)
    AND last_accessed < CURRENT_TIMESTAMP - (days_to_keep || ' days')::INTERVAL
    AND times_used < 5;
    GET DIAGNOSTICS del_papers = ROW_COUNT;
    
    RETURN QUERY SELECT del_queries, del_responses, del_papers, del_logs;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 2. Database Maintenance Routine
-- ============================================

CREATE OR REPLACE FUNCTION perform_maintenance()
RETURNS TABLE(
    task TEXT,
    status TEXT,
    details TEXT
) AS $$
BEGIN
    -- Update statistics
    ANALYZE;
    RETURN QUERY SELECT 'Update Statistics'::TEXT, 'COMPLETED'::TEXT, 'Statistics updated for query planner'::TEXT;
    
    -- Reindex tables with heavy updates
    REINDEX TABLE user_queries;
    RETURN QUERY SELECT 'Reindex user_queries'::TEXT, 'COMPLETED'::TEXT, 'Indexes rebuilt'::TEXT;
    
    REINDEX TABLE cached_responses;
    RETURN QUERY SELECT 'Reindex cached_responses'::TEXT, 'COMPLETED'::TEXT, 'Indexes rebuilt'::TEXT;
    
    -- Update performance metrics
    INSERT INTO performance_metrics (
        date, total_queries, cache_hits, cache_hit_rate, avg_response_time_ms
    )
    SELECT 
        CURRENT_DATE,
        COUNT(*),
        SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END),
        ROUND(100.0 * SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::NUMERIC / NULLIF(COUNT(*), 0), 2),
        ROUND(AVG(response_time_ms)::NUMERIC, 2)
    FROM user_queries
    WHERE DATE(timestamp) = CURRENT_DATE
    ON CONFLICT (date) DO UPDATE SET
        total_queries = EXCLUDED.total_queries,
        cache_hits = EXCLUDED.cache_hits,
        cache_hit_rate = EXCLUDED.cache_hit_rate,
        avg_response_time_ms = EXCLUDED.avg_response_time_ms;
    
    RETURN QUERY SELECT 'Update Metrics'::TEXT, 'COMPLETED'::TEXT, 'Daily metrics updated'::TEXT;
    
    RETURN;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 3. Cache Optimization Function
-- ============================================

CREATE OR REPLACE FUNCTION optimize_cache()
RETURNS TABLE(
    optimization TEXT,
    items_affected INT,
    description TEXT
) AS $$
DECLARE
    promoted INT := 0;
    evicted INT := 0;
BEGIN
    -- Promote frequently accessed papers to priority cache
    UPDATE research_papers
    SET quality_score = LEAST(quality_score + 0.1, 1.0)
    WHERE times_used >= 20
    AND quality_score < 1.0;
    GET DIAGNOSTICS promoted = ROW_COUNT;
    
    RETURN QUERY 
    SELECT 
        'Promoted Popular Papers'::TEXT, 
        promoted, 
        'Increased quality score for frequently used papers'::TEXT;
    
    -- Evict least recently used cache entries if cache is too large
    WITH cache_size AS (
        SELECT COUNT(*) as total FROM cached_responses
    )
    DELETE FROM cached_responses
    WHERE response_id IN (
        SELECT response_id 
        FROM cached_responses
        WHERE last_served < CURRENT_TIMESTAMP - INTERVAL '60 days'
        ORDER BY last_served ASC
        LIMIT GREATEST((SELECT total FROM cache_size) - 1000, 0)
    );
    GET DIAGNOSTICS evicted = ROW_COUNT;
    
    RETURN QUERY 
    SELECT 
        'Evicted Stale Cache'::TEXT, 
        evicted, 
        'Removed least recently used cache entries'::TEXT;
    
    RETURN;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 4. Query Performance Analysis
-- ============================================

CREATE OR REPLACE FUNCTION analyze_slow_queries()
RETURNS TABLE(
    query_pattern TEXT,
    occurrence_count BIGINT,
    avg_time_ms NUMERIC,
    recommendation TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        CASE 
            WHEN query_text LIKE '%protein%' THEN 'Protein-related'
            WHEN query_text LIKE '%creatine%' THEN 'Creatine-related'
            WHEN query_text LIKE '%cardio%' OR query_text LIKE '%hiit%' THEN 'Cardio-related'
            WHEN query_text LIKE '%muscle%' OR query_text LIKE '%strength%' THEN 'Strength-related'
            ELSE 'General fitness'
        END as pattern,
        COUNT(*),
        ROUND(AVG(response_time_ms)::NUMERIC, 2),
        CASE 
            WHEN AVG(response_time_ms) > 5000 THEN 'Critical - Consider pre-caching'
            WHEN AVG(response_time_ms) > 2000 THEN 'Slow - Optimize query or add index'
            ELSE 'Acceptable'
        END
    FROM user_queries
    WHERE response_time_ms IS NOT NULL
    GROUP BY pattern
    ORDER BY AVG(response_time_ms) DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 5. Database Health Check
-- ============================================

CREATE OR REPLACE VIEW database_health AS
SELECT 
    'Database Size' as metric,
    pg_size_pretty(pg_database_size(current_database())) as value,
    CASE 
        WHEN pg_database_size(current_database()) > 1073741824 THEN 'WARNING: >1GB'
        ELSE 'OK'
    END as status
UNION ALL
SELECT 
    'Total Tables',
    COUNT(*)::TEXT,
    'OK'
FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
UNION ALL
SELECT 
    'Total Indexes',
    COUNT(*)::TEXT,
    CASE 
        WHEN COUNT(*) < 20 THEN 'WARNING: Few indexes'
        ELSE 'OK'
    END
FROM pg_indexes WHERE schemaname = 'public'
UNION ALL
SELECT 
    'Cache Size (MB)',
    ROUND(SUM(LENGTH(response_text)) / 1048576.0, 2)::TEXT,
    CASE 
        WHEN SUM(LENGTH(response_text)) > 104857600 THEN 'WARNING: >100MB'
        ELSE 'OK'
    END
FROM cached_responses;