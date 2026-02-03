CREATE TABLE IF NOT EXISTS services (
    service_id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(company_id),
    category_id INTEGER NOT NULL REFERENCES categories(category_id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    status moderation_status NOT NULL DEFAULT 'pending',
    cancel_deadline INTEGER,
    edit_deadline INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS service_contacts (
    service_contact_id SERIAL PRIMARY KEY,
    service_id INTEGER NOT NULL REFERENCES services(service_id),
    contact_id INTEGER NOT NULL REFERENCES contacts(contact_id),
    UNIQUE(service_id, contact_id)
);

CREATE TABLE IF NOT EXISTS service_addresses (
    service_address_id SERIAL PRIMARY KEY,
    service_id INTEGER NOT NULL REFERENCES services(service_id),
    address_id INTEGER NOT NULL REFERENCES addresses(address_id),
    UNIQUE(service_id, address_id)
);

CREATE TABLE IF NOT EXISTS service_tags (
    service_tag_id SERIAL PRIMARY KEY,
    service_id INTEGER NOT NULL REFERENCES services(service_id),
    tag_id INTEGER NOT NULL REFERENCES tags(tag_id),
    UNIQUE(service_id, tag_id)
);

CREATE TABLE IF NOT EXISTS service_media (
    service_media_id SERIAL PRIMARY KEY,
    service_id INTEGER NOT NULL REFERENCES services(service_id),
    media_id INTEGER NOT NULL REFERENCES media(media_id),
    UNIQUE(service_id, media_id)
);

CREATE TABLE IF NOT EXISTS time_slots (
    time_slot_id SERIAL PRIMARY KEY,
    service_id INTEGER NOT NULL REFERENCES services(service_id),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    is_available BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS bookings (
    booking_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    service_id INTEGER NOT NULL REFERENCES services(service_id),
    time_slot_id INTEGER NOT NULL REFERENCES time_slots(time_slot_id),
    status booking_status NOT NULL DEFAULT 'new',
    address_id INTEGER NOT NULL REFERENCES addresses(address_id),
    comment TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS promo_codes (
    promo_code_id SERIAL PRIMARY KEY,
    service_id INTEGER NOT NULL REFERENCES services(service_id),
    code VARCHAR(50) UNIQUE NOT NULL,
    discount_type discount_type NOT NULL,
    discount_value DECIMAL(5,2) NOT NULL,
    min_amount DECIMAL(10,2),
    valid_from TIMESTAMP NOT NULL,
    valid_to TIMESTAMP NOT NULL
);