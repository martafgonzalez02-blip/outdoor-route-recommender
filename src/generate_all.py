"""
Orchestrator for simulated data generation.

Usage:
    python -m src.generate_all              # Generate CSVs only
    python -m src.generate_all --load-db    # Generate CSVs + load into MySQL
"""

import argparse
import sys
import time

from src.generators import generate_users, generate_routes, generate_activities


def main():
    parser = argparse.ArgumentParser(
        description="Generate simulated data for Outdoor Route Recommender"
    )
    parser.add_argument(
        "--load-db",
        action="store_true",
        help="Load generated CSVs into MySQL (requires Docker + MySQL running)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed for reproducibility (default: uses config.SEED=42)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run data quality checks after generating CSVs",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Outdoor Route Recommender — Data Generation")
    print("=" * 60)

    t_start = time.time()

    # 1. Users
    t0 = time.time()
    seed_kwargs = {"seed": args.seed} if args.seed is not None else {}
    users = generate_users(**seed_kwargs)
    t_users = time.time() - t0

    # 2. Routes
    t0 = time.time()
    routes = generate_routes(**seed_kwargs)
    t_routes = time.time() - t0

    # 3. Activities
    t0 = time.time()
    activities = generate_activities(users, routes, **seed_kwargs)
    t_activities = time.time() - t0

    t_total = time.time() - t_start

    # Final summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Users:       {len(users):>6,d}  ({t_users:.2f}s)")
    print(f"  Routes:      {len(routes):>6,d}  ({t_routes:.2f}s)")
    print(f"  Activities:  {len(activities):>6,d}  ({t_activities:.2f}s)")
    print(f"  Total:                ({t_total:.2f}s)")
    print(f"\n  Output in: data/raw/")

    # 4. DB load (optional)
    if args.load_db:
        print("\n" + "=" * 60)
        print("Loading into MySQL...")
        print("=" * 60)
        from src.db_loader import load_all
        load_all()

    # 5. Data quality checks (optional)
    if args.check:
        print()
        from src.data_quality import run_all_checks, format_report
        results, score, status = run_all_checks()
        lines = format_report(results, score, status)
        print("\n".join(lines))
        if status == "FAIL":
            sys.exit(1)

    print("\nDone.")


if __name__ == "__main__":
    main()
