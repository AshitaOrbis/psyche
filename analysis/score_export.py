#!/usr/bin/env python3
"""Score raw session data from a web app export that wasn't finalized.

Usage: python score_export.py profiles/self-report.json
"""
import json
import sys
from pathlib import Path


def score_likert(items: list[dict], responses: list[dict], scale_min: int, scale_max: int) -> dict[str, dict]:
    """Score Likert items with reverse scoring support."""
    resp_map = {r["itemId"]: r["value"] for r in responses if isinstance(r.get("value"), (int, float))}

    scale_values: dict[str, list[float]] = {}
    for item in items:
        item_id = item["id"]
        if item_id not in resp_map:
            continue
        value = resp_map[item_id]
        if item.get("reversed"):
            value = scale_max + scale_min - value
        scale_values.setdefault(item["scaleId"], []).append(value)

    scores = {}
    for scale_id, values in scale_values.items():
        raw = sum(values) / len(values)
        normalized = ((raw - scale_min) / (scale_max - scale_min)) * 100
        scores[scale_id] = {
            "scaleId": scale_id,
            "raw": round(raw, 3),
            "normalized": round(normalized, 1),
            "itemCount": len(values),
        }
    return scores


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("profiles/self-report.json")
    data = json.loads(path.read_text())
    sessions = data["sessions"]
    results = {}

    # === IPIP-NEO-120 ===
    if "ipip-neo-120" in sessions:
        # Load items from npm package
        items_path = Path(__file__).parent.parent / "web/node_modules/b5-johnson-120-ipip-neo-pi-r/data/en/questions.json"
        raw_items = json.loads(items_path.read_text())
        items = [{
            "id": q["id"],
            "scaleId": f"{q['domain']}{q['facet']}",
            "reversed": q["keyed"] == "minus",
        } for q in raw_items]

        facet_scores = score_likert(items, sessions["ipip-neo-120"]["responses"], 1, 5)

        # Compute domain scores as mean of facets
        domains = {"N": "Neuroticism", "E": "Extraversion", "O": "Openness", "A": "Agreeableness", "C": "Conscientiousness"}
        domain_scores = {}
        for dk, name in domains.items():
            facets = [v for k, v in facet_scores.items() if k.startswith(dk)]
            if facets:
                avg_norm = sum(f["normalized"] for f in facets) / len(facets)
                avg_raw = sum(f["raw"] for f in facets) / len(facets)
                domain_scores[dk] = {
                    "scaleId": dk,
                    "scaleName": name,
                    "raw": round(avg_raw, 3),
                    "normalized": round(avg_norm, 1),
                    "itemCount": sum(f["itemCount"] for f in facets),
                }

        all_scores = list(domain_scores.values()) + [
            {**v, "scaleName": v["scaleId"]} for v in facet_scores.values()
        ]
        results["ipip-neo-120"] = {"instrumentId": "ipip-neo-120", "scores": all_scores}

    # === CRT-7 ===
    if "crt-7" in sessions:
        correct_answers = {
            "crt-1": lambda v: float(v) == 5,
            "crt-2": lambda v: float(v) == 5,
            "crt-3": lambda v: float(v) == 47,
            "crt-4": lambda v: float(v) == 4,
            "crt-5": lambda v: float(v) == 29,
            "crt-6": lambda v: float(v) == 20,
            "crt-7": lambda v: str(v).lower().strip() == "c",
        }
        correct = 0
        for r in sessions["crt-7"]["responses"]:
            checker = correct_answers.get(r["itemId"])
            if checker:
                try:
                    if checker(r["value"]):
                        correct += 1
                except (ValueError, TypeError):
                    pass
        results["crt-7"] = {
            "instrumentId": "crt-7",
            "scores": [{"scaleId": "crt-analytic", "scaleName": "Analytic Thinking", "raw": correct, "normalized": round(correct / 7 * 100, 1), "itemCount": 7}],
        }

    # === NCS-18 ===
    if "ncs-18" in sessions:
        reversed_indices = {2, 3, 4, 6, 7, 8, 11, 15, 16}  # 0-indexed
        items = [{"id": f"ncs-{i+1}", "scaleId": "ncs", "reversed": i in reversed_indices} for i in range(18)]
        scores = score_likert(items, sessions["ncs-18"]["responses"], 1, 5)
        ncs = scores.get("ncs", {"raw": 3, "normalized": 50, "itemCount": 0})
        results["ncs-18"] = {
            "instrumentId": "ncs-18",
            "scores": [{"scaleId": "ncs", "scaleName": "Need for Cognition", **ncs}],
        }

    # === Rosenberg ===
    if "rosenberg" in sessions:
        reversed_indices = {1, 4, 5, 7, 8}  # 0-indexed
        items = [{"id": f"rses-{i+1}", "scaleId": "self-esteem", "reversed": i in reversed_indices} for i in range(10)]
        scores = score_likert(items, sessions["rosenberg"]["responses"], 1, 4)
        se = scores.get("self-esteem", {"raw": 2.5, "normalized": 50, "itemCount": 0})
        results["rosenberg"] = {
            "instrumentId": "rosenberg",
            "scores": [{"scaleId": "self-esteem", "scaleName": "Self-Esteem", **se}],
        }

    # === SD3 ===
    if "sd3" in sessions:
        sd3_scales = (["mach"] * 9) + (["narc"] * 9) + (["psych"] * 9)
        sd3_reversed = {10, 14, 16, 19, 24}  # 1-indexed items that are reversed
        items = [{"id": f"sd3-{i+1}", "scaleId": sd3_scales[i], "reversed": (i+1) in sd3_reversed} for i in range(27)]
        scores = score_likert(items, sessions["sd3"]["responses"], 1, 5)
        score_list = []
        for scale_id, name in [("mach", "Machiavellianism"), ("narc", "Narcissism"), ("psych", "Psychopathy")]:
            s = scores.get(scale_id, {"raw": 3, "normalized": 50, "itemCount": 0})
            score_list.append({"scaleId": scale_id, "scaleName": name, **s})
        results["sd3"] = {"instrumentId": "sd3", "scores": score_list}

    # === PHQ-9 + GAD-7 ===
    if "phq9-gad7" in sessions:
        resp_map = {r["itemId"]: r["value"] for r in sessions["phq9-gad7"]["responses"]}
        phq9_sum = sum(resp_map.get(f"phq9-{i+1}", 0) for i in range(9))
        gad7_sum = sum(resp_map.get(f"gad7-{i+1}", 0) for i in range(7))
        results["phq9-gad7"] = {
            "instrumentId": "phq9-gad7",
            "scores": [
                {"scaleId": "phq9", "scaleName": "Depression (PHQ-9)", "raw": phq9_sum, "normalized": round(phq9_sum / 27 * 100, 1), "itemCount": 9},
                {"scaleId": "gad7", "scaleName": "Anxiety (GAD-7)", "raw": gad7_sum, "normalized": round(gad7_sum / 21 * 100, 1), "itemCount": 7},
            ],
        }

    # === Open-Ended ===
    if "open-ended" in sessions:
        responses = sessions["open-ended"]["responses"]
        answered = sum(1 for r in responses if isinstance(r.get("value"), str) and r["value"].strip())
        total_words = sum(len(str(r.get("value", "")).split()) for r in responses if isinstance(r.get("value"), str))
        results["open-ended"] = {
            "instrumentId": "open-ended",
            "scores": [
                {"scaleId": "qualitative", "scaleName": "Qualitative Responses", "raw": answered, "normalized": round(answered / 10 * 100, 1), "itemCount": answered},
                {"scaleId": "word-count", "scaleName": "Total Word Count", "raw": total_words, "normalized": min(round(total_words / 1000 * 100, 1), 100), "itemCount": answered},
            ],
        }

    # Write scored export
    data["results"] = results
    out_path = path.parent / "self-report-scored.json"
    out_path.write_text(json.dumps(data, indent=2))
    print(f"Scored export saved to {out_path}")

    # Print summary
    print("\n=== RESULTS ===")
    for inst_id, result in results.items():
        print(f"\n{inst_id}:")
        for s in result["scores"]:
            name = s.get("scaleName", s["scaleId"])
            print(f"  {name}: {s['raw']:.1f} raw, {s['normalized']:.1f}/100")


if __name__ == "__main__":
    main()
