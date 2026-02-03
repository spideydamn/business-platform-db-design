import os
import time
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
from prometheus_client import start_http_server, Summary, Counter

QUERY_DURATION = Summary(
    'company_details_query_duration_seconds',
    'Time spent executing company details SQL query'
)
QUERY_TOTAL = Counter(
    'company_details_query_total',
    'Total number of company detail queries executed'
)

# Используем переменные из docker-compose окружения
DB_USER     = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST     = os.getenv('DB_HOST', 'localhost')
DB_PORT     = os.getenv('DB_PORT', '5432')
DB_NAME     = os.getenv('DB_NAME')

COMPANY_ID = int(os.getenv('SIMULATOR_COMPANY_ID', '1'))

def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        cursor_factory=RealDictCursor
    )

@QUERY_DURATION.time()
def query_company_full_details():
    """
    Получение полной информации о компании, включая услуги, контакты, отзывы и финансы.
    """
    QUERY_TOTAL.inc()
    conn = get_connection()
    try:
        cur = conn.cursor()
        full_query = """
        SELECT
            c.company_id,
            c.name AS company_name,
            c.is_verified,
            cb.balance,
            (
                SELECT json_agg(contact_info)
                FROM (
                    SELECT 
                        ct.value,
                        ct.type,
                        COUNT(cc.contact_id) OVER (PARTITION BY ct.type) AS contact_type_count
                    FROM company_contacts cc
                    JOIN contacts ct ON cc.contact_id = ct.contact_id
                    WHERE cc.company_id = c.company_id
                ) AS contact_info
            ) AS contacts,
            (
                SELECT json_agg(service_details)
                FROM (
                    SELECT
                        s.service_id,
                        s.name,
                        s.price,
                        cat.name AS category,
                        (
                            SELECT json_agg(tag_data)
                            FROM (
                                SELECT t.name
                                FROM service_tags st
                                JOIN tags t ON st.tag_id = t.tag_id
                                WHERE st.service_id = s.service_id
                            ) AS tag_data
                        ) AS tags,
                        COALESCE(avg_rating.rating, 0) AS avg_rating,
                        (
                            SELECT json_agg(time_slot)
                            FROM (
                                SELECT
                                    ts.start_time,
                                    ts.end_time,
                                    (
                                        SELECT COUNT(*)
                                        FROM bookings b
                                        WHERE b.time_slot_id = ts.time_slot_id
                                        AND b.status NOT IN ('canceled', 'completed')
                                    ) AS active_bookings
                                FROM time_slots ts
                                WHERE ts.service_id = s.service_id
                                AND ts.start_time > NOW()
                            ) AS time_slot
                        ) AS future_slots
                    FROM services s
                    JOIN categories cat ON s.category_id = cat.category_id
                    LEFT JOIN (
                        SELECT
                            sr.service_id,
                            AVG(r.rating) AS rating
                        FROM service_reviews sr
                        JOIN reviews r ON sr.review_id = r.review_id
                        GROUP BY sr.service_id
                    ) AS avg_rating ON s.service_id = avg_rating.service_id
                    WHERE s.company_id = c.company_id
                    AND s.status = 'approved'
                ) AS service_details
            ) AS services,
            (
                SELECT json_agg(review_details)
                FROM (
                    SELECT
                        r.review_id,
                        r.rating,
                        r.comment,
                        u.full_name AS user_name,
                        (
                            SELECT json_agg(media_info)
                            FROM (
                                SELECT 
                                    m.url,
                                    m.type
                                FROM review_media rm
                                JOIN media m ON rm.media_id = m.media_id
                                WHERE rm.review_id = r.review_id
                            ) AS media_info
                        ) AS media,
                        EXISTS (
                            SELECT 1
                            FROM review_moderations rm
                            WHERE rm.review_id = r.review_id
                            AND rm.status = 'approved'
                        ) AS is_moderated
                    FROM company_reviews cr
                    JOIN reviews r ON cr.review_id = r.review_id
                    JOIN users u ON r.user_id = u.user_id
                    WHERE cr.company_id = c.company_id
                    AND r.rating > 3
                ) AS review_details
            ) AS reviews,
            (
                SELECT json_agg(financial_info)
                FROM (
                    SELECT
                        SUM(p.amount) AS total_revenue,
                        (
                            SELECT SUM(w.amount)
                            FROM withdrawals w
                            WHERE w.company_id = c.company_id
                            AND w.status = 'completed'
                        ) AS total_withdrawn,
                        (
                            SELECT json_agg(payment_methods)
                            FROM (
                                SELECT
                                    pm.method,
                                    COUNT(p.payment_id) AS transaction_count
                                FROM payment_methods pm
                                LEFT JOIN payments p ON pm.payment_method_id = p.payment_method_id
                                WHERE pm.service_id IN (
                                    SELECT service_id
                                    FROM services
                                    WHERE company_id = c.company_id
                                )
                                GROUP BY pm.method
                            ) AS payment_methods
                        ) AS payment_stats
                    FROM payments p
                    JOIN bookings b ON p.booking_id = b.booking_id
                    JOIN services s ON b.service_id = s.service_id
                    WHERE s.company_id = c.company_id
                    AND p.status = 'completed'
                ) AS financial_info
            ) AS financial_data
        FROM companies c
        LEFT JOIN company_balances cb ON c.company_id = cb.company_id
        WHERE c.company_id = %s
        GROUP BY c.company_id, cb.balance;
        """
        cur.execute(full_query, (COMPANY_ID,))
        result = cur.fetchone()

        if result:
            print("Полная информация о компании:")
            print(result)
        else:
            print("Компания не найдена.")

        cur.close()
    except Exception as e:
        print("Ошибка при выполнении query_company_full_details():", e)
    finally:
        conn.close()


if __name__ == "__main__":
    start_http_server(8000)
    print("Prometheus metrics available on http://0.0.0.0:8000/metrics")

    INTERVAL_SEC = int(os.getenv("SIMULATOR_RAW_INTERVAL_SEC", "1"))
    print(f"Running single-threaded simulator; interval = {INTERVAL_SEC} seconds")

    try:
        while True:
            query_company_full_details()
            time.sleep(INTERVAL_SEC)
    except KeyboardInterrupt:
        print("Simulator interrupted, exiting…")
