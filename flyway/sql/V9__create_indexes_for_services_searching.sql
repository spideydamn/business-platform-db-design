CREATE INDEX idx_companies_company_id ON companies(company_id);
CREATE INDEX idx_company_balances_company_id ON company_balances(company_id);

CREATE INDEX idx_company_contacts_company_id ON company_contacts(company_id);
CREATE INDEX idx_contacts_contact_id ON contacts(contact_id);

CREATE INDEX idx_services_company_id ON services(company_id);
CREATE INDEX idx_services_status ON services(status);
CREATE INDEX idx_categories_category_id ON categories(category_id);

CREATE INDEX idx_service_reviews_service_id ON service_reviews(service_id);
CREATE INDEX idx_reviews_rating ON reviews(rating);
CREATE INDEX idx_company_reviews_company_id ON company_reviews(company_id);
CREATE INDEX idx_review_moderations_review_id ON review_moderations(review_id);

CREATE INDEX idx_time_slots_service_id ON time_slots(service_id);
CREATE INDEX idx_time_slots_start_time ON time_slots(start_time);
CREATE INDEX idx_bookings_time_slot_id ON bookings(time_slot_id);
CREATE INDEX idx_bookings_status ON bookings(status);

CREATE INDEX idx_service_tags_service_id ON service_tags(service_id);
CREATE INDEX idx_tags_tag_id ON tags(tag_id);

CREATE INDEX idx_review_media_review_id ON review_media(review_id);
CREATE INDEX idx_media_media_id ON media(media_id);

CREATE INDEX idx_payments_booking_id ON payments(booking_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_withdrawals_company_id ON withdrawals(company_id);
CREATE INDEX idx_payment_methods_service_id ON payment_methods(service_id);

CREATE INDEX idx_users_user_id ON users(user_id);