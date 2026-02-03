CREATE TABLE IF NOT EXISTS notifications (
    notification_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    company_id INTEGER REFERENCES companies(company_id),
    type notification_type NOT NULL,
    message TEXT NOT NULL,
    read BOOLEAN NOT NULL DEFAULT false,
    sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS chats (
    chat_id SERIAL PRIMARY KEY,
    service_id INTEGER NOT NULL REFERENCES services(service_id),
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    UNIQUE(service_id, user_id)
);

CREATE TABLE IF NOT EXISTS messages (
    message_id SERIAL PRIMARY KEY,
    chat_id INTEGER NOT NULL REFERENCES chats(chat_id),
    is_to_service BOOLEAN NOT NULL,
    content TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT false,
    sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS reviews (
    review_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    status moderation_status NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS service_reviews (
    service_review_id SERIAL PRIMARY KEY,
    service_id INTEGER NOT NULL REFERENCES services(service_id),
    review_id INTEGER NOT NULL REFERENCES reviews(review_id),
    UNIQUE(service_id, review_id)
);

CREATE TABLE IF NOT EXISTS company_reviews (
    company_review_id SERIAL PRIMARY KEY,

    company_id INTEGER NOT NULL REFERENCES companies(company_id),
    review_id INTEGER NOT NULL REFERENCES reviews(review_id),

    UNIQUE(company_id, review_id)
);

CREATE TABLE IF NOT EXISTS review_media (
    review_media_id SERIAL PRIMARY KEY,
    review_id INTEGER NOT NULL REFERENCES reviews(review_id),
    media_id INTEGER NOT NULL REFERENCES media(media_id),
    UNIQUE(review_id, media_id)
);
