.PHONY: setup test lint lint-svg lint-post check build png gif palette-report factcheck factcheck-gpt factcheck-apply thumbnail-prompt thumbnail-check

setup:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .

lint-svg:
	uv run lint-svg diagrams/

# 소스(초안)를 린트한다 — 카테고리·태그는 초안 frontmatter 에서 읽는다 (POST-01~05).
# 발행본(posts/)이 아니라 초안을 보는 이유: 메타데이터가 거기 살고, build 가 발행본에서
# frontmatter 를 떼어내기 때문이다 (writing.md §5). 본문 규칙(POST-06~12)은 두 벌이 같다.
lint-post:
	uv run lint-post drafts/

# 발행 전 기계 검사: SVG 규격 + 링크(lychee)·태그·카테고리·본문 톤. lint-post 가 POST-06(lychee)을 내부 실행한다.
check: lint-svg lint-post

# 단일 소스(Obsidian 문법 초안)에서 발행본을 빌드한다. 글을 두 벌 쓰지 않는다.
# callout 만 HTML 로 바뀌고 나머지 마크다운은 그대로 남는다 (guides/callouts.md §1).
# posts/ 는 평평하게 간다 — 카테고리는 lint-post 가 CLI 인자로 받는다.
build:
ifndef POST
	$(error POST=<drafts/foo.md> 를 지정할 것)
endif
	@mkdir -p posts
	uv run convert-callouts "$(POST)" -o "posts/$(notdir $(POST))"

# SVG는 소스, PNG는 산출물(gitignore). rsvg-convert 필요 (apt-get install librsvg2-bin)
png:
	find diagrams -name '*.svg' -exec sh -c 'rsvg-convert -w 2160 "$$0" -o "$${0%.svg}.png"' {} \;

# 애니메이션 GIF 렌더 (diagram-system.md §8). 정적은 make png. Chrome + ffmpeg 필요.
# 소스 <name>.gif.html 은 ?t=초 로 프레임을 그린다. 산출물 <name>.gif 는 추적한다.
# 사용: make gif SRC=diagrams/dsa/dp_longest_path.gif.html FRAMES=151 [FPS=12 WIN=660,560 W=700]
gif:
ifndef SRC
	$(error SRC=<diagrams/.../name.gif.html> 를 지정할 것)
endif
ifndef FRAMES
	$(error FRAMES=<프레임 수> 를 지정할 것)
endif
	@command -v google-chrome >/dev/null 2>&1 || { echo "[gif] google-chrome 이 없습니다 (headless 렌더러)."; exit 1; }
	@command -v ffmpeg >/dev/null 2>&1 || { echo "[gif] ffmpeg 이 없습니다 (GIF 조립)."; exit 1; }
	@fps=$${FPS:-12}; win=$${WIN:-660,560}; w=$${W:-700}; \
	out=$$(echo "$(SRC)" | sed 's/\.gif\.html$$/.gif/'); \
	tmp=$$(mktemp -d); \
	echo "[gif] $(FRAMES) 프레임 렌더 ($$fps fps, $$win)…"; \
	for f in $$(seq 0 $$(( $(FRAMES) - 1 ))); do \
	  t=$$(awk "BEGIN{printf \"%.4f\", $$f/$$fps}"); \
	  google-chrome --headless=new --disable-gpu --no-sandbox --force-device-scale-factor=2 \
	    --default-background-color=FFFFFFFF --hide-scrollbars --virtual-time-budget=500 \
	    --screenshot="$$tmp/$$(printf '%04d' $$f).png" --window-size=$$win \
	    "file://$(CURDIR)/$(SRC)?t=$$t" >/dev/null 2>&1; \
	done; \
	ffmpeg -y -framerate $$fps -i "$$tmp/%04d.png" -vf "scale=$$w:-1:flags=lanczos,palettegen=stats_mode=diff" "$$tmp/pal.png" >/dev/null 2>&1; \
	ffmpeg -y -framerate $$fps -i "$$tmp/%04d.png" -i "$$tmp/pal.png" \
	  -lavfi "scale=$$w:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=sierra2_4a" -loop 0 "$$out" >/dev/null 2>&1; \
	rm -rf "$$tmp"; \
	echo "[gif] 완료: $$out ($$(du -h "$$out" | cut -f1))"

palette-report:
	uv run lint-svg --palette-report diagrams/

# 팩트체크는 GPT 왕복 게이트다 — GPT(다른 프로바이더)가 판정해 에코 챔버를 깬다 (FACT-02).
# 1) 프롬프트 생성 → factcheck/<slug>.prompt.txt 를 GPT에 붙여넣는다. (수동 경로)
factcheck:
	uv run factcheck $(POST)

# 1-auto) codex(OpenAI GPT)로 판정을 자동화한다. 붙여넣기 없이 크로스 프로바이더를 지킨다.
# codex 는 Claude 와 다른 프로바이더라 FACT-02 를 만족한다. read-only 샌드박스 — 판정만 한다.
# codex 없으면 안내하고 멈춘다 (수동 경로로 폴백). 판정 후 make factcheck-apply 로 리포트를 본다.
factcheck-gpt:
ifndef POST
	$(error POST=<drafts/foo.md> 를 지정할 것)
endif
	@command -v codex >/dev/null 2>&1 || { echo "[factcheck-gpt] codex 가 없습니다. 설치하거나 factcheck/<slug>.prompt.txt 를 GPT 에 직접 붙여넣으세요 (make factcheck)."; exit 1; }
	uv run factcheck $(POST)
	@slug=$(notdir $(basename $(POST))); \
	echo "[factcheck-gpt] codex(GPT, read-only)로 판정 중…"; \
	codex exec --sandbox read-only -C "$(CURDIR)" \
	  --output-last-message "factcheck/$$slug.response.json" \
	  < "factcheck/$$slug.prompt.txt" >/dev/null; \
	python3 -c "import json; json.load(open('factcheck/$$slug.response.json'))" \
	  && echo "[factcheck-gpt] 판정 저장됨 → make factcheck-apply POST=$(POST)" \
	  || { echo "[factcheck-gpt] codex 출력이 JSON 이 아닙니다. 확인: factcheck/$$slug.response.json"; exit 1; }

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
