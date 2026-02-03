CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,

    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,

    is_verified BOOLEAN NOT NULL DEFAULT false,
    is_passport_verified BOOLEAN NOT NULL DEFAULT false,
    is_blocked BOOLEAN NOT NULL DEFAULT false,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS passports (
    passport_id SERIAL PRIMARY KEY,

    user_id INTEGER NOT NULL REFERENCES users(user_id),
    passport_number VARCHAR(6) UNIQUE NOT NULL,
    series VARCHAR(4) NOT NULL,
    issued_by VARCHAR(255) NOT NULL,
    issue_date TIMESTAMP NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_contacts (
    user_contact_id SERIAL PRIMARY KEY,

    user_id INTEGER NOT NULL REFERENCES users(user_id),
    contact_id INTEGER NOT NULL REFERENCES contacts(contact_id),

    UNIQUE(user_id, contact_id)
);

CREATE TABLE IF NOT EXISTS user_addresses (
    user_address_id SERIAL PRIMARY KEY,

    user_id INTEGER NOT NULL REFERENCES users(user_id),
    address_id INTEGER NOT NULL REFERENCES addresses(address_id),

    UNIQUE(user_id, address_id)
);

CREATE TABLE IF NOT EXISTS phone_change_requests (
    phone_change_request_id SERIAL PRIMARY KEY,

    user_id INTEGER NOT NULL REFERENCES users(user_id),
    new_phone VARCHAR(20) NOT NULL,
    status moderation_status NOT NULL DEFAULT 'pending',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS external_accounts (
    external_account_id SERIAL PRIMARY KEY,

    user_id INTEGER NOT NULL REFERENCES users(user_id),
    provider provider_enum NOT NULL,
    external_user_id VARCHAR(255) NOT NULL,

    connected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, provider)
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    password_reset_token_id SERIAL PRIMARY KEY,

    user_id INTEGER NOT NULL REFERENCES users(user_id),
    token VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    is_used BOOLEAN NOT NULL DEFAULT false,
    
    UNIQUE(token)
);
