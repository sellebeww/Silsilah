# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
.PHONY: eval test lint

eval:  ## sapuan ambang + evaluasi penempatan/diff pada dataset sintetis (hasil: docs/EVAL.md)
	uv run python scripts/eval_phylogeny.py

test:
	uv run pytest -q -p no:cacheprovider

lint:
	uv run ruff check . && uv run ruff format --check . && uv run mypy src tests scripts
