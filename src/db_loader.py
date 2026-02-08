"""
Carga CSVs generados en MySQL.

Lee data/raw/{users,routes,activities}.csv e inserta en las tablas
correspondientes via mysql.connector. Batch de 100 filas.

Requisitos:
- MySQL corriendo (docker compose up -d)
- Tablas creadas (schema.sql ejecutado)
"""

import csv

from src.config import DATA_RAW_DIR, DB_CONFIG

BATCH_SIZE = 100


def load_all():
    """Carga los 3 CSVs en MySQL en orden (FKs)."""
    try:
        import mysql.connector
    except ImportError:
        print("ERROR: mysql-connector-python no instalado.")
        print("  pip install mysql-connector-python")
        return

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as e:
        print(f"ERROR: No se pudo conectar a MySQL: {e}")
        print("  Verifica que Docker este corriendo: docker compose up -d")
        return

    cursor = conn.cursor()
    print(f"Conectado a {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")

    try:
        _load_users(cursor)
        conn.commit()
        _load_routes(cursor)
        conn.commit()
        _load_activities(cursor)
        conn.commit()

        # Verificar conteos
        print("\nVerificacion de conteos:")
        for table in ["dim_users", "dim_routes", "fact_activities"]:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count:,d} filas")

    except Exception as e:
        conn.rollback()
        print(f"ERROR durante la carga: {e}")
        raise
    finally:
        cursor.close()
        conn.close()
        print("Conexion cerrada.")


def _load_users(cursor):
    """Inserta usuarios desde CSV."""
    csv_path = DATA_RAW_DIR / "users.csv"
    print(f"\nCargando usuarios desde {csv_path}...")

    sql = """
        INSERT INTO dim_users
            (user_id, username, registration_date, experience_level, preferred_activity_type_id)
        VALUES (%s, %s, %s, %s, %s)
    """

    rows = _read_csv(csv_path)
    batch = []
    for row in rows:
        pref = int(row["preferred_activity_type_id"]) if row["preferred_activity_type_id"] else None
        batch.append((
            int(row["user_id"]),
            row["username"],
            row["registration_date"],
            row["experience_level"],
            pref,
        ))
        if len(batch) >= BATCH_SIZE:
            cursor.executemany(sql, batch)
            batch = []

    if batch:
        cursor.executemany(sql, batch)

    print(f"  {len(rows)} usuarios insertados.")


def _load_routes(cursor):
    """Inserta rutas desde CSV."""
    csv_path = DATA_RAW_DIR / "routes.csv"
    print(f"\nCargando rutas desde {csv_path}...")

    sql = """
        INSERT INTO dim_routes
            (route_id, name, distance_km, elevation_gain_m, elevation_loss_m,
             estimated_duration_h, difficulty, is_circular, activity_type_id,
             terrain_type_id, zone_id, created_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    rows = _read_csv(csv_path)
    batch = []
    for row in rows:
        batch.append((
            int(row["route_id"]),
            row["name"],
            float(row["distance_km"]),
            int(row["elevation_gain_m"]),
            int(row["elevation_loss_m"]),
            float(row["estimated_duration_h"]),
            row["difficulty"],
            bool(int(row["is_circular"])),
            int(row["activity_type_id"]),
            int(row["terrain_type_id"]),
            int(row["zone_id"]),
            row["created_date"],
        ))
        if len(batch) >= BATCH_SIZE:
            cursor.executemany(sql, batch)
            batch = []

    if batch:
        cursor.executemany(sql, batch)

    print(f"  {len(rows)} rutas insertadas.")


def _load_activities(cursor):
    """Inserta actividades desde CSV."""
    csv_path = DATA_RAW_DIR / "activities.csv"
    print(f"\nCargando actividades desde {csv_path}...")

    sql = """
        INSERT INTO fact_activities
            (activity_id, user_id, route_id, activity_date,
             completed, actual_duration_h, rating)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    rows = _read_csv(csv_path)
    batch = []
    count = 0
    for row in rows:
        rating = int(row["rating"]) if row["rating"] else None
        batch.append((
            int(row["activity_id"]),
            int(row["user_id"]),
            int(row["route_id"]),
            row["activity_date"],
            bool(int(row["completed"])),
            float(row["actual_duration_h"]),
            rating,
        ))
        if len(batch) >= BATCH_SIZE:
            cursor.executemany(sql, batch)
            count += len(batch)
            batch = []

    if batch:
        cursor.executemany(sql, batch)
        count += len(batch)

    print(f"  {count} actividades insertadas.")


def _read_csv(path):
    """Lee un CSV y devuelve lista de dicts."""
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))
