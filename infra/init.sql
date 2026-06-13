-- PostgreSQL schema — document embeddings handled by ChromaDB, not here.

-- Users & Settings
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Research Sessions
CREATE TABLE IF NOT EXISTS research_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    query TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    agent_states JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent Results
CREATE TABLE IF NOT EXISTS agent_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    result JSONB DEFAULT '{}',
    status TEXT DEFAULT 'pending',
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Final Reports
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE,
    company_name TEXT,
    report_json JSONB DEFAULT '{}',
    pdf_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Risk Scores
CREATE TABLE IF NOT EXISTS risk_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    score FLOAT NOT NULL,
    evidence JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sample user
INSERT INTO users (email, name) VALUES ('demo@intel.ai', 'Demo User')
ON CONFLICT DO NOTHING;
