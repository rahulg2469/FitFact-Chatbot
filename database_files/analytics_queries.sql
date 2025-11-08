-- Report 1: Cache effectiveness by day
CREATE OR REPLACE VIEW daily_cache_performance AS
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as total_queries,
    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as hits,
    ROUND(AVG(response_time_ms)) as avg_ms,
    ROUND(100.0 * SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) / COUNT(*), 2) as hit_rate
FROM user_queries
GROUP BY DATE(timestamp)
ORDER BY date DESC;

-- Report 2: Papers ready for auto-caching (approaching threshold)
CREATE OR REPLACE VIEW auto_cache_candidates AS
SELECT pmid, title, times_used, quality_score,
    CASE 
        WHEN times_used >= 20 THEN 'AUTO-CACHE NOW'
        WHEN times_used >= 15 THEN 'APPROACHING THRESHOLD'
        ELSE 'MONITORING'
    END as status
FROM research_papers
WHERE times_used >= 10
ORDER BY times_used DESC;
