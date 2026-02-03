from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncpg
import os
import asyncio
import logging
from prometheus_client import make_asgi_app, Counter, Histogram
from typing import List, Dict, Any
import functools

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus метрики
REQUEST_COUNT = Counter(
    'service_requests_total',
    'Total number of requests',
    ['endpoint']
)
REQUEST_DURATION = Histogram(
    'service_request_duration_seconds',
    'Request duration in seconds',
    ['endpoint']
)
DB_QUERY_DURATION = Histogram(
    'service_db_query_duration_seconds',
    'Database query duration in seconds',
    ['query_name']
)

# Конфигурация
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "postgres"),
    "port": os.getenv("DB_PORT", 5432),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация пула подключений
    app.state.pool = await asyncpg.create_pool(
        min_size=5,
        max_size=20,
        **DB_CONFIG
    )
    logger.info("Database connection pool created")
    yield
    # Очистка при завершении
    await app.state.pool.close()
    logger.info("Database connection pool closed")

app = FastAPI(lifespan=lifespan)
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_db():
    async with app.state.pool.acquire() as connection:
        yield connection

# Декоратор для измерения времени выполнения запросов
def track_request(endpoint_name):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            REQUEST_COUNT.labels(endpoint=endpoint_name).inc()
            with REQUEST_DURATION.labels(endpoint=endpoint_name).time():
                return await func(*args, **kwargs)
        return wrapper
    return decorator

# Декоратор для измерения времени выполнения SQL-запросов
def track_query(query_name):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            with DB_QUERY_DURATION.labels(query_name=query_name).time():
                return await func(*args, **kwargs)
        return wrapper
    return decorator

@app.get("/")
@track_request("healthcheck")
async def healthcheck():
    return {"status": "ok"}

@app.get("/services/search")
@track_request("search_services")
async def search_services(
    category_id: int = None,
    min_price: float = None,
    max_price: float = None,
    rating: float = None,
    db=Depends(get_db)
):
    """
    Поиск услуг с фильтрами по категории, цене и рейтингу.
    Сложный запрос с несколькими JOIN и фильтрами.
    """
    query = """
    SELECT 
        s.service_id,
        s.name,
        s.description,
        s.price,
        c.name AS company_name,
        cat.name AS category_name,
        COALESCE(AVG(r.rating), 0) AS avg_rating,
        COUNT(r.review_id) AS reviews_count
    FROM services s
    JOIN companies c ON s.company_id = c.company_id
    JOIN categories cat ON s.category_id = cat.category_id
    LEFT JOIN service_reviews sr ON s.service_id = sr.service_id
    LEFT JOIN reviews r ON sr.review_id = r.review_id
    WHERE 
        ($1::INT IS NULL OR s.category_id = $1)
        AND ($2::FLOAT IS NULL OR s.price >= $2)
        AND ($3::FLOAT IS NULL OR s.price <= $3)
        AND ($4::FLOAT IS NULL OR (
            SELECT AVG(r2.rating) 
            FROM service_reviews sr2
            JOIN reviews r2 ON sr2.review_id = r2.review_id
            WHERE sr2.service_id = s.service_id
        ) >= $4)
    GROUP BY s.service_id, c.name, cat.name
    ORDER BY s.price
    LIMIT 100
    """
    
    results = await execute_query(
        "search_services", db, query, 
        category_id, min_price, max_price, rating
    )
    return {"results": results}

@app.get("/companies/{company_id}/details")
@track_request("company_details")
async def get_company_details(company_id: int, db=Depends(get_db)):
    """
    Получение детальной информации о компании:
    - Основная информация
    - Баланс
    - Документы
    - Услуги с рейтингом
    - Отзывы
    """
    # Запрос 1: Основная информация о компании
    company_query = """
    SELECT 
        c.company_id,
        c.name,
        c.email,
        c.is_verified,
        cb.balance,
        json_agg(DISTINCT ct.value) AS contacts,
        json_agg(DISTINCT a.location) AS addresses
    FROM companies c
    LEFT JOIN company_balances cb ON c.company_id = cb.company_id
    LEFT JOIN company_contacts cc ON c.company_id = cc.company_id
    LEFT JOIN contacts ct ON cc.contact_id = ct.contact_id
    LEFT JOIN company_addresses ca ON c.company_id = ca.company_id
    LEFT JOIN addresses a ON ca.address_id = a.address_id
    WHERE c.company_id = $1
    GROUP BY c.company_id, cb.balance
    """
    
    # Запрос 2: Услуги компании с рейтингом
    services_query = """
    SELECT 
        s.service_id,
        s.name,
        s.price,
        cat.name AS category,
        COALESCE(AVG(r.rating), 0) AS avg_rating
    FROM services s
    JOIN categories cat ON s.category_id = cat.category_id
    LEFT JOIN service_reviews sr ON s.service_id = sr.service_id
    LEFT JOIN reviews r ON sr.review_id = r.review_id
    WHERE s.company_id = $1
    GROUP BY s.service_id, cat.name
    ORDER BY avg_rating DESC
    LIMIT 10
    """
    
    # Запрос 3: Отзывы о компании
    reviews_query = """
    SELECT 
        r.review_id,
        r.rating,
        r.comment,
        u.full_name AS user_name,
        json_agg(rm.url) AS media_urls
    FROM company_reviews cr
    JOIN reviews r ON cr.review_id = r.review_id
    JOIN users u ON r.user_id = u.user_id
    LEFT JOIN review_media rev_med ON r.review_id = rev_med.review_id
    LEFT JOIN media rm ON rev_med.media_id = rm.media_id
    WHERE cr.company_id = $1
    GROUP BY r.review_id, u.full_name
    ORDER BY r.rating DESC
    LIMIT 5
    """
    
    company_info = await execute_query(
        "company_info", db, company_query, company_id
    )
    services = await execute_query(
        "company_services", db, services_query, company_id
    )
    reviews = await execute_query(
        "company_reviews", db, reviews_query, company_id
    )
    
    if not company_info:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {
        "company": company_info[0],
        "services": services,
        "reviews": reviews
    }

@app.get("/users/{user_id}/activity")
@track_request("user_activity")
async def get_user_activity(user_id: int, db=Depends(get_db)):
    """
    Получение активности пользователя:
    - История заказов
    - Избранные компании и услуги
    - История поиска
    - Уведомления
    """
    # Запрос 1: История заказов
    bookings_query = """
    SELECT 
        b.booking_id,
        s.name AS service_name,
        c.name AS company_name,
        b.status,
        t.start_time,
        t.end_time,
        p.status AS payment_status,
        p.amount
    FROM bookings b
    JOIN services s ON b.service_id = s.service_id
    JOIN companies c ON s.company_id = c.company_id
    JOIN time_slots t ON b.time_slot_id = t.time_slot_id
    LEFT JOIN payments p ON b.booking_id = p.booking_id
    WHERE b.user_id = $1
    ORDER BY t.start_time DESC
    LIMIT 10
    """
    
    # Запрос 2: Избранное
    favorites_query = """
    (
        SELECT 
            'company' AS type,
            c.company_id AS id,
            c.name AS name,
            NULL AS price
        FROM favorite_companies fc
        JOIN companies c ON fc.company_id = c.company_id
        WHERE fc.user_id = $1
        LIMIT 5
    )
    UNION ALL
    (
        SELECT 
            'service' AS type,
            s.service_id AS id,
            s.name AS name,
            s.price AS price
        FROM favorite_services fs
        JOIN services s ON fs.service_id = s.service_id
        WHERE fs.user_id = $1
        LIMIT 5
    )
    """
    
    # Запрос 3: История поиска
    search_history_query = """
    SELECT query, MAX(search_time) AS last_searched
    FROM search_histories
    WHERE user_id = $1
    GROUP BY query
    ORDER BY last_searched DESC
    LIMIT 10
    """
    
    # Запрос 4: Уведомления
    notifications_query = """
    SELECT 
        notification_id,
        type,
        message,
        created_at,
        read
    FROM notifications
    WHERE user_id = $1
    ORDER BY created_at DESC
    LIMIT 10
    """
    
    bookings = await execute_query(
        "user_bookings", db, bookings_query, user_id
    )
    favorites = await execute_query(
        "user_favorites", db, favorites_query, user_id
    )
    search_history = await execute_query(
        "user_search_history", db, search_history_query, user_id
    )
    notifications = await execute_query(
        "user_notifications", db, notifications_query, user_id
    )
    
    return {
        "bookings": bookings,
        "favorites": favorites,
        "search_history": search_history,
        "notifications": notifications
    }

@app.get("/analytics/top-companies")
@track_request("top_companies")
async def get_top_companies(
    min_rating: float = 4.0,
    min_services: int = 5,
    db=Depends(get_db)
):
    """
    Аналитика: топ компаний по количеству услуг и рейтингу.
    Сложный запрос с агрегацией и несколькими JOIN.
    """
    query = """
    WITH company_stats AS (
        SELECT
            c.company_id,
            c.name,
            COUNT(DISTINCT s.service_id) AS services_count,
            COALESCE(AVG(r.rating), 0) AS avg_rating,
            COUNT(DISTINCT r.review_id) AS reviews_count,
            SUM(CASE WHEN b.status = 'completed' THEN 1 ELSE 0 END) AS completed_bookings,
            COALESCE(SUM(p.amount), 0) AS total_revenue
        FROM companies c
        LEFT JOIN services s ON c.company_id = s.company_id
        LEFT JOIN company_reviews cr ON c.company_id = cr.company_id
        LEFT JOIN reviews r ON cr.review_id = r.review_id
        LEFT JOIN bookings b ON s.service_id = b.service_id
        LEFT JOIN payments p ON b.booking_id = p.booking_id AND p.status = 'completed'
        GROUP BY c.company_id
    )
    SELECT *
    FROM company_stats
    WHERE 
        avg_rating >= $1
        AND services_count >= $2
    ORDER BY 
        total_revenue DESC, 
        avg_rating DESC
    LIMIT 20
    """
    
    results = await execute_query(
        "top_companies", db, query, min_rating, min_services
    )
    return {"results": results}

@app.get("/geo/nearby-services")
@track_request("nearby_services")
async def get_nearby_services(
    lat: float,
    lon: float,
    radius_km: float = 10,
    db=Depends(get_db)
):
    """
    Поиск услуг рядом с заданными координатами.
    Использует PostGIS функции для работы с геоданными.
    """
    query = """
    SELECT
        s.service_id,
        s.name,
        s.price,
        c.name AS company_name,
        a.location,
        ST_DistanceSphere(
            ST_MakePoint($1, $2),
            a.coordinates
        ) / 1000 AS distance_km,
        COALESCE(AVG(r.rating), 0) AS avg_rating
    FROM services s
    JOIN companies c ON s.company_id = c.company_id
    JOIN service_addresses sa ON s.service_id = sa.service_id
    JOIN addresses a ON sa.address_id = a.address_id
    LEFT JOIN service_reviews sr ON s.service_id = sr.service_id
    LEFT JOIN reviews r ON sr.review_id = r.review_id
    WHERE ST_DWithin(
        a.coordinates::geography,
        ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography,
        $3 * 1000
    )
    GROUP BY s.service_id, c.name, a.location, a.coordinates
    HAVING ST_DistanceSphere(
        ST_MakePoint($1, $2),
        a.coordinates
    ) / 1000 <= $3
    ORDER BY distance_km, avg_rating DESC
    LIMIT 50
    """
    
    results = await execute_query(
        "nearby_services", db, query, lon, lat, radius_km
    )
    return {"results": results}

@app.get("/admin/moderation-queue")
@track_request("moderation_queue")
async def get_moderation_queue(
    entity_type: str = "service", 
    status: str = "pending",
    db=Depends(get_db)
):
    """
    Очередь модерации для администраторов.
    Комбинирует данные из разных таблиц модерации.
    """
    if entity_type == "service":
        query = """
        SELECT
            sm.service_moderation_id AS id,
            'service' AS type,
            s.name,
            sm.status,
            sm.comment AS moderation_comment,
            a.admin_id,
            u.full_name AS admin_name,
            sm.created_at
        FROM service_moderations sm
        JOIN services s ON sm.service_id = s.service_id
        LEFT JOIN admins a ON sm.admin_id = a.admin_id
        LEFT JOIN users u ON a.user_id = u.user_id
        WHERE sm.status = $1
        ORDER BY sm.created_at DESC
        LIMIT 50
        """
    elif entity_type == "review":
        query = """
        SELECT
            rm.review_moderation_id AS id,
            'review' AS type,
            r.comment AS content,
            rm.status,
            rm.comment AS moderation_comment,
            a.admin_id,
            u.full_name AS admin_name,
            rm.created_at
        FROM review_moderations rm
        JOIN reviews r ON rm.review_id = r.review_id
        LEFT JOIN admins a ON rm.admin_id = a.admin_id
        LEFT JOIN users u ON a.user_id = u.user_id
        WHERE rm.status = $1
        ORDER BY rm.created_at DESC
        LIMIT 50
        """
    else:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    results = await execute_query(
        "moderation_queue", db, query, status
    )
    return {"results": results}

@track_query("execute_query")
async def execute_query(
    query_name: str, 
    db, 
    sql: str, 
    *params
) -> List[Dict[str, Any]]:
    try:
        logger.info(f"Executing query: {query_name}")
        rows = await db.fetch(sql, *params)
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Query {query_name} failed: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Database error: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)