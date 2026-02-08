"""
Orquestador de generacion de datos simulados.

Uso:
    python -m src.generate_all              # Solo genera CSVs
    python -m src.generate_all --load-db    # Genera CSVs + carga en MySQL
"""

import argparse
import time

from src.generators import generate_users, generate_routes, generate_activities


def main():
    parser = argparse.ArgumentParser(
        description="Genera datos simulados para Outdoor Route Recommender"
    )
    parser.add_argument(
        "--load-db",
        action="store_true",
        help="Cargar CSVs generados en MySQL (requiere Docker + MySQL corriendo)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed para reproducibilidad (default: usa config.SEED=42)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Outdoor Route Recommender — Generacion de datos")
    print("=" * 60)

    t_start = time.time()

    # 1. Usuarios
    t0 = time.time()
    seed_kwargs = {"seed": args.seed} if args.seed is not None else {}
    users = generate_users(**seed_kwargs)
    t_users = time.time() - t0

    # 2. Rutas
    t0 = time.time()
    routes = generate_routes(**seed_kwargs)
    t_routes = time.time() - t0

    # 3. Actividades
    t0 = time.time()
    activities = generate_activities(users, routes, **seed_kwargs)
    t_activities = time.time() - t0

    t_total = time.time() - t_start

    # Resumen final
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"  Usuarios:    {len(users):>6,d}  ({t_users:.2f}s)")
    print(f"  Rutas:       {len(routes):>6,d}  ({t_routes:.2f}s)")
    print(f"  Actividades: {len(activities):>6,d}  ({t_activities:.2f}s)")
    print(f"  Total:                ({t_total:.2f}s)")
    print(f"\n  Archivos en: data/raw/")

    # 4. Carga en DB (opcional)
    if args.load_db:
        print("\n" + "=" * 60)
        print("Cargando en MySQL...")
        print("=" * 60)
        from src.db_loader import load_all
        load_all()

    print("\nDone.")


if __name__ == "__main__":
    main()
