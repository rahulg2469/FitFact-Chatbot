-- FitFact Database Schema

-- 1. Research Papers Table
CREATE TABLE research_papers (
    paper_id SERIAL PRIMARY KEY,
    pmid VARCHAR(20) UNIQUE NOT NULL,
    doi VARCHAR(100),
    title TEXT NOT NULL,
    abstract TEXT,
    authors TEXT,
    publication_date DATE,
    journal_name VARCHAR(255),
    study_type VARCHAR(50),
    quality_score DECIMAL(3,2),
    times_used INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    search_vector tsvector
);

-- 2. User Queries Table
CREATE TABLE user_queries (
    query_id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    normalized_text TEXT,
    query_hash VARCHAR(64),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    detected_topic VARCHAR(100),
    response_time_ms INT,
    cache_hit BOOLEAN DEFAULT FALSE
);

-- 3. Topics Table
CREATE TABLE topics (
    topic_id SERIAL PRIMARY KEY,
    topic_name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Query Synonyms Table
CREATE TABLE query_synonyms (
    synonym_id SERIAL PRIMARY KEY,
    original_term VARCHAR(100) NOT NULL,
    normalized_term VARCHAR(100) NOT NULL,
    similarity_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. API Call Log Table
CREATE TABLE api_call_log (
    call_id SERIAL PRIMARY KEY,
    api_name VARCHAR(50),
    endpoint VARCHAR(255),
    query_params TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_time_ms INT,
    status_code INT,
    tokens_used INT,
    cost_usd DECIMAL(8,4),
    error_message TEXT
);

-- 6. Cached Responses Table
CREATE TABLE cached_responses (
    response_id SERIAL PRIMARY KEY,
    query_id INT REFERENCES user_queries(query_id),
    response_text TEXT NOT NULL,
    response_hash VARCHAR(64),
    confidence_score DECIMAL(3,2),
    claude_model VARCHAR(50),
    total_tokens INT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    times_served INT DEFAULT 1,
    last_served TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Response Citations Table
CREATE TABLE response_citations (
    response_id INT REFERENCES cached_responses(response_id) ON DELETE CASCADE,
    paper_id INT REFERENCES research_papers(paper_id) ON DELETE CASCADE,
    citation_order INT,
    relevance_rank INT,
    snippet TEXT,
    PRIMARY KEY (response_id, paper_id)
);

-- 8. Paper Topics Table
CREATE TABLE paper_topics (
    paper_id INT REFERENCES research_papers(paper_id) ON DELETE CASCADE,
    topic_id INT REFERENCES topics(topic_id) ON DELETE CASCADE,
    relevance_score DECIMAL(3,2),
    PRIMARY KEY (paper_id, topic_id)
);

-- 9. User Feedback Table
CREATE TABLE user_feedback (
    feedback_id SERIAL PRIMARY KEY,
    response_id INT REFERENCES cached_responses(response_id),
    rating INT CHECK (rating BETWEEN 1 AND 5),
    is_helpful BOOLEAN,
    feedback_text TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. Performance Metrics Table
CREATE TABLE performance_metrics (
    metric_id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    total_queries INT DEFAULT 0,
    cache_hits INT DEFAULT 0,
    cache_hit_rate DECIMAL(5,2),
    avg_response_time_ms INT,
    successful_responses INT DEFAULT 0,
    failed_responses INT DEFAULT 0,
    avg_user_rating DECIMAL(3,2),
    unique_papers_used INT DEFAULT 0,
    api_calls_pubmed INT DEFAULT 0,
    api_calls_claude INT DEFAULT 0,
    total_cost_usd DECIMAL(8,4)
);