"""
Utilidades de normalizacion para feature engineering.

Min-max scaling a [0, 1]. Stats guardados para reproducibilidad.
"""

import csv


def compute_stats(values):
    """Calcula min y max de una lista de valores numericos.

    Args:
        values: lista de floats (ignora None).

    Returns:
        dict con keys 'min', 'max', 'count'.
    """
    clean = [v for v in values if v is not None]
    if not clean:
        return {"min": 0.0, "max": 0.0, "count": 0}
    return {
        "min": min(clean),
        "max": max(clean),
        "count": len(clean),
    }


def min_max_normalize(value, min_val, max_val):
    """Normaliza un valor al rango [0, 1] con min-max scaling.

    Si min == max, devuelve 0.0 (sin varianza).
    Si value es None, devuelve None.
    Clamps al rango [0, 1].
    """
    if value is None:
        return None
    if max_val == min_val:
        return 0.0
    normalized = (value - min_val) / (max_val - min_val)
    return max(0.0, min(1.0, normalized))


def normalize_rows(rows, columns, stats_dict):
    """Normaliza columnas in-place en una lista de dicts.

    Args:
        rows: lista de dicts con los datos.
        columns: lista de nombres de columnas a normalizar.
        stats_dict: dict de {col_name: {"min": x, "max": y}}.

    Returns:
        rows (modificados in-place).
    """
    for row in rows:
        for col in columns:
            if col in row and col in stats_dict:
                s = stats_dict[col]
                row[col] = min_max_normalize(row[col], s["min"], s["max"])
    return rows


def save_stats(stats_dict, output_path):
    """Guarda stats de normalizacion a CSV.

    Args:
        stats_dict: dict de {col_name: {"min": x, "max": y, "count": n}}.
        output_path: pathlib.Path del archivo de salida.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["feature", "min", "max", "count"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for feat, s in sorted(stats_dict.items()):
            writer.writerow({
                "feature": feat,
                "min": round(s["min"], 6),
                "max": round(s["max"], 6),
                "count": s["count"],
            })
