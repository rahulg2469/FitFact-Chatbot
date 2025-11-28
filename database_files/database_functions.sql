-- FitFact Database Functions
-- Created: Week 1 - Database Foundation
-- Purpose: Helper functions for cache management

-- Full-text search trigger
CREATE OR REPLACE FUNCTION papers_search_trigger() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.abstract, '')), 'B');
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

-- Drop trigger if exists, then create it
DROP TRIGGER IF EXISTS update_papers_search ON research_papers;
CREATE TRIGGER update_papers_search 
BEFORE INSERT OR UPDATE ON research_papers 
FOR EACH ROW EXECUTE FUNCTION papers_search_trigger();

-- Increment paper usage
CREATE OR REPLACE FUNCTION increment_paper_usage(p_pmid VARCHAR)
RETURNS void AS $$
BEGIN
    UPDATE research_papers 
    SET times_used = times_used + 1,
        last_accessed = CURRENT_TIMESTAMP
    WHERE pmid = p_pmid;
END;
$$ LANGUAGE plpgsql;

-- Find cached response with fuzzy matching
CREATE OR REPLACE FUNCTION find_cached_response(query_text_input TEXT)
RETURNS TABLE(response_id INT, response_text TEXT, similarity REAL) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cr.response_id,
        cr.response_text,
        similarity(uq.query_text, query_text_input) as sim
    FROM user_queries uq
    JOIN cached_responses cr ON uq.query_id = cr.query_id
    WHERE similarity(uq.query_text, query_text_input) > 0.5
    ORDER BY similarity(uq.query_text, query_text_input) DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;