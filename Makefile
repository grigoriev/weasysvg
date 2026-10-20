# Tests and the visual bench run in Docker: WeasyPrint needs Pango, which macOS lacks.
IMAGE ?= weasysvg-test
BASE ?= python:3.14-slim-trixie@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170
RUN = docker run --rm --volume "$(CURDIR):/src"

.PHONY: lint test test-image upstream hooks visual visual-image visual-baseline visual-check comparison

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src tests tools
	uv run mypy upstream

test-image:
	docker build --file Dockerfile.test --target test --build-arg BASE="$(BASE)" --tag $(IMAGE):test .

test: test-image
	$(RUN) $(IMAGE):test

# WeasyPrint alone: the gaps weasysvg covers and the internals it hooks (UPGRADING.md)
upstream: test-image
	$(RUN) $(IMAGE):test uv run --frozen --all-extras pytest upstream -v

# Write upstream/hooks.json for the WeasyPrint the image installs
hooks: test-image
	$(RUN) $(IMAGE):test uv run --frozen --all-extras python tools/upstream/hooks.py

visual-image:
	docker build --file Dockerfile.test --target visual --build-arg BASE="$(BASE)" --tag $(IMAGE):visual .

# make visual ARGS="--only drawio" renders one group or name
visual: visual-image
	$(RUN) $(IMAGE):visual uv run --frozen --all-extras python tools/visual/bench.py $(ARGS)

BENCH = $(RUN) $(IMAGE):visual uv run --frozen --all-extras python tools/visual/bench.py

# Store the mismatch of weasysvg and of WeasyPrint alone in corpus/baseline.json
visual-baseline: visual-image
	$(BENCH) --out tools/visual/out/weasysvg --write-baseline corpus/baseline.json
	$(BENCH) --native --out tools/visual/out/native --write-baseline corpus/baseline.json

# Compare both with corpus/baseline.json: fails when weasysvg got worse (UPGRADING.md)
visual-check: visual-image
	$(BENCH) --native --out tools/visual/out/native --against corpus/baseline.json
	$(BENCH) --out tools/visual/out/weasysvg --against corpus/baseline.json

# Render the panels of both modes into corpus/render and write corpus/COMPARISON.md
comparison: visual-image
	$(BENCH) --native --out tools/visual/out/native --panels corpus/render/weasyprint
	$(BENCH) --out tools/visual/out/weasysvg --panels corpus/render/weasysvg
	$(RUN) $(IMAGE):visual uv run --frozen --all-extras python tools/visual/comparison.py
