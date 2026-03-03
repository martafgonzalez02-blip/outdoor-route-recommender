"""
Offline evaluation of the content-based recommender.

Methodology — behavioral consistency:
  For each user, score ALL routes (including already-completed ones).
  Completed activities are treated as positive implicit feedback.
  We then measure how many completed routes appear in top-K, which
  answers: would the recommender have surfaced routes the user actually did?

  Note: since the data simulator uses similar affinity signals to the
  recommender, scores are expected to be meaningful. This is a sanity
  check, not a claim of generalization to unseen data.

Metrics:
  hit@K          fraction of users with >=1 completed route in top-K
  recall@K       fraction of each user's completed routes recovered in top-K
  ndcg@K         normalized discounted cumulative gain (binary relevance)
  coverage@10    fraction of catalog recommended to >=1 user
  diversity@10   mean pairwise route diversity within recommendation lists
  personalization@10  1 - mean pairwise Jaccard overlap across users

Usage:
    python -m src.evaluation
    python -m src.evaluation --output docs/EVALUATION_REPORT.txt
"""

import argparse
import itertools
import math
import random

from src.recommender import _load_data, _score_route

K_VALUES = [5, 10, 20]
N_EVAL = max(K_VALUES)     # routes ranked per user (covers all K values)
N_SAMPLE_USERS = 100       # users sampled for personalization (O(n²) metric)


# =============================================================================
# Public API
# =============================================================================

def evaluate():
    """Run full offline evaluation.

    Returns:
        metrics:  dict metric_name -> float
        n_users:  int, number of users with at least 1 completed activity
    """
    user_profiles, route_feats, route_names, route_raw, completed_per_user = _load_data()

    # Score all routes for all users (include completed so we can check their rank)
    all_recs = _batch_recommend(user_profiles, route_feats, n=N_EVAL)

    # Only evaluate users who have at least 1 completed activity
    active_users = [uid for uid in all_recs if completed_per_user.get(uid)]

    metrics = {}

    # 1. Behavioral consistency: hit@K, recall@K, ndcg@K
    for k in K_VALUES:
        hits, recalls, ndcgs = [], [], []
        for uid in active_users:
            top_k = all_recs[uid][:k]
            completed = completed_per_user[uid]

            n_hits = sum(1 for rid in top_k if rid in completed)

            hits.append(1 if n_hits > 0 else 0)
            recalls.append(n_hits / len(completed))

            # NDCG@K with binary relevance (1 = completed, 0 = not)
            dcg = sum(
                1.0 / math.log2(i + 2)
                for i, rid in enumerate(top_k)
                if rid in completed
            )
            ideal_n = min(len(completed), k)
            idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_n))
            ndcgs.append(dcg / idcg if idcg > 0 else 0.0)

        n = len(hits)
        metrics[f"hit@{k}"]    = round(sum(hits)    / n, 4) if n else 0.0
        metrics[f"recall@{k}"] = round(sum(recalls) / n, 4) if n else 0.0
        metrics[f"ndcg@{k}"]   = round(sum(ndcgs)   / n, 4) if n else 0.0

    # 2. Catalog coverage@10
    recommended = set()
    for top_n in all_recs.values():
        recommended.update(top_n[:10])
    metrics["coverage@10"] = round(len(recommended) / len(route_feats), 4)

    # 3. Intra-list diversity@10
    #    Mean pairwise distance within each user's top-10.
    #    Distance = fraction of {difficulty, zone, activity type} that differ.
    div_scores = []
    for top_n in all_recs.values():
        top10 = top_n[:10]
        if len(top10) < 2:
            continue
        pairs = list(itertools.combinations(top10, 2))
        div = sum(_route_distance(a, b, route_feats) for a, b in pairs) / len(pairs)
        div_scores.append(div)
    metrics["diversity@10"] = round(sum(div_scores) / len(div_scores), 4) if div_scores else 0.0

    # 4. Personalization@10
    #    1 - mean pairwise Jaccard overlap between users' top-10 sets.
    #    Sampled to avoid O(n²) cost over all 500 users.
    random.seed(42)
    sample = random.sample(list(all_recs.keys()), min(N_SAMPLE_USERS, len(all_recs)))
    overlap_scores = []
    for u1, u2 in itertools.combinations(sample, 2):
        set1 = set(all_recs[u1][:10])
        set2 = set(all_recs[u2][:10])
        union = set1 | set2
        overlap_scores.append(len(set1 & set2) / len(union) if union else 0.0)

    n_pairs = len(overlap_scores)
    metrics["personalization@10"] = (
        round(1.0 - sum(overlap_scores) / n_pairs, 4) if n_pairs else 0.0
    )

    return metrics, len(active_users)


# =============================================================================
# Helpers
# =============================================================================

def _batch_recommend(user_profiles, route_feats, n):
    """Score all routes for all users in one pass (data loaded once).

    Returns:
        dict user_id -> list[route_id] sorted by score descending, top-n only.
    """
    all_recs = {}
    for uid, profile in user_profiles.items():
        scored = [
            (rid, _score_route(profile, route)[0])
            for rid, route in route_feats.items()
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        all_recs[uid] = [rid for rid, _ in scored[:n]]
    return all_recs


def _route_distance(rid_a, rid_b, route_feats):
    """Diversity between two routes: fraction of key attributes that differ."""
    a = route_feats.get(rid_a, {})
    b = route_feats.get(rid_b, {})
    diffs = [
        a.get("difficulty")       != b.get("difficulty"),
        a.get("zone_id")          != b.get("zone_id"),
        a.get("activity_type_id") != b.get("activity_type_id"),
    ]
    return sum(diffs) / len(diffs)


def format_report(metrics, n_users):
    """Format evaluation results as a list of text lines."""
    lines = []
    lines.append("=" * 60)
    lines.append("OFFLINE EVALUATION REPORT")
    lines.append("=" * 60)
    lines.append(f"Users evaluated:  {n_users}")
    lines.append(f"Methodology:      behavioral consistency")
    lines.append(f"                  (completed activities = relevant items)")
    lines.append("")

    lines.append("--- Behavioral consistency ---")
    for k in K_VALUES:
        lines.append(
            f"  @K={k:<3d}  "
            f"hit={metrics[f'hit@{k}']:.4f}  "
            f"recall={metrics[f'recall@{k}']:.4f}  "
            f"ndcg={metrics[f'ndcg@{k}']:.4f}"
        )
    lines.append("")

    lines.append("--- System-level ---")
    lines.append(
        f"  coverage@10:        {metrics['coverage@10']:.4f}"
        f"  (fraction of catalog recommended to >=1 user)"
    )
    lines.append(
        f"  diversity@10:       {metrics['diversity@10']:.4f}"
        f"  (mean pairwise diversity within top-10)"
    )
    lines.append(
        f"  personalization@10: {metrics['personalization@10']:.4f}"
        f"  (1 - mean Jaccard overlap across users)"
    )
    lines.append("")
    lines.append("=" * 60)

    return lines


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Offline evaluation of the recommender")
    parser.add_argument(
        "--output", type=str, default=None,
        help="Write report to file",
    )
    args = parser.parse_args()

    print("Running evaluation (scoring 200 routes x 500 users)...")
    metrics, n_users = evaluate()
    lines = format_report(metrics, n_users)
    report = "\n".join(lines)

    print(report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        print(f"Report written to: {args.output}")


if __name__ == "__main__":
    main()
