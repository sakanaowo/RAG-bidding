--
-- PostgreSQL database dump
--

\restrict AxaRw6vfMfzk2vzLIqVldK9GQ7Kbf4pDaZyNL9GgClcWpl28LljJUBzEHWuwUZ8

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


SET default_tablespace = '';

SET default_table_access_method = heap;

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
-- Name: langchain_pg_embedding; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.langchain_pg_embedding (
    uuid uuid DEFAULT gen_random_uuid() NOT NULL,
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
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


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
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


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
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


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
-- Name: langchain_pg_embedding langchain_pg_embedding_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.langchain_pg_embedding
    ADD CONSTRAINT langchain_pg_embedding_pkey PRIMARY KEY (uuid);


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
-- Name: users trigger_users_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: citations citations_chunk_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.citations
    ADD CONSTRAINT citations_chunk_id_fkey FOREIGN KEY (chunk_id) REFERENCES public.document_chunks(id);


--
-- Name: citations citations_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.citations
    ADD CONSTRAINT citations_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id);


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
    ADD CONSTRAINT feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


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
    ADD CONSTRAINT messages_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: queries queries_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.queries
    ADD CONSTRAINT queries_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id);


--
-- Name: queries queries_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.queries
    ADD CONSTRAINT queries_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.messages(id);


--
-- Name: queries queries_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.queries
    ADD CONSTRAINT queries_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_usage_metrics user_usage_metrics_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_usage_metrics
    ADD CONSTRAINT user_usage_metrics_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--

\unrestrict AxaRw6vfMfzk2vzLIqVldK9GQ7Kbf4pDaZyNL9GgClcWpl28LljJUBzEHWuwUZ8

