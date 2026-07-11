.PHONY: setup test lint lint-svg lint-post check png palette-report factcheck factcheck-apply thumbnail-prompt thumbnail-check

setup:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .

lint-svg:
	uv run lint-svg diagrams/

lint-post:
	uv run lint-post posts/

# 발행 전 기계 검사: SVG 규격 + 링크(lychee)·태그·카테고리. lint-post 가 POST-06(lychee)을 내부 실행한다.
check: lint-svg lint-post

# SVG는 소스, PNG는 산출물(gitignore). rsvg-convert 필요 (apt-get install librsvg2-bin)
png:
	find diagrams -name '*.svg' -exec sh -c 'rsvg-convert -w 2160 "$$0" -o "$${0%.svg}.png"' {} \;

palette-report:
	uv run lint-svg --palette-report diagrams/

# 팩트체크는 GPT 왕복 수동 게이트라 check 에 넣지 않는다 (무인 실행 불가).
# 1) 프롬프트 생성 → factcheck/<slug>.prompt.txt 를 GPT에 붙여넣는다.
factcheck:
	uv run factcheck $(POST)

# 2) GPT 응답(factcheck/<slug>.response.json)을 파싱해 심각도순 리포트. 자동 수정 없음.
factcheck-apply:
	uv run factcheck-apply $(POST)

# 썸네일도 GPT 왕복 수동 게이트다. 뼈대 프롬프트만 결정론적으로 박는다.
# 오브젝트 자리({{OBJECT}})와 근거 헤더는 Claude가 초안을 읽고 채운다 (thumbnails.md §2.4).
thumbnail-prompt:
	uv run thumbnail-prompt $(POST) --category $(CATEGORY)
# 오브젝트까지 하네스가 박게 하려면 콘솔 스크립트를 직접 호출한다:
#   uv run thumbnail-prompt drafts/foo.md --category Infra \
#     --object "..." --concept "..." --rationale "..."

# GPT 산출물 검사 + 150px 생성. Pillow 필요 (uv sync --extra thumbnail).
thumbnail-check:
	uv run thumbnail-check $(THUMB)
