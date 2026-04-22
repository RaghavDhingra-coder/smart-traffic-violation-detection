from typing import Optional

from psycopg2.extras import RealDictRow

try:
    from ..pg_database import db_manager
    from ..schemas.violation import ViolationCreate
except ImportError:
    from pg_database import db_manager
    from schemas.violation import ViolationCreate


def _normalize_row(row: Optional[RealDictRow]) -> Optional[dict]:
    return dict(row) if row is not None else None


def insert_violation(violation: ViolationCreate) -> dict:
    insert_query = """
    INSERT INTO violations (type, plate, timestamp, confidence, image_url, location)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id, type, plate, timestamp, confidence, image_url, location;
    """

    with db_manager.get_cursor() as (_, cursor):
        cursor.execute(
            insert_query,
            (
                violation.type,
                violation.plate,
                violation.timestamp,
                violation.confidence,
                violation.image_url,
                violation.location,
            ),
        )
        created_violation = _normalize_row(cursor.fetchone())

    if created_violation is None:
        raise RuntimeError("Failed to create violation record")

    return created_violation


def is_stolen_vehicle(plate: str) -> bool:
    stolen_lookup_query = "SELECT 1 FROM stolen_vehicles WHERE plate = %s LIMIT 1;"

    with db_manager.get_cursor() as (_, cursor):
        cursor.execute(stolen_lookup_query, (plate,))
        return cursor.fetchone() is not None


def send_over_speed_alert(plate: str) -> None:
    owner_lookup_query = "SELECT phone FROM vehicles WHERE plate = %s LIMIT 1;"

    with db_manager.get_cursor() as (_, cursor):
        cursor.execute(owner_lookup_query, (plate,))
        owner = _normalize_row(cursor.fetchone())

    if owner and owner.get("phone"):
        print("Alert sent to owner")


def fetch_all_violations() -> list[dict]:
    query = """
    SELECT id, type, plate, timestamp, confidence, image_url, location
    FROM violations
    ORDER BY timestamp DESC, id DESC;
    """

    with db_manager.get_cursor() as (_, cursor):
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]


def fetch_vehicle_violations(plate: str) -> list[dict]:
    query = """
    SELECT id, type, plate, timestamp, confidence, image_url, location
    FROM violations
    WHERE plate = %s
    ORDER BY timestamp DESC, id DESC;
    """

    with db_manager.get_cursor() as (_, cursor):
        cursor.execute(query, (plate,))
        return [dict(row) for row in cursor.fetchall()]
