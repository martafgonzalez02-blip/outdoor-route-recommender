"""
Simulated user generator for dim_users.

Distribution controlled by config.py:
- registration_date: beta(3,2) biased towards recent dates
- experience_level: beginner 35%, intermediate 40%, advanced 18%, expert 7%
- preferred_activity_type_id: hiking 51%, trail_running 21%, cycling 13%, NULL 15%
"""

import csv
import random
import string
from datetime import timedelta

from src.config import (
    DATA_RAW_DIR,
    DATE_END,
    DATE_START,
    NUM_USERS,
    SEED,
    USER_EXPERIENCE_DIST,
    USER_PREFERRED_ACTIVITY_DIST,
    USER_REG_BETA_A,
    USER_REG_BETA_B,
)

try:
    from faker import Faker
    fake = Faker("es_ES")
    _HAS_FAKER = True
except ImportError:
    fake = None
    _HAS_FAKER = False

# Username vocabulary without Faker
_PREFIXES = [
    "trail", "route", "mount", "path", "summit", "forest", "river", "lake",
    "peak", "valley", "stone", "wind", "snow", "sun", "moon", "wolf",
    "eagle", "falcon", "deer", "bear", "lynx", "goat", "chamois",
]
_SUFFIXES = [
    "runner", "hiker", "rider", "walker", "explorer", "nomad", "wanderer",
    "climber", "trekker", "biker", "adventure", "free", "wild", "north",
    "south", "alpine", "coastal", "volcanic",
]


def generate_users(seed=SEED):
    """Generate NUM_USERS users with realistic distributions.

    Returns:
        list[dict]: List of dicts with dim_users fields.
    """
    random.seed(seed)
    if _HAS_FAKER:
        Faker.seed(seed)

    exp_levels = list(USER_EXPERIENCE_DIST.keys())
    exp_weights = list(USER_EXPERIENCE_DIST.values())

    pref_activities = list(USER_PREFERRED_ACTIVITY_DIST.keys())
    pref_weights = list(USER_PREFERRED_ACTIVITY_DIST.values())

    total_days = (DATE_END - DATE_START).days

    users = []
    seen_usernames = set()

    for user_id in range(1, NUM_USERS + 1):
        # Unique username
        username = _make_username(user_id, seen_usernames)
        seen_usernames.add(username)

        # Registration date: beta(3,2) biased towards recent dates
        beta_val = random.betavariate(USER_REG_BETA_A, USER_REG_BETA_B)
        reg_date = DATE_START + timedelta(days=int(beta_val * total_days))

        # Experience level
        experience = random.choices(exp_levels, weights=exp_weights, k=1)[0]

        # Preferred activity type (can be NULL)
        pref_activity = random.choices(pref_activities, weights=pref_weights, k=1)[0]

        users.append({
            "user_id": user_id,
            "username": username,
            "registration_date": reg_date.isoformat(),
            "experience_level": experience,
            "preferred_activity_type_id": pref_activity if pref_activity is not None else "",
        })

    # Write CSV
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = DATA_RAW_DIR / "users.csv"
    fieldnames = ["user_id", "username", "registration_date", "experience_level",
                  "preferred_activity_type_id"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(users)

    _print_stats(users)
    return users


def _make_username(user_id, seen):
    """Generate a unique username. Uses Faker if available, otherwise own vocabulary."""
    if _HAS_FAKER:
        base = fake.user_name()
        username = f"{base}{user_id}"
        while username in seen:
            username = f"{fake.user_name()}{random.randint(1000, 9999)}"
        return username

    # Fallback without Faker: prefix + suffix + id
    for _ in range(50):
        username = f"{random.choice(_PREFIXES)}_{random.choice(_SUFFIXES)}{user_id}"
        if username not in seen:
            return username
    return f"user_{user_id}_{random.randint(1000, 9999)}"


def _print_stats(users):
    """Print distribution of generated users."""
    n = len(users)
    print(f"\n--- Users: {n} generated ---")

    # Experience distribution
    exp_counts = {}
    for u in users:
        lvl = u["experience_level"]
        exp_counts[lvl] = exp_counts.get(lvl, 0) + 1
    print("  Experience level:")
    for lvl in ["beginner", "intermediate", "advanced", "expert"]:
        count = exp_counts.get(lvl, 0)
        print(f"    {lvl:15s}: {count:4d} ({count/n*100:5.1f}%)")

    # Preferred activity distribution
    act_counts = {}
    for u in users:
        val = u["preferred_activity_type_id"]
        act_counts[val] = act_counts.get(val, 0) + 1
    print("  Preferred activity:")
    for val, count in sorted(act_counts.items(), key=lambda x: str(x[0])):
        label = val if val != "" else "NULL"
        print(f"    {str(label):15s}: {count:4d} ({count/n*100:5.1f}%)")

    print(f"  CSV: data/raw/users.csv")
