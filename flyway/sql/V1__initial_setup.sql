CREATE TYPE booking_status AS ENUM ('new', 'confirmed', 'in_progress', 'completed', 'canceled');
CREATE TYPE transaction_status AS ENUM ('pending', 'completed', 'refused');
CREATE TYPE moderation_status AS ENUM ('pending', 'approved', 'rejected');
CREATE TYPE feedback_status AS ENUM ('new', 'ignored', 'in_progress', 'resolved');
CREATE TYPE provider_enum AS ENUM ('vk', 'gosuslugi', 'other');
CREATE TYPE doc_type AS ENUM ('passport', 'company_registration');
CREATE TYPE discount_type AS ENUM ('percent', 'fixed');
CREATE TYPE notification_type AS ENUM ('system', 'booking', 'payment', 'promo');
CREATE TYPE message_direction AS ENUM ('to_service', 'from_service');
CREATE TYPE feedback_type AS ENUM ('complaint', 'suggestion');
CREATE TYPE media_type AS ENUM ('photo', 'video');
CREATE TYPE payment_method AS ENUM ('cash', 'card', 'sbp');
CREATE TYPE contact_type AS ENUM ('phone', 'email', 'social');


CREATE TABLE IF NOT EXISTS contacts (
    contact_id SERIAL PRIMARY KEY,
    type contact_type NOT NULL,
    value VARCHAR(255) NOT NULL,
    UNIQUE(type, value)
);

CREATE TABLE IF NOT EXISTS addresses (
    address_id SERIAL PRIMARY KEY,
    location VARCHAR(512) NOT NULL,
    coordinates POINT NOT NULL
);


CREATE TABLE IF NOT EXISTS categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    parent_category_id INTEGER REFERENCES categories(category_id)
);

CREATE TABLE IF NOT EXISTS tags (
    tag_id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL
);


CREATE TABLE IF NOT EXISTS media (
    media_id SERIAL PRIMARY KEY,
    type media_type NOT NULL,
    url VARCHAR(512) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);