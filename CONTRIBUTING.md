# Contributing

## Local setup

Use Python 3.12 or newer. From the repository root:

```bash
python3 -m pip install -e '.[dev]'
python3 -m pytest
python3 -m ruff check .
python3 -m ruff format --check .
python3 -m mypy src/smartanalyticsinvest
```

Tests are offline and use local deterministic fixtures only.

## Filing issues

Use the *Bug report* or *Feature request* template when opening an issue. Both
follow the same structure used throughout this repository:

- **Summary** — what's broken or missing, and why it matters.
- **Scope** — the concrete changes needed.
- **Acceptance Criteria** — how we'll know the issue is resolved (usually
  including "Full pytest suite and `ruff check` remain green.").

Apply one of the existing `type:*` labels (`type:bug`, `type:feature`,
`type:chore`, `type:docs`) so issues stay easy to triage.

## Pull requests

- Branch from `main`.
- Reference the issue you're closing with `Closes #<number>` in the PR
  description.
- Keep the PR description's **Changes** and **Testing** sections accurate —
  reviewers rely on the testing section to know what was actually run.
- Ensure `python3 -m pytest`, `python3 -m ruff check .`,
  `python3 -m ruff format --check .`, and `python3 -m mypy src/smartanalyticsinvest`
  all pass before requesting review, and check off the PR template's
  compliance checklist accordingly.
