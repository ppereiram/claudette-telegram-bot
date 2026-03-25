-- ============================================================
-- Claudette Knowledge Base — Schema PostgreSQL
-- Ejecutar UNA VEZ en la BD de Render:
--   psql $DATABASE_URL -f kb_schema.sql
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Tabla principal
CREATE TABLE IF NOT EXISTS documents (
    id               UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    filepath         VARCHAR(500) UNIQUE NOT NULL,
    title            VARCHAR(200) NOT NULL,
    content          TEXT         NOT NULL,
    content_vector   TSVECTOR     NOT NULL,
    tags             TEXT[]       DEFAULT '{}',
    metadata         JSONB        DEFAULT '{}',
    word_count       INTEGER      DEFAULT 0,
    created_at       TIMESTAMP    DEFAULT NOW(),
    updated_at       TIMESTAMP    DEFAULT NOW(),
    file_modified_at TIMESTAMP,
    is_active        BOOLEAN      DEFAULT TRUE
);

-- Links internos (grafo de conocimiento)
CREATE TABLE IF NOT EXISTS document_links (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_doc_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    target_doc_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    link_text     VARCHAR(200),
    link_type     VARCHAR(50) DEFAULT 'internal',
    created_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_doc_id, target_doc_id, link_text)
);

-- Sesiones de aprendizaje (self-learning loop — futuro)
CREATE TABLE IF NOT EXISTS learning_sessions (
    id                   UUID      PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_start        TIMESTAMP DEFAULT NOW(),
    session_end          TIMESTAMP,
    topics_discussed     TEXT[],
    documents_referenced UUID[],
    insights_generated   TEXT,
    effectiveness_score  INTEGER,
    metadata             JSONB DEFAULT '{}'
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_documents_fts     ON documents USING GIN(content_vector);
CREATE INDEX IF NOT EXISTS idx_documents_tags    ON documents USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_documents_path    ON documents(filepath);
CREATE INDEX IF NOT EXISTS idx_documents_active  ON documents(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_documents_updated ON documents(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_links_source      ON document_links(source_doc_id);
CREATE INDEX IF NOT EXISTS idx_links_target      ON document_links(target_doc_id);

-- Trigger: actualiza content_vector y updated_at automáticamente
-- (columna explícita — correcto para Render, sin IMMUTABLE en GIN)
CREATE OR REPLACE FUNCTION update_content_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.content_vector := to_tsvector(
        'spanish',
        COALESCE(NEW.title, '') || ' ' ||
        COALESCE(NEW.content, '') || ' ' ||
        COALESCE(array_to_string(NEW.tags, ' '), '')
    );
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_content_vector ON documents;
CREATE TRIGGER trigger_update_content_vector
    BEFORE INSERT OR UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_content_vector();

-- Vista limpia para consultas (sin ranking hardcodeado — el ranking va en cada query)
CREATE OR REPLACE VIEW kb_docs AS
SELECT id, filepath, title, content, tags, metadata, word_count, created_at, updated_at
FROM documents
WHERE is_active = TRUE;

-- Verificación:
-- SELECT COUNT(*) FROM documents;
-- SELECT title, word_count FROM kb_docs ORDER BY updated_at DESC LIMIT 5;
