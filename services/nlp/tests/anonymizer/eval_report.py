# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Cetak precision/recall pada set uji sintetis. Jalankan: uv run python -m tests.anonymizer.eval_report"""

from silsilah.anonymizer import anonymize
from silsilah.anonymizer.ner import default_recognizer

from .cases import CASES, HOLDOUT, evaluate, leaked


def main() -> None:
    ner = default_recognizer()
    configs = {
        "regex+heuristik+NER": lambda t: anonymize(t, ner=ner),
        "regex+heuristik": lambda t: anonymize(t, ner=lambda _: []),
    }
    for set_name, cases in {"tuning": CASES, "holdout": HOLDOUT}.items():
        for name, run in configs.items():
            print(f"{set_name:8} {name:22} {evaluate(run, cases)}")
    for case in HOLDOUT:
        out = anonymize(case.text, ner=ner).text
        missing = [k for k in case.keep if k not in out]
        if leaked(case, out) or missing:
            print(f"holdout gagal: {case.id}: bocor={leaked(case, out)} hilang={missing} -> {out!r}")


if __name__ == "__main__":
    main()
