.PHONY: setup test lint lint-svg png palette-report

setup:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .

lint-svg:
	uv run lint-svg diagrams/

# SVG는 소스, PNG는 산출물(gitignore). rsvg-convert 필요 (apt-get install librsvg2-bin)
png:
	find diagrams -name '*.svg' -exec sh -c 'rsvg-convert -w 2160 "$$0" -o "$${0%.svg}.png"' {} \;

palette-report:
	uv run lint-svg --palette-report diagrams/
