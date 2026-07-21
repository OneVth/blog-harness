<!-- DIAGRAM-LEDGER
guides/sensors 2×2 → diagram (harness_2x2) | axis crossing conveys more than a table
pipeline → prose + ASCII flow | ordering reads fine as a sketch, no diagram
lint / callout examples → code blocks | the real output is the visual
measurement-overruled list → table | it is a comparison, so §3.4 table fits
-->
# blog-harness

*[한국어로 읽기](README.ko.md)*

**This repository is not a blog. It is a machine that checks and converts blog
posts before they are published.**

I write technical posts in [Obsidian](https://obsidian.md) (a local Markdown
notebook) and publish them to [Tistory](https://www.tistory.com) (a Korean
blogging platform). The posts live there, not here. What lives here are the
*linters*, the *converters*, and the *fact-checker* that sit between the draft
and the published copy.

It is a personal tool for one person's blog. You probably won't want to *use*
it. The part worth reading is the experiment behind it: applying harness
engineering to a domain that has no compiler. The transferable part is the ideas
below, not the SVG-coordinate arithmetic.

## Why this exists

I already had five design documents describing how posts should be written,
diagrammed, tagged, and categorized. They were not followed. Not because they
were wrong, but because a document has no teeth. When you write "please do it
this way" in a guide, an LLM ignores it.

Birgitta Böckeler (in Martin Fowler's "Exploring Gen AI" series) models a harness
as *guides* that steer the agent before it acts and *sensors* that check it
after, each of them either *computational* (deterministic) or *inferential*
(AI-judged), with a human steering by improving the harness over time.

![The harness model: guides/sensors x computational/inferential, with this repo's tools in each quadrant](diagrams/meta/harness_2x2.png)

The sensor row now holds `lint-post` and `factcheck`, but at the start it was
empty. I had the guides as documents and nothing else; a single human was doing
all the sensing by hand, against five documents. That does not scale, and it
does not last.

So the governing rule is: **if a rule can be checked by a machine, move it out of
the document and into code.** And when the agent makes a mistake, don't patch the
prompt to scold it. Change the system so that class of mistake cannot recur.

## The pipeline

A draft flows top to bottom. The `make` steps are mechanical; the numbered gates
are the points where only a human can judge. Gate ① is writing the draft itself,
at the top.

```
drafts/<slug>.md
     ↓ make lint-svg      SVG diagram spec (coordinates, palette, sizes)
     ↓ human: review diagrams            ← gate ②  does it convey its meaning
     ↓ make check         dead links · tags · categories · prose rules
     ↓ make factcheck     cross-check unsourced claims against another model
     ↓ humanize-korean    strip the "AI smell": prose that reads as machine-written
★ final file frozen
     ├→ Obsidian archive (kept in callout syntax)
     └→ make build → posts/<slug>.md (callout syntax → HTML)
     ↓ make thumbnail-prompt
     ↓ human: paste prompt into an image model   ← gate ③
     ↓ make thumbnail-check + blind test
     ↓ human: publish to Tistory                 ← gate ④
```

The gates are deliberate. The machine checks what it can check mechanically; the
human judges what only a human can (does this diagram convey its meaning, does
this thumbnail read as the concept it's supposed to be). When the machine handles
the checks it does better, the human's attention is left for the ones it can't.

## What it looks like in practice

Two of the machine steps, concretely.

**Checking.** The linter reads a draft, and every rule it prints carries an ID
that leads back to the document defining it. Here is real output from a draft
with three planted mistakes:

```
  [WARN] POST-12: dramatic idiom "심장이다" (line 6): "이 개념이야말로 알고리즘의 심장이다."
         — keep it plain. writing.md §4.3
  [WARN] POST-13: [IMG:] filename 'dp_missing_diagram' not found under diagrams/ (line 12)
         — typo? if it's a description, avoid the lowercase_underscore filename shape.
  [WARN] POST-14: 2 underscores inside one math span (line 8)
         — Tistory Markdown eats `_..._` as emphasis and breaks KaTeX. Inline two-plus
           subscripts as plain text.

1 file checked — ERROR 0, WARN 2
```

All three of these rules came out of mistakes made while writing the first post
(see "The first real run"). None of them existed as code a week ago; each one is
now caught before publish.

**Converting.** Drafts are written once, in Obsidian's callout syntax. The build
step deterministically rewrites callouts into the HTML that Tistory's skin
styles. Tistory does not parse Markdown inside a `<blockquote>`, so a backtick
left alone would render as a literal backtick:

```markdown
> [!important] Time complexity
> Average `O(log n)`.
```

↓ `make build`

```html
<blockquote class="markdown-callout markdown-callout-important">
  <p class="callout-title">Time complexity</p>
  <p>Average <code>O(log n)</code>.</p>
</blockquote>
```

No LLM does this by hand; it is a pure function. The post is written once, in one
syntax, and the HTML is a build artifact.

## The rule contract

`guides/RULES.md` is the linter's contract. Two principles govern it:

- **Only what is written there becomes code. What is not there is not checked.**
- **No false positives.** If the linter flags something that is actually fine,
  the human learns to ignore the linter, and the moment that happens, the linter
  stops being used. When in doubt, downgrade: ERROR → WARN → INFO.

Every rule is defined with an ID, a level, a condition, and a source. A linter
error prints the rule ID; the ID leads you back to the document that defines it.
There is deliberately no rule count in this README. The count lives in exactly
one place, `RULES.md`, and a machine does the counting (see "One source of
truth").

### What is *not* checked

The contract ends with an explicit list of things the harness does **not** check,
because a machine can't:

- Whether a diagram actually conveys its meaning. A human reviews it (gate ②).
- Thumbnail object selection. Claude decides, because it requires reading the
  whole draft; a lookup table can't.
- Whether a thumbnail reads as the intended concept. A blind test decides: a
  fresh session is shown only the image, with no title or caption, and asked what
  concept it sees.
- Broad tone judgments (definition-first prose, first person, procedural voice).
  These need semantic judgment. A few *specific* dramatic idioms are the
  exception, since an exact phrase list can be matched; POST-12 catches those.
- The "AI smell" in Korean prose. The `humanize-korean` tool handles that.
- Practice-topic tags inside a lecture. Context-dependent; the machine can't tell
  a hands-on subject from a domain concept.

This list matters. A linter that pretends to be omniscient makes the human stop
reviewing.

## One source of truth

A spec must exist in exactly one place. The category list and the thumbnail color
mapping are **parsed from machine-readable blocks in the documents**, not
hard-coded as constants in the linter:

```
<!-- CATEGORIES:BEGIN -->
Embedded
...
<!-- CATEGORIES:END -->
```

The reason: a list that grows will drift from a hard-coded copy. It already
happened. The `OSS Tools` category existed in reality but was missing from the
constant. So the boundary is drawn here: a growing list is parsed from the
document, and a fixed physical constant (SVG geometry) is hard-coded with a
rule-ID comment.

## When measurement overruled the document

The most instructive part of building this was how often real measurement
contradicted the design documents. Every one of these would have been missed by
reading the docs alone:

| The document said | What measurement showed |
|---|---|
| viewBox max is 720 | 900 (confirmed in dev tools) |
| no backticks in callouts | the converter turns them into `<code>` (confirmed by render test) |
| — | LaTeX needs protecting (`$a*b*c$` was corrupted into `$a <em>b</em> c$`) |
| no dashes in body text | structural separators are allowed (only 11 of 77 were real violations) |
| no first person in definitional prose | only the *judging* subject is banned; an example participant is fine |
| plural tags = ERROR | WARN (Redis, HTTPS, macOS are false positives) |
| — | Tistory eats paired `_..._` inside `$$…$$` as emphasis; a single subscript renders, two break KaTeX (POST-14) |

## The first real run

Phases 0 through 6 are implemented, including the callout → HTML `make build`
step. For a long time this README ended here with the line "the pipeline has
never been run on a real post."

It has now. The first post was an introduction to dynamic programming, and it
went the full length: lint → diagram review → fact-check (cross-checked against a
second model) → humanize → build → thumbnail → blind test → published. Three
problems came up along the way, and each one became a new rule rather than a new
prompt.

- A dramatic, screenplay-ish sentence slipped through. **POST-12** now matches a
  parsed list of such idioms.
- An `[IMG:]` placeholder pointed at a diagram filename that didn't exist.
  **POST-13** now checks those filenames against `diagrams/`.
- A block equation with two subscripts rendered fine in Obsidian but broke on
  Tistory. **POST-14** now flags paired underscores inside math.

Each was a mistake that could recur, turned into a check that catches it at lint
time instead of after publish. That is what this repository is for.

## What was reused

I did not reinvent wheels that already exist:

| Tool | Role |
|---|---|
| [lychee](https://github.com/lycheeverse/lychee) | dead-link checking |
| [humanize-korean](https://github.com/epoko77-ai/im-not-ai) | stripping the "AI smell" from Korean text (the tool is `humanize-korean`; `im-not-ai` is its repo) |
| ce-compound | learning accumulation (forked from the Compound Engineering plugin) |

What I wrote from scratch is only the part that doesn't exist in the world:
domain rules. SVG coordinate arithmetic, the Obsidian → Tistory callout
conversion, and the four-axis tag convention.

## License

MIT — see [LICENSE](LICENSE).

The vendored `ce-compound` skill is a fork of the Compound Engineering plugin
(also MIT). Its attribution and modification record are in
[.claude/skills/ce-compound/THIRD-PARTY-NOTICES.md](.claude/skills/ce-compound/THIRD-PARTY-NOTICES.md).

## Reference — harness engineering

This project applies harness engineering to a **non-coding** domain. I looked at
Superpowers, Compound Engineering, Ouroboros, and grill-me-codex, but they were
all coding harnesses, and the foundation those rely on (compiler, linter, test
suite) doesn't exist for a blog. I had to build that foundation here myself.

- Birgitta Böckeler, "Harness Engineering" (on martinfowler.com) —
  <https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html>
- Chad Fowler, "Relocating Rigor" —
  <https://www.honeycomb.io/blog/production-is-where-the-rigor-goes>
