# Third-Party Notices

## ce-compound

This skill is adapted from the **ce-compound** skill in
[compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin)
by **Every**, used under the MIT License.

**Source**: `EveryInc/compound-engineering-plugin@7f86be9d` (upstream main HEAD)

**Modifications**:
- Removed all `ce-compound-refresh` references (that skill was not vendored).
  Phase 2.5 (Selective Refresh Check) — whose sole purpose was invoking it —
  was replaced with a "Stale-Doc Note (manual review)": the dead automation
  was stripped, the signal it carried was preserved.
- Removed references to CE commands not vendored: `/ce-plan`, `ce-code-review`,
  `ce-simplify-code`, `/research`, `ce-sessions`, `code-simplicity-reviewer`.
- Added an explicit `mode:lightweight` token (upstream selects Full vs
  Lightweight by context pressure, with no deterministic override).
- Fixed three pre-existing static-analysis errors in the vendored scripts
  (no behavior change): added a missing `NoReturn` import in
  `validate-doc-claims.py` and `validate-frontmatter.py`, and removed an
  unused exception binding in `session-history/extract-metadata.py`.

The full modification record lives in commit `5ef675c` and
`docs/solutions/tooling-decisions/vendor-ce-compound-learning-skill.md`.

```
MIT License

Copyright (c) 2025 Every

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
