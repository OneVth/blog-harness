# blog-harness

*[한국어로 읽기](README.ko.md)*

This repository is not a blog. It is a machine for making blog posts.

The posts themselves do not live here — they live in Obsidian (the archive) and
on Tistory (the published copies). What lives here are the linters, the
converters, and the fact-checker.

## Why this exists

I already had five design documents describing how posts should be written,
diagrammed, tagged, and categorized. They were not followed. Not because they
were wrong — because a document has no teeth. When you write "please do it this
way" in a guide, it gets ignored.

Fowler and Böckeler's "harness engineering" frames a harness as a 2×2: guides,
machine verification, and LLM judgment, with a human in the loop. My setup had
only the top-left quadrant filled — guides. The two right-hand quadrants
(machine checks, LLM judgment) were empty, and a human was standing in for
both. That does not scale and it does not hold.

So the rule is: **if a rule can be verified by a machine, move it into code.**
When the agent makes a mistake, don't patch the prompt — change the system so
that class of mistake can't recur.

## The pipeline

```
drafts/<slug>.md
     ↓ make lint-svg      SVG spec
     ↓ human: review diagrams      ← gate ②
     ↓ make check         links · tags · categories
     ↓ make factcheck     GPT cross-check (claims with no source)
     ↓ im-not-ai          strip the "AI smell" (external tool)
★ final file frozen
     ├→ Obsidian archive (callout syntax as-is)
     └→ make build → posts/<cat>/<slug>.md (callout → HTML)
     ↓ make thumbnail-prompt
     ↓ human: paste into GPT       ← gate ③
     ↓ make thumbnail-check + blind test
     ↓ human: publish to Tistory   ← gate ④
```

The human gates are deliberate. The machine checks what it can check
mechanically; the human judges what only a human can judge (does the diagram
convey its meaning? does the thumbnail read as the intended concept?).

## The rule contract

`guides/RULES.md` is the linter's contract. Two principles govern it:

- **Only what is written here becomes code. What is not here is not checked.**
- **No false positives.** If the linter flags something that is fine, the human
  learns to ignore the linter — and the moment that happens, the harness is
  dead. When in doubt, downgrade: ERROR → WARN → INFO.

Every rule is defined with an ID, a level, a condition, and a source. A linter
error prints the rule ID; the ID leads you back to the document that defines it.
There is no rule count in this README on purpose — the count lives in exactly
one place, `RULES.md`, and a machine does the counting (see "One source of
truth" below).

### What is *not* checked

The contract ends with an explicit list of things the harness does **not**
check, because a machine can't:

- Whether a diagram actually conveys its meaning — a human reviews it (gate ②).
- Thumbnail object selection — Claude decides, because it requires reading the
  draft; a lookup table can't do it.
- Whether a thumbnail reads as the intended concept — a blind test decides.
- Tone judgments (definition-first prose, first person, procedural voice) —
  these need semantic judgment.
- The "AI smell" in Korean prose — `im-not-ai` handles that.
- Practice-topic tags inside a lecture — context-dependent; the machine can't
  tell a practice subject from a domain concept.

This list matters. A linter that pretends to be omniscient makes the human stop
reviewing.

## One source of truth

A spec must exist in exactly one place. The category list and the thumbnail
color mapping are **parsed from machine-readable blocks in the documents** —
they are not hard-coded as constants in the linter:

```
<!-- CATEGORIES:BEGIN -->
Embedded
...
<!-- CATEGORIES:END -->
```

The reason: a list that grows will drift from a hard-coded copy, guaranteed. It
already happened — the `OSS Tools` category existed in reality but was missing
from the document. Parse the document; don't embed the list.

## When measurement overruled the document

The most instructive part of building this was watching real measurement
contradict the design documents. Every one of these would have been missed by
reading the docs alone:

| The document said | Reality |
|---|---|
| viewBox max is 720 | 900 (confirmed in dev tools) |
| no backticks in callouts | the converter turns them into `<code>` — fine (render test) |
| — | LaTeX needs protecting (`$a*b*c$` was corrupted into `$a <em>b</em> c$`) |
| no dashes in body text | structural separators are allowed (only 11 of 77 were real violations) |
| no first person in definitional prose | only the *judging* subject is banned; an example participant is fine, even good |
| plural tags = ERROR | WARN (Redis, HTTPS, macOS are false positives) |

## What was reused

I did not reinvent wheels that already exist:

| Tool | Role |
|---|---|
| [lychee](https://github.com/lycheeverse/lychee) | dead-link checking |
| [im-not-ai](https://github.com/epoko77-ai/im-not-ai) | stripping the "AI smell" from Korean text |
| ce-compound | learning accumulation (forked from the Compound Engineering plugin) |

What I wrote from scratch is only the part that doesn't exist in the world:
domain rules — SVG coordinate arithmetic, the Obsidian → Tistory callout
conversion, and the four-axis tag convention.

## Status — honestly

Phases 0 through 6 are implemented. **The pipeline has never been run on a real
post yet.** When it breaks against a real article, that breakage becomes
ce-compound's second Learning. (One known gap already: the pipeline diagram
shows `make build`, but that target isn't wired in the Makefile yet — the
callout → HTML conversion exists as code but not as a make target.)

## License

MIT — see [LICENSE](LICENSE).

The vendored `ce-compound` skill is a fork of the Compound Engineering plugin
(also MIT). Its attribution and modification record are in
[.claude/skills/ce-compound/THIRD-PARTY-NOTICES.md](.claude/skills/ce-compound/THIRD-PARTY-NOTICES.md).

## Reference — harness engineering

This project applies harness engineering to a **non-coding** domain. I looked at
Superpowers, Compound Engineering, Ouroboros, and grill-me-codex, but they were
all coding harnesses, and the spine those rely on — compiler, linter, test
suite — doesn't exist for a blog. That spine had to be built by hand here.

- Martin Fowler / Birgitta Böckeler, "Harness Engineering" —
  <https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html>
- Chad Fowler, "Relocating Rigor" —
  <https://www.honeycomb.io/blog/production-is-where-the-rigor-goes>
