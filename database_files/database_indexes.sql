-- FitFact Database Indexes

-- Research Papers Indexes
CREATE INDEX idx_papers_pmid ON research_papers(pmid);
CREATE INDEX idx_papers_quality ON research_papers(quality_score DESC);
CREATE INDEX idx_papers_used ON research_papers(times_used DESC);
CREATE INDEX idx_papers_date ON research_papers(publication_date DESC);
CREATE INDEX idx_papers_search ON research_papers USING gin(search_vector);

-- User Queries Indexes
CREATE INDEX idx_queries_timestamp ON user_queries(timestamp DESC);
CREATE INDEX idx_queries_hash ON user_queries(query_hash);
CREATE INDEX idx_queries_cache ON user_queries(cache_hit);
CREATE INDEX idx_queries_text_fts ON user_queries USING gin(to_tsvector('english', query_text));

-- Other Table Indexes
CREATE INDEX idx_synonyms_original ON query_synonyms(original_term);
CREATE INDEX idx_synonyms_normalized ON query_synonyms(normalized_term);
CREATE INDEX idx_api_timestamp ON api_call_log(timestamp DESC);
CREATE INDEX idx_api_name ON api_call_log(api_name);
CREATE INDEX idx_responses_query ON cached_responses(query_id);
CREATE INDEX idx_responses_hash ON cached_responses(response_hash);
CREATE INDEX idx_responses_served ON cached_responses(times_served DESC);
CREATE INDEX idx_citations_response ON response_citations(response_id);
CREATE INDEX idx_citations_paper ON response_citations(paper_id);
CREATE INDEX idx_paper_topics_paper ON paper_topics(paper_id);
CREATE INDEX idx_paper_topics_topic ON paper_topics(topic_id);
CREATE INDEX idx_feedback_response ON user_feedback(response_id);
CREATE INDEX idx_feedback_rating ON user_feedback(rating);
CREATE INDEX idx_metrics_date ON performance_metrics(date DESC);