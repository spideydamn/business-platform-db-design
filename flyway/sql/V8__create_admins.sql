CREATE TABLE IF NOT EXISTS admins (
    admin_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(user_id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    audit_log_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    action VARCHAR(255) NOT NULL,
    details TEXT,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feedbacks (
    feedback_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    type feedback_type NOT NULL,
    message TEXT NOT NULL,
    status feedback_status NOT NULL DEFAULT 'new',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS service_moderations (
    service_moderation_id SERIAL PRIMARY KEY,
    service_id INTEGER NOT NULL REFERENCES services(service_id),
    admin_id INTEGER NOT NULL REFERENCES admins(admin_id),
    status moderation_status NOT NULL DEFAULT 'pending',
    comment TEXT,
    moderated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS review_moderations (
    review_moderation_id SERIAL PRIMARY KEY,
    review_id INTEGER NOT NULL REFERENCES reviews(review_id),
    admin_id INTEGER NOT NULL REFERENCES admins(admin_id),
    status moderation_status NOT NULL DEFAULT 'pending',
    comment TEXT,
    moderated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);