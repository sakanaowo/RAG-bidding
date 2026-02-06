--
-- PostgreSQL database dump
--

\restrict 5Xf0joMuG6OutFGKmyL7QhTayNaZDkav0xvvrnsrdG81MHOnlBC9NBtahvGfkUt

-- Dumped from database version 18.1 (Ubuntu 18.1-1.pgdg24.04+2)
-- Dumped by pg_dump version 18.1 (Ubuntu 18.1-1.pgdg24.04+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- Name: processing_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.processing_status AS ENUM (
    'pending',
    'classifying',
    'preprocessing',
    'chunking',
    'embedding',
    'storing',
    'completed',
    'failed'
);


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


--
-- Name: update_upload_jobs_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_upload_jobs_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: citations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.citations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    message_id uuid NOT NULL,
    document_id uuid NOT NULL,
    chunk_id uuid NOT NULL,
    citation_number integer NOT NULL,
    citation_text text,
    relevance_score numeric(5,4),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: conversations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conversations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    title character varying(500),
    summary text,
    rag_mode character varying(50) DEFAULT 'balanced'::character varying,
    category_filter text[],
    message_count integer DEFAULT 0,
    total_tokens integer DEFAULT 0,
    total_cost_usd numeric(10,4) DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    last_message_at timestamp without time zone,
    deleted_at timestamp without time zone
);


--
-- Name: document_chunks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_chunks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    chunk_id character varying(255) NOT NULL,
    document_id uuid NOT NULL,
    content text NOT NULL,
    chunk_index integer NOT NULL,
    section_title character varying(500),
    hierarchy_path text[],
    keywords text[],
    concepts text[],
    entities jsonb,
    char_count integer,
    has_table boolean DEFAULT false,
    has_list boolean DEFAULT false,
    is_complete_unit boolean DEFAULT true,
    retrieval_count integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: document_upload_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_upload_jobs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    upload_id character varying(36) NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    total_files integer NOT NULL,
    completed_files integer DEFAULT 0 NOT NULL,
    failed_files integer DEFAULT 0 NOT NULL,
    progress_data jsonb,
    options jsonb,
    error_message text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    completed_at timestamp without time zone,
    files_data jsonb,
    extracted_metadata jsonb,
    admin_metadata jsonb,
    storage_path text,
    uploaded_by uuid,
    confirmed_by uuid,
    confirmed_at timestamp without time zone,
    cancelled_at timestamp without time zone,
    cancel_reason text
);


--
-- Name: TABLE document_upload_jobs; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.document_upload_jobs IS 'Tracks upload job status persistently across workers';


--
-- Name: COLUMN document_upload_jobs.id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.document_upload_jobs.id IS 'Primary key';


--
-- Name: COLUMN document_upload_jobs.upload_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.document_upload_jobs.upload_id IS 'Client-facing upload ID';


--
-- Name: COLUMN document_upload_jobs.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.document_upload_jobs.status IS 'Current processing status';


--
-- Name: COLUMN document_upload_jobs.total_files; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.document_upload_jobs.total_files IS 'Total number of files in this upload batch';


--
-- Name: COLUMN document_upload_jobs.completed_files; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.document_upload_jobs.completed_files IS 'Number of successfully processed files';


--
-- Name: COLUMN document_upload_jobs.failed_files; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.document_upload_jobs.failed_files IS 'Number of failed files';


--
-- Name: COLUMN document_upload_jobs.progress_data; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.document_upload_jobs.progress_data IS 'Detailed progress for each file (file_id, filename, status, progress_percent, error_message, etc.)';


--
-- Name: COLUMN document_upload_jobs.options; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.document_upload_jobs.options IS 'Processing options (chunk_size, chunk_overlap, enable_enrichment, etc.)';


--
-- Name: COLUMN document_upload_jobs.error_message; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.document_upload_jobs.error_message IS 'Overall error message if job failed';


--
-- Name: COLUMN document_upload_jobs.created_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.document_upload_jobs.created_at IS 'When the upload was initiated';


--
-- Name: COLUMN document_upload_jobs.updated_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.document_upload_jobs.updated_at IS 'Last update timestamp';


--
-- Name: COLUMN document_upload_jobs.completed_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.document_upload_jobs.completed_at IS 'When processing completed/failed';


--
-- Name: COLUMN document_upload_jobs.files_data; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.document_upload_jobs.files_data IS 'Array of file info: file_id, filename, file_path, size_bytes, content_type, extracted_text_preview';


--
-- Name: COLUMN document_upload_jobs.extracted_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.document_upload_jobs.extracted_metadata IS 'Auto-extracted metadata from files: detected_type, confidence, title, keywords, etc.';


--
-- Name: COLUMN document_upload_jobs.admin_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.document_upload_jobs.admin_metadata IS 'Admin-edited/confirmed metadata: document_type, category, custom fields';


--
-- Name: COLUMN document_upload_jobs.storage_path; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.document_upload_jobs.storage_path IS 'Permanent storage path for uploaded files: data/uploads/{upload_id}/';


--
-- Name: COLUMN document_upload_jobs.uploaded_by; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.document_upload_jobs.uploaded_by IS 'User who uploaded the files';


--
-- Name: COLUMN document_upload_jobs.confirmed_by; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.document_upload_jobs.confirmed_by IS 'Admin who confirmed the upload for processing';


--
-- Name: COLUMN document_upload_jobs.confirmed_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.document_upload_jobs.confirmed_at IS 'When admin confirmed for processing';


--
-- Name: COLUMN document_upload_jobs.cancelled_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.document_upload_jobs.cancelled_at IS 'When upload was cancelled';


--
-- Name: COLUMN document_upload_jobs.cancel_reason; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.document_upload_jobs.cancel_reason IS 'Reason for cancellation';


--
-- Name: documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documents (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    document_id character varying(255),
    document_name character varying(500),
    filename character varying(255),
    filepath character varying(500),
    source_file text,
    category character varying(100) DEFAULT 'Khác'::character varying NOT NULL,
    document_type character varying(50),
    uploaded_by uuid,
    file_hash character varying(64),
    file_size_bytes bigint,
    total_chunks integer DEFAULT 0,
    metadata jsonb,
    status character varying(50) DEFAULT 'active'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: feedback; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.feedback (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    message_id uuid NOT NULL,
    feedback_type character varying(50),
    rating integer,
    comment text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: langchain_pg_collection; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.langchain_pg_collection (
    uuid uuid NOT NULL,
    name character varying NOT NULL,
    cmetadata json
);


--
-- Name: langchain_pg_embedding; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.langchain_pg_embedding (
    id character varying DEFAULT (gen_random_uuid())::text NOT NULL,
    collection_id uuid,
    embedding public.vector(1536),
    document text,
    cmetadata jsonb,
    chunk_id uuid,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.messages (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    conversation_id uuid NOT NULL,
    user_id uuid NOT NULL,
    role character varying(20) NOT NULL,
    content text NOT NULL,
    sources jsonb,
    processing_time_ms integer,
    tokens_total integer,
    feedback_rating integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    rag_mode character varying(50)
);


--
-- Name: COLUMN messages.rag_mode; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.messages.rag_mode IS 'RAG mode used: fast, balanced, quality, adaptive';


--
-- Name: queries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.queries (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    conversation_id uuid,
    message_id uuid,
    query_text text NOT NULL,
    query_hash character varying(64),
    rag_mode character varying(50),
    categories_searched text[],
    retrieval_count integer,
    total_latency_ms integer,
    tokens_total integer,
    estimated_cost_usd numeric(10,6),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    input_tokens integer,
    output_tokens integer
);


--
-- Name: COLUMN queries.input_tokens; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.queries.input_tokens IS 'Number of input/prompt tokens';


--
-- Name: COLUMN queries.output_tokens; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.queries.output_tokens IS 'Number of output/completion tokens';


--
-- Name: user_usage_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_usage_metrics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    date date NOT NULL,
    total_queries integer DEFAULT 0,
    total_messages integer DEFAULT 0,
    total_tokens bigint DEFAULT 0,
    total_cost_usd numeric(10,4) DEFAULT 0,
    categories_accessed text[],
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    total_input_tokens bigint,
    total_output_tokens bigint
);


--
-- Name: COLUMN user_usage_metrics.total_input_tokens; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_usage_metrics.total_input_tokens IS 'Total input tokens consumed';


--
-- Name: COLUMN user_usage_metrics.total_output_tokens; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_usage_metrics.total_output_tokens IS 'Total output tokens consumed';


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email character varying(255) NOT NULL,
    username character varying(100),
    password_hash character varying(255),
    full_name character varying(255),
    role character varying(50) DEFAULT 'user'::character varying,
    oauth_provider character varying(50),
    oauth_id character varying(255),
    preferences jsonb DEFAULT '{}'::jsonb,
    is_active boolean DEFAULT true,
    is_verified boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    deleted_at timestamp without time zone
);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: citations citations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.citations
    ADD CONSTRAINT citations_pkey PRIMARY KEY (id);


--
-- Name: conversations conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_pkey PRIMARY KEY (id);


--
-- Name: document_chunks document_chunks_chunk_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_chunk_id_key UNIQUE (chunk_id);


--
-- Name: document_chunks document_chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_pkey PRIMARY KEY (id);


--
-- Name: document_upload_jobs document_upload_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_upload_jobs
    ADD CONSTRAINT document_upload_jobs_pkey PRIMARY KEY (id);


--
-- Name: document_upload_jobs document_upload_jobs_upload_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_upload_jobs
    ADD CONSTRAINT document_upload_jobs_upload_id_key UNIQUE (upload_id);


--
-- Name: documents documents_document_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_document_id_key UNIQUE (document_id);


--
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);


--
-- Name: feedback feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_pkey PRIMARY KEY (id);


--
-- Name: langchain_pg_collection langchain_pg_collection_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.langchain_pg_collection
    ADD CONSTRAINT langchain_pg_collection_name_key UNIQUE (name);


--
-- Name: langchain_pg_collection langchain_pg_collection_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.langchain_pg_collection
    ADD CONSTRAINT langchain_pg_collection_pkey PRIMARY KEY (uuid);


--
-- Name: langchain_pg_embedding langchain_pg_embedding_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.langchain_pg_embedding
    ADD CONSTRAINT langchain_pg_embedding_pkey PRIMARY KEY (id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- Name: queries queries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.queries
    ADD CONSTRAINT queries_pkey PRIMARY KEY (id);


--
-- Name: user_usage_metrics user_usage_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_usage_metrics
    ADD CONSTRAINT user_usage_metrics_pkey PRIMARY KEY (id);


--
-- Name: user_usage_metrics user_usage_metrics_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_usage_metrics
    ADD CONSTRAINT user_usage_metrics_unique UNIQUE (user_id, date);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: idx_document_chunks_document; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_document_chunks_document ON public.document_chunks USING btree (document_id);


--
-- Name: idx_document_chunks_fts; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_document_chunks_fts ON public.document_chunks USING gin (to_tsvector('english'::regconfig, content));


--
-- Name: idx_documents_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_category ON public.documents USING btree (category) WHERE ((status)::text = 'active'::text);


--
-- Name: idx_documents_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_status ON public.documents USING btree (status);


--
-- Name: idx_documents_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_type ON public.documents USING btree (document_type);


--
-- Name: idx_documents_uploader; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_uploader ON public.documents USING btree (uploaded_by);


--
-- Name: idx_langchain_pg_embedding_vector; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_langchain_pg_embedding_vector ON public.langchain_pg_embedding USING hnsw (embedding public.vector_cosine_ops) WITH (m='16', ef_construction='64');


--
-- Name: idx_users_oauth; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_oauth ON public.users USING btree (oauth_provider, oauth_id);


--
-- Name: idx_users_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_role ON public.users USING btree (role) WHERE (deleted_at IS NULL);


--
-- Name: ix_upload_jobs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_upload_jobs_created_at ON public.document_upload_jobs USING btree (created_at);


--
-- Name: ix_upload_jobs_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_upload_jobs_status ON public.document_upload_jobs USING btree (status);


--
-- Name: ix_upload_jobs_upload_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_upload_jobs_upload_id ON public.document_upload_jobs USING btree (upload_id);


--
-- Name: ix_upload_jobs_uploaded_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_upload_jobs_uploaded_by ON public.document_upload_jobs USING btree (uploaded_by);


--
-- Name: document_upload_jobs trigger_update_upload_jobs_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_update_upload_jobs_updated_at BEFORE UPDATE ON public.document_upload_jobs FOR EACH ROW EXECUTE FUNCTION public.update_upload_jobs_updated_at();


--
-- Name: users trigger_users_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: citations citations_chunk_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.citations
    ADD CONSTRAINT citations_chunk_id_fkey FOREIGN KEY (chunk_id) REFERENCES public.document_chunks(id) ON DELETE CASCADE;


--
-- Name: citations citations_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.citations
    ADD CONSTRAINT citations_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: citations citations_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.citations
    ADD CONSTRAINT citations_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.messages(id) ON DELETE CASCADE;


--
-- Name: conversations conversations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: document_chunks document_chunks_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: documents documents_uploaded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES public.users(id);


--
-- Name: feedback feedback_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.messages(id) ON DELETE CASCADE;


--
-- Name: feedback feedback_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: langchain_pg_embedding langchain_pg_embedding_chunk_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.langchain_pg_embedding
    ADD CONSTRAINT langchain_pg_embedding_chunk_id_fkey FOREIGN KEY (chunk_id) REFERENCES public.document_chunks(id) ON DELETE SET NULL;


--
-- Name: messages messages_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id) ON DELETE CASCADE;


--
-- Name: messages messages_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: queries queries_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.queries
    ADD CONSTRAINT queries_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id) ON DELETE SET NULL;


--
-- Name: queries queries_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.queries
    ADD CONSTRAINT queries_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.messages(id) ON DELETE SET NULL;


--
-- Name: queries queries_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.queries
    ADD CONSTRAINT queries_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: user_usage_metrics user_usage_metrics_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_usage_metrics
    ADD CONSTRAINT user_usage_metrics_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict 5Xf0joMuG6OutFGKmyL7QhTayNaZDkav0xvvrnsrdG81MHOnlBC9NBtahvGfkUt

