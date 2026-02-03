CREATE EXTENSION IF NOT EXISTS dblink;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'app_db') THEN
        PERFORM dblink_exec('dbname=postgres user=postgres password=app_password',
                            'CREATE DATABASE app_db OWNER postgres');
    END IF;
    
END
$$;

\connect app_db

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'public') THEN
        GRANT USAGE, CREATE ON SCHEMA public TO postgres;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO postgres;
    END IF;
END
$$;