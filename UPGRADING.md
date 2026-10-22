# Upgrading WeasyPrint

weasysvg supports one WeasyPrint major version, the latest. It patches WeasyPrint internals, so each new
major needs this procedure. It finds three things: the gaps WeasyPrint closed, which make patches
redundant; the internals that changed, which can break patches; and the renderings that got worse.

## The tools

| Tool | Command | What a failure means |
|---|---|---|
| Gap probes, `upstream/test_gaps.py` | `make upstream` | WeasyPrint closed a gap: the message names the patch to remove |
| Hook snapshot, `upstream/hooks.json` | `make upstream` | WeasyPrint changed an internal weasysvg hooks: the message names the code to review |
| Bench baseline, `corpus/baseline.json` | `make visual-check` | weasysvg renders an SVG worse than before |
| Weekly run, `.github/workflows/upstream.yml` | Actions, every Monday | one of the above, against the latest release and the main branch |

The probes render with WeasyPrint alone, in a process of their own. Each passes while its gap is there.

## When to start

The weekly Upstream run turns red, or Renovate opens a pull request that moves the WeasyPrint pin.
Renovate does not merge it on its own. Work on that branch, or on `chore/weasyprint-<version>`.

## Procedure

1. Move the pin in `pyproject.toml` to `weasyprint>=N,<N+1`, and run `uv lock`.
2. Set `SUPPORTED_MAJOR = N` in `src/weasysvg/__init__.py`.
3. Match the Python versions of WeasyPrint N: `requires-python`, the classifiers, the CI matrix, and
   the Python versions in `README.md` and `CLAUDE.md`.
4. Run `make upstream`. Read each failure:
   - **A failed probe** names the gap WeasyPrint closed and the patch that covers it. Check with the
     bench that WeasyPrint alone now renders the case right. Then remove the patch, its tests and the
     probe. Drop the line from the feature table in `README.md`.
   - **A changed hook** names the internal and the weasysvg code that depends on it. Read the upstream
     change with `git diff vN-1..vN -- <file>` in a clone of Kozea/WeasyPrint. Adapt the weasysvg code
     if the change touches what it relies on.
5. Run `make test`. Fix each failure test first.
6. Run `make visual-check`.
   - **weasysvg worse** than the baseline is a regression: fix it, test first.
   - **WeasyPrint alone better** than the baseline points at a gap it may have closed: compare with
     the probes of step 4.
   Look at the panels of `tools/visual/out/weasysvg/report.html` for every SVG the check lists.
7. When all of it passes:
   - `make hooks` writes `upstream/hooks.json` for WeasyPrint N.
   - `make visual-baseline` writes `corpus/baseline.json`.
   - Review the verdicts in `corpus/verdicts.json` and the counts in `README.md`.
   - `make comparison` writes `corpus/COMPARISON.md` and its panels.
   - Add the upgrade to `CHANGELOG.md`.
8. Open the pull request. Run the CodeRabbit review before the push, as for any change.

## Adding a patch

Each new patch for a WeasyPrint gap comes with:

- a probe in `upstream/test_gaps.py` that shows the gap on WeasyPrint alone and names the patch;
- an entry in `HOOKS` of `tools/upstream/hooks.py` for each internal it replaces or relies on,
  followed by `make hooks`.

A patch that covers no WeasyPrint gap, such as the cache of `fetch.py` for foreignObject documents,
needs no probe. Its hooks still go into the snapshot.
