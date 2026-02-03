CREATE TABLE IF NOT EXISTS companies (
    company_id SERIAL PRIMARY KEY,

    name VARCHAR(255) NOT NULL,
    owner_id INTEGER NOT NULL REFERENCES users(user_id),
    category_id INTEGER REFERENCES categories(category_id),
    email VARCHAR(255) NOT NULL,

    is_verified BOOLEAN NOT NULL DEFAULT false,
    is_blocked BOOLEAN NOT NULL DEFAULT false,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS company_contacts (
    company_contact_id SERIAL PRIMARY KEY,

    company_id INTEGER NOT NULL REFERENCES companies(company_id),
    contact_id INTEGER NOT NULL REFERENCES contacts(contact_id),

    UNIQUE(company_id, contact_id)
);

CREATE TABLE IF NOT EXISTS company_addresses (
    company_address_id SERIAL PRIMARY KEY,

    company_id INTEGER NOT NULL REFERENCES companies(company_id),
    address_id INTEGER NOT NULL REFERENCES addresses(address_id),

    UNIQUE(company_id, address_id)
);

CREATE TABLE IF NOT EXISTS company_categories (
    company_category_id SERIAL PRIMARY KEY,

    company_id INTEGER NOT NULL REFERENCES companies(company_id),
    category_id INTEGER NOT NULL REFERENCES categories(category_id),

    UNIQUE(company_id, category_id)
);

CREATE TABLE IF NOT EXISTS company_tags (
    company_tag_id SERIAL PRIMARY KEY,

    company_id INTEGER NOT NULL REFERENCES companies(company_id),
    tag_id INTEGER NOT NULL REFERENCES tags(tag_id),

    UNIQUE(company_id, tag_id)
);

CREATE TABLE IF NOT EXISTS company_media (
    company_media_id SERIAL PRIMARY KEY,

    company_id INTEGER NOT NULL REFERENCES companies(company_id),
    media_id INTEGER NOT NULL REFERENCES media(media_id),

    UNIQUE(company_id, media_id)
);

CREATE TABLE IF NOT EXISTS company_balances (
    company_balance_id SERIAL PRIMARY KEY,

    company_id INTEGER NOT NULL REFERENCES companies(company_id),
    balance DECIMAL(15,2) NOT NULL DEFAULT 0.00,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    document_id SERIAL PRIMARY KEY,

    company_id INTEGER NOT NULL REFERENCES companies(company_id),
    type doc_type NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    verified BOOLEAN NOT NULL DEFAULT false,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS permissions (
    permission_id SERIAL PRIMARY KEY,

    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS roles (
    role_id SERIAL PRIMARY KEY,

    company_id INTEGER NOT NULL REFERENCES companies(company_id),
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    name VARCHAR(50) NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(company_id, user_id)
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_permission_id SERIAL PRIMARY KEY,
    
    role_id INTEGER NOT NULL REFERENCES roles(role_id),
    permission_id INTEGER NOT NULL REFERENCES permissions(permission_id),

    UNIQUE(role_id, permission_id)
);

