import os
import psycopg2
from faker import Faker
import random
import sys
import traceback
from datetime import timedelta
from collections import defaultdict
from prometheus_client import start_http_server, Counter, Histogram, Gauge
import time

# Количество вставленных строк по таблицам
SEED_ROWS_INSERTED = Counter(
    'seeder_rows_inserted_total', 
    'Total inserted rows', 
    ['table']
)
# Количество ошибок
SEED_ERRORS = Counter(
    'seeder_errors_total', 
    'Total seeding errors'
)
# Время выполнения сидирования
SEED_DURATION = Histogram(
    'seeder_duration_seconds', 
    'Seeding duration in seconds',
    ['status']
)
# Время обработки каждой таблицы
SEED_TABLE_DURATION = Histogram(
    'seeder_table_duration_seconds',
    'Duration per table seeding',
    ['table', 'status']
)
# Статус подключения к БД
DB_CONNECTION_STATUS = Gauge(
    'seeder_db_connection_status',
    'Database connection status (1 = success, 0 = failure)'
)
# Количество успешно заполненных таблиц
TABLES_SEEDED = Gauge(
    'seeder_tables_seeded_total',
    'Total tables seeded'
)

start_http_server(8000)

MIGRATION_VERSION = int(os.getenv("MIGRATION_VERSION", "1"))

APP_ENV = os.getenv("APP_ENV", "prod")
if APP_ENV != "dev":
    print("Skipping seed: not in dev environment")
    sys.exit(0)

SEED_COUNT = int(os.getenv("SEED_COUNT", 100))

faker = Faker()

# Настройка подключения к PostgreSQL
try:
    start_time = time.time()
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    conn.autocommit = False  # Ручное управление транзакциями
    cur = conn.cursor()
    DB_CONNECTION_STATUS.set(1)
    connect_time = time.time() - start_time
    SEED_DURATION.labels(status='connection').observe(connect_time)
    print(f"Database connected in {connect_time:.2f} seconds")
except Exception as e:
    DB_CONNECTION_STATUS.set(0)
    SEED_ERRORS.inc()
    print(f"Database connection error: {e}")
    sys.exit(1)

# Словарь соответствия таблиц и их первичных ключей
ID_COLUMNS = {
    'contacts': 'contact_id',
    'addresses': 'address_id',
    'categories': 'category_id',
    'tags': 'tag_id',
    'media': 'media_id',
    'users': 'user_id',
    'passports': 'passport_id',
    'user_contacts': 'user_contact_id',
    'user_addresses': 'user_address_id',
    'phone_change_requests': 'phone_change_request_id',
    'external_accounts': 'external_account_id',
    'password_reset_tokens': 'password_reset_token_id',
    'companies': 'company_id',
    'company_contacts': 'company_contact_id',
    'company_addresses': 'company_address_id',
    'company_categories': 'company_category_id',
    'company_tags': 'company_tag_id',
    'company_media': 'company_media_id',
    'company_balances': 'company_balance_id',
    'documents': 'document_id',
    'permissions': 'permission_id',
    'roles': 'role_id',
    'role_permissions': 'role_permission_id',
    'services': 'service_id',
    'service_contacts': 'service_contact_id',
    'service_addresses': 'service_address_id',
    'service_tags': 'service_tag_id',
    'service_media': 'service_media_id',
    'time_slots': 'time_slot_id',
    'bookings': 'booking_id',
    'promo_codes': 'promo_code_id',
    'favorite_companies': 'favorite_company_id',
    'favorite_services': 'favorite_service_id',
    'search_histories': 'search_history_id',
    'notifications': 'notification_id',
    'chats': 'chat_id',
    'messages': 'message_id',
    'reviews': 'review_id',
    'service_reviews': 'service_review_id',
    'company_reviews': 'company_review_id',
    'review_media': 'review_media_id',
    'payment_methods': 'payment_method_id',
    'payments': 'payment_id',
    'withdrawals': 'withdrawal_id',
    'admins': 'admin_id',
    'audit_logs': 'audit_log_id',
    'feedbacks': 'feedback_id',
    'service_moderations': 'service_moderation_id',
    'review_moderations': 'review_moderation_id'
}

def get_unique_constraints() -> dict:
    """
    Возвращает словарь UNIQUE_CONSTRAINTS: {table_name: [column1, column2, ...], ...}
    учитывая составные уникальные ключи.
    """
    query = """
    SELECT
        tc.table_name,
        tc.constraint_name,
        kcu.column_name,
        kcu.ordinal_position
    FROM
        information_schema.table_constraints AS tc
    JOIN
        information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    WHERE
        tc.constraint_type = 'UNIQUE'
        AND tc.table_schema = 'public'
    ORDER BY
        tc.table_name, tc.constraint_name, kcu.ordinal_position
    """
    try:
        cur.execute(query)
        rows = cur.fetchall()
    except Exception as e:
        SEED_ERRORS.inc()
        print(f"Error fetching unique constraints: {e}")
        return {}

    constraint_map = defaultdict(list)
    for table_name, constraint_name, column_name, _ in rows:
        constraint_map[(table_name, constraint_name)].append(column_name)

    # Преобразуем к нужному виду: table_name -> [columns] (одно ограничение на таблицу)
    table_constraints = defaultdict(list)
    for (table, _), columns in constraint_map.items():
        if columns not in table_constraints[table]:
            table_constraints[table].append(columns)

    # Оставим только одиночные уникальные ключи (без мульти-constraint)
    result = {
        table: columns[0] if len(columns) == 1 else columns
        for table, columns in table_constraints.items()
    }

    return result


def safe_execute(query, params=None):
    """Безопасное выполнение SQL-запросов"""
    try:
        cur.execute(query, params or ())
        return True
    except Exception as e:
        conn.rollback()
        SEED_ERRORS.inc()
        print(f"Query failed: {e}")
        return False

def table_exists(table_name):
    """Проверка существования таблицы"""
    return safe_execute(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s)",
        (table_name,)
    ) and cur.fetchone()[0]

def get_columns(table_name):
    """Получение списка колонок таблицы"""
    if safe_execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
        (table_name,)
    ):
        return [row[0] for row in cur.fetchall()]
    return []

# Инициализация кэша
cache = defaultdict(list)

UNIQUE_CONSTRAINTS = get_unique_constraints()

def filter_columns(table_name, data):
    """Фильтрует словарь данных по существующим колонкам в таблице"""
    existing_columns = get_columns(table_name)
    return {key: value for key, value in data.items() if key in existing_columns}

def seed_wrapper(table, generator):
    return lambda: filter_columns(table, generator())

def generate_user_data():
    """Генератор данных для таблицы users с поддержкой изменений столбцов"""
    if not hasattr(generate_user_data, 'existing_columns'):
        generate_user_data.existing_columns = get_columns('users')
    existing_columns = generate_user_data.existing_columns
    
    data = {
        "full_name": faker.name(),
        "phone": faker.unique.numerify('+7##########'),
    }
    
    if 'mail' in existing_columns:
        data['mail'] = faker.unique.email()
    elif 'email' in existing_columns:
        data['email'] = faker.unique.email()
    
    if 'password_hash' in existing_columns:
        data['password_hash'] = faker.sha256()
    if 'is_verified' in existing_columns:
        data['is_verified'] = random.choice([True, False])
    if 'is_passport_verified' in existing_columns:
        data['is_passport_verified'] = random.choice([True, False])
    if 'is_blocked' in existing_columns:
        data['is_blocked'] = random.choice([True, False])
    
    return data

SEED_TARGETS = {
    # V1
    "contacts": seed_wrapper("contacts", lambda: {
        "type": (contact_type := random.choice(['phone', 'email', 'social'])),
        "value": {
            'phone': faker.numerify('+7##########'),
            'email': faker.email(),
            'social': faker.url()
        }[contact_type]
    }),
    
    "addresses": seed_wrapper("addresses", lambda: {
        "location": faker.address(),
        "coordinates": f"({faker.longitude()},{faker.latitude()})"
    }),
    
    "categories": seed_wrapper("categories", lambda: {
        "name": faker.job(),
        "parent_category_id": random.choice([None] + cache['category_id'])
    }),
    
    "tags": seed_wrapper("tags", lambda: {
        "name": faker.unique.bothify(text='tag_###???')
    }),
    
    "media": seed_wrapper("media", lambda: {
        "type": random.choice(['photo', 'video']),
        "url": faker.image_url()
    }),

    # V2
    "users": seed_wrapper("users", generate_user_data),
    
    "passports": seed_wrapper("passports", lambda: {
        "user_id": random.choice(cache['user_id']),
        "passport_number": faker.unique.numerify('######'),
        "series": faker.bothify('####'),
        "issued_by": faker.company(),
        "issue_date": faker.date_between(start_date='-10y', end_date='today')
    }),
    
    "user_contacts": seed_wrapper("user_contacts", lambda: {
        "user_id": random.choice(cache['user_id']),
        "contact_id": random.choice(cache['contact_id'])
    }),
    
    "user_addresses": seed_wrapper("user_addresses", lambda: {
        "user_id": random.choice(cache['user_id']),
        "address_id": random.choice(cache['address_id'])
    }),
    
    "phone_change_requests": seed_wrapper("phone_change_requests", lambda: {
        "user_id": random.choice(cache['user_id']),
        "new_phone": faker.numerify('+7##########'),
        "status": random.choice(['pending', 'approved', 'rejected'])
    }),
    
    "external_accounts": seed_wrapper("external_accounts", lambda: {
        "user_id": random.choice(cache['user_id']),
        "provider": random.choice(['vk', 'gosuslugi', 'other']),
        "external_user_id": faker.uuid4()
    }),
    
    "password_reset_tokens": seed_wrapper("password_reset_tokens", lambda: {
        "user_id": random.choice(cache['user_id']),
        "token": faker.sha256(),
        "expires_at": faker.future_datetime(end_date='+30d'),
        "is_used": random.choice([True, False])
    }),

    # V3
    "companies": seed_wrapper("companies", lambda: {
        "name": faker.company(),
        "owner_id": random.choice(cache['user_id']),
        "category_id": random.choice(cache['category_id']),
        "email": faker.company_email(),
        "is_verified": random.choice([True, False]),
        "is_blocked": random.choice([True, False])
    }),
    
    "company_contacts": seed_wrapper("company_contacts", lambda: {
        "company_id": random.choice(cache['company_id']),
        "contact_id": random.choice(cache['contact_id'])
    }),
    
    "company_addresses": seed_wrapper("company_addresses", lambda: {
        "company_id": random.choice(cache['company_id']),
        "address_id": random.choice(cache['address_id'])
    }),
    
    "company_categories": seed_wrapper("company_categories", lambda: {
        "company_id": random.choice(cache['company_id']),
        "category_id": random.choice(cache['category_id'])
    }),
    
    "company_tags": seed_wrapper("company_tags", lambda: {
        "company_id": random.choice(cache['company_id']),
        "tag_id": random.choice(cache['tag_id'])
    }),
    
    "company_media": seed_wrapper("company_media", lambda: {
        "company_id": random.choice(cache['company_id']),
        "media_id": random.choice(cache['media_id'])
    }),
    
    "company_balances": seed_wrapper("company_balances", lambda: {
        "company_id": random.choice(cache['company_id']),
        "balance": round(random.uniform(1000, 1000000), 2)
    }),
    
    "documents": seed_wrapper("documents", lambda: {
        "company_id": random.choice(cache['company_id']),
        "type": random.choice(['passport', 'company_registration']),
        "file_path": faker.file_path(),
        "verified": random.choice([True, False])
    }),
    
    "permissions": seed_wrapper("permissions", lambda: {
        "code": faker.unique.bothify('perm_????_####'),
        "description": faker.sentence()
    }),
    
    "roles": seed_wrapper("roles", lambda: {
        "company_id": random.choice(cache['company_id']),
        "user_id": random.choice(cache['user_id']),
        "name": faker.job()[:50]
    }),
    
    "role_permissions": seed_wrapper("role_permissions", lambda: {
        "role_id": random.choice(cache['role_id']),
        "permission_id": random.choice(cache['permission_id'])
    }),

    # V4
    "services": seed_wrapper("services", lambda: {
        "company_id": random.choice(cache['company_id']),
        "category_id": random.choice(cache['category_id']),
        "name": faker.catch_phrase(),
        "description": faker.text(),
        "price": round(random.uniform(100, 10000), 2),
        "status": random.choice(['pending', 'approved', 'rejected']),
        "cancel_deadline": random.randint(1, 30),
        "edit_deadline": random.randint(1, 30)
    }),
    
    "service_contacts": seed_wrapper("service_contacts", lambda: {
        "service_id": random.choice(cache['service_id']),
        "contact_id": random.choice(cache['contact_id'])
    }),
    
    "service_addresses": seed_wrapper("service_addresses", lambda: {
        "service_id": random.choice(cache['service_id']),
        "address_id": random.choice(cache['address_id'])
    }),
    
    "service_tags": seed_wrapper("service_tags", lambda: {
        "service_id": random.choice(cache['service_id']),
        "tag_id": random.choice(cache['tag_id'])
    }),
    
    "service_media": seed_wrapper("service_media", lambda: {
        "service_id": random.choice(cache['service_id']),
        "media_id": random.choice(cache['media_id'])
    }),
    
    "time_slots": seed_wrapper("time_slots", lambda: {
        "service_id": random.choice(cache['service_id']),
        "start_time": (start := faker.date_time_this_year()),
        "end_time": start + timedelta(hours=random.randint(1, 24)),
        "is_available": random.choice([True, False])
    }),
    
    "bookings": seed_wrapper("bookings", lambda: {
        "user_id": random.choice(cache['user_id']),
        "service_id": random.choice(cache['service_id']),
        "time_slot_id": random.choice(cache['time_slot_id']),
        "status": random.choice(['new', 'confirmed', 'in_progress', 'completed', 'canceled']),
        "address_id": random.choice(cache['address_id']),
        "comment": faker.sentence()
    }),
    
    "promo_codes": seed_wrapper("promo_codes", lambda: {
        "service_id": random.choice(cache['service_id']),
        "code": faker.unique.bothify('PROMO-????-####'),
        "discount_type": random.choice(['percent', 'fixed']),
        "discount_value": round(random.uniform(5, 50), 2),
        "min_amount": round(random.uniform(100, 1000), 2),
        "valid_from": faker.date_this_year(),
        "valid_to": faker.date_this_year()
    }),

    # V5
    "favorite_companies": seed_wrapper("favorite_companies", lambda: {
        "user_id": random.choice(cache['user_id']),
        "company_id": random.choice(cache['company_id'])
    }),
    
    "favorite_services": seed_wrapper("favorite_services", lambda: {
        "user_id": random.choice(cache['user_id']),
        "service_id": random.choice(cache['service_id'])
    }),
    
    "search_histories": seed_wrapper("search_histories", lambda: {
        "user_id": random.choice(cache['user_id']),
        "query": faker.sentence(nb_words=3)
    }),

    # V6
    "notifications": seed_wrapper("notifications", lambda: {
        "user_id": random.choice(cache['user_id']),
        "company_id": random.choice(cache['company_id'] + [None]),
        "type": random.choice(['system', 'booking', 'payment', 'promo']),
        "message": faker.text(),
        "read": random.choice([True, False])
    }),
    
    "chats": seed_wrapper("chats", lambda: {
        "service_id": random.choice(cache['service_id']),
        "user_id": random.choice(cache['user_id'])
    }),
    
    "messages": seed_wrapper("messages", lambda: {
        "chat_id": random.choice(cache['chat_id']),
        "is_to_service": random.choice([True, False]),
        "content": faker.text(),
        "is_read": random.choice([True, False])
    }),
    
    "reviews": seed_wrapper("reviews", lambda: {
        "user_id": random.choice(cache['user_id']),
        "rating": random.randint(1, 5),
        "comment": faker.text(),
        "status": random.choice(['pending', 'approved', 'rejected'])
    }),
    
    "service_reviews": seed_wrapper("service_reviews", lambda: {
        "service_id": random.choice(cache['service_id']),
        "review_id": random.choice(cache['review_id'])
    }),
    
    "company_reviews": seed_wrapper("company_reviews", lambda: {
        "company_id": random.choice(cache['company_id']),
        "review_id": random.choice(cache['review_id'])
    }),
    
    "review_media": seed_wrapper("review_media", lambda: {
        "review_id": random.choice(cache['review_id']),
        "media_id": random.choice(cache['media_id'])
    }),

    # V7
    "payment_methods": seed_wrapper("payment_methods", lambda: {
        "service_id": random.choice(cache['service_id']),
        "method": random.choice(['cash', 'card', 'sbp'])
    }),
    
    "payments": seed_wrapper("payments", lambda: {
        "booking_id": random.choice(cache['booking_id']),
        "amount": round(random.uniform(100, 10000), 2),
        "payment_method_id": random.choice(cache['payment_method_id']),
        "status": random.choice(['pending', 'completed', 'refused']),
        "transaction_id": faker.uuid4()
    }),
    
    "withdrawals": seed_wrapper("withdrawals", lambda: {
        "company_id": random.choice(cache['company_id']),
        "user_id": random.choice(cache['user_id']),
        "amount": round(random.uniform(1000, 100000), 2),
        "status": random.choice(['pending', 'completed', 'refused'])
    }),

    # V8
    "admins": seed_wrapper("admins", lambda: {
        "user_id": random.choice(cache['user_id'])
    }),
    
    "audit_logs": seed_wrapper("audit_logs", lambda: {
        "user_id": random.choice(cache['user_id']),
        "action": faker.sentence(nb_words=3),
        "details": faker.text()
    }),
    
    "feedbacks": seed_wrapper("feedbacks", lambda: {
        "user_id": random.choice(cache['user_id']),
        "type": random.choice(['complaint', 'suggestion']),
        "message": faker.text(),
        "status": random.choice(['new', 'ignored', 'in_progress', 'resolved'])
    }),
    
    "service_moderations": seed_wrapper("service_moderations", lambda: {
        "service_id": random.choice(cache['service_id']),
        "admin_id": random.choice(cache['admin_id']),
        "status": random.choice(['pending', 'approved', 'rejected']),
        "comment": faker.text()
    }),
    
    "review_moderations": seed_wrapper("review_moderations", lambda: {
        "review_id": random.choice(cache['review_id']),
        "admin_id": random.choice(cache['admin_id']),
        "status": random.choice(['pending', 'approved', 'rejected']),
        "comment": faker.text()
    })
}

SEED_ORDER = [
    # V1
    'contacts', 'addresses', 'categories', 'tags', 'media',
    
    # V2
    'users', 'passports', 'user_contacts', 'user_addresses',
    'phone_change_requests', 'external_accounts', 'password_reset_tokens',
    
    # V3
    'companies', 'company_contacts', 'company_addresses', 'company_categories',
    'company_tags', 'company_media', 'company_balances', 'documents',
    'permissions', 'roles', 'role_permissions',
    
    # V4
    'services', 'service_contacts', 'service_addresses', 'service_tags',
    'service_media', 'time_slots', 'bookings', 'promo_codes',
    
    # V5
    'favorite_companies', 'favorite_services', 'search_histories',
    
    # V6
    'notifications', 'chats', 'messages', 'reviews',
    'service_reviews', 'company_reviews', 'review_media',
    
    # V7
    'payment_methods', 'payments', 'withdrawals',
    
    # V8
    'admins', 'audit_logs', 'feedbacks', 'service_moderations', 'review_moderations'
]

MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", 1000))

total_start_time = time.time()
success = False
tables_seeded_count = 0

try:
    for table in SEED_ORDER:
        if table not in SEED_TARGETS:
            print(f"Skipping unknown table: {table}")
            continue

        if not table_exists(table):
            print(f"Skipping missing table: {table}")
            continue

        print(f"Seeding table: {table}")
        inserted_ids = []
        table_start_time = time.time()
        table_success = False

        try:
            for _ in range(SEED_COUNT):
                
                data = SEED_TARGETS[table]()
                if data is None:
                    continue

                unique_keys = UNIQUE_CONSTRAINTS.get(table, [])

                if unique_keys:
                    for _ in range(MAX_ATTEMPTS):
                        check = True
                        if isinstance(unique_keys[0], list):
                            for unique_key in unique_keys:
                                where_clause = " AND ".join(f"{key} = %s" for key in unique_key)
                                values_to_check = [data[key] for key in unique_key]
                                cur.execute(
                                    f"SELECT 1 FROM {table} WHERE {where_clause} LIMIT 1",
                                    values_to_check,
                                )
                                if cur.fetchone():
                                    check = False
                        else:
                            where_clause = " AND ".join(f"{key} = %s" for key in unique_keys)
                            values_to_check = [data[key] for key in unique_keys]
                            cur.execute(
                                f"SELECT 1 FROM {table} WHERE {where_clause} LIMIT 1",
                                values_to_check,
                            )
                            check = not cur.fetchone()
                        if check:
                            break  # Уникально — вставляем
                        data = SEED_TARGETS[table]()  # Перегенерируем
                        if data is None:
                            break
                    else:
                        print(f"Skipping duplicate after {MAX_ATTEMPTS} attempts: {table}")
                        continue
                
                columns = list(data.keys())
                values = [data[col] for col in columns]
                placeholders = ', '.join(['%s'] * len(columns))
                column_names = ', '.join(columns)

                query = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders}) RETURNING {ID_COLUMNS[table]}"
                cur.execute(query, values)
                returned_id = cur.fetchone()[0]
                inserted_ids.append(returned_id)

            if inserted_ids:
                cache[ID_COLUMNS[table]].extend(inserted_ids)
                SEED_ROWS_INSERTED.labels(table=table).inc(len(inserted_ids))
                print(f"Inserted {len(inserted_ids)} rows into {table}")

            conn.commit()
            table_success = True
            tables_seeded_count += 1
        
        except Exception as e:
            conn.rollback()
            SEED_ERRORS.inc()
            print(f"Error seeding table {table}: {e}")
            traceback.print_exc()
        finally:
            table_duration = time.time() - table_start_time
            status = 'success' if table_success else 'error'
            SEED_TABLE_DURATION.labels(table=table, status=status).observe(table_duration)

    success=True
    print("Seeding completed successfully.")

except Exception as e:
    conn.rollback()
    SEED_ERRORS.inc()
    print(f"Seeding failed: {e}")
    traceback.print_exc()

finally:
    total_duration = time.time() - total_start_time
    status = 'success' if success else 'error'
    SEED_DURATION.labels(status=status).observe(total_duration)
    TABLES_SEEDED.set(tables_seeded_count)
    
    if 'cur' in locals() and cur is not None:
        cur.close()
    if 'conn' in locals() and conn is not None:
        conn.close()
    
    print(f"Total seeding time: {total_duration:.2f} seconds")
    print(f"Tables seeded: {tables_seeded_count}/{len(SEED_ORDER)}")
    print(f"Metrics available at http://localhost:8000/metrics")
    
    # Оставляем процесс работающим для сбора метрик
    print("Keeping container alive for metrics collection...")
    while True:
        time.sleep(60)