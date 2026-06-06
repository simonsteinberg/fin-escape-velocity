# Versioning and Releases

This document describes how `finev` is versioned and released. It is the
canonical reference for the scheme, the tooling, and the day-to-day workflows —
including how to **retire a version** that turns out to have a security bug.

The operational checklist (the short "what command do I run") lives in
[CLAUDE.md](../CLAUDE.md#versioning-and-releases); this file is the "why" and the
full detail.

---

## 1. The scheme: Semantic Versioning

`finev` follows [Semantic Versioning 2.0.0](https://semver.org/): a version is
`MAJOR.MINOR.PATCH`.

| Part | Bump when… | Example |
|------|------------|---------|
| **MAJOR** | You make an incompatible / breaking change | `1.4.2 → 2.0.0` |
| **MINOR** | You add functionality in a backward-compatible way | `1.4.2 → 1.5.0` |
| **PATCH** | You make a backward-compatible bug fix | `1.4.2 → 1.4.3` |

**Pre-1.0 caveat (we are here).** While the version is `0.y.z`, the public surface
is considered unstable. By convention the `MINOR` slot absorbs breaking changes and
`PATCH` absorbs fixes — so a breaking change pre-1.0 is `0.4.0 → 0.5.0`, not a major
bump. The first stable, compatibility-committed release is `1.0.0`.

**Pre-releases.** A release that is not yet final carries a suffix:
`1.0.0-rc.1` (release candidate), `1.0.0-beta.1`, `1.0.0-alpha.1`. Pre-releases
sort *before* their final version and are flagged as "pre-release" on GitHub so
they are not surfaced as the latest stable build.

---

## 2. Source of truth: `pyproject.toml`

The canonical version number lives in **one place**: the `version` field of
[`pyproject.toml`](../pyproject.toml). Everything else derives from it.

- **Runtime reads it via package metadata.** `finev.greet.get_version()` calls
  `importlib.metadata.version("finev")`, so the running app/CLI report the version
  that was actually installed — no second copy of the number in the source. The
  CLI (`finev-version`), and the version label in the web UI, both go through this
  one function.
- **The git tag mirrors it.** Every release has a matching annotated tag
  `vX.Y.Z`. The tag and the file are kept in lockstep by `mise run release` (see
  below), and the release workflow refuses to publish if they disagree.

> **Golden rule:** never hand-edit the version string. Always change it with
> `uv version --bump …` (driven by `mise run release`). Hand-editing risks an
> invalid string or a file/tag mismatch.

Check the current version any time:

```bash
mise run version        # prints e.g. 0.1.0
```

---

## 3. How GitHub supports versioning

GitHub provides three primitives we build on:

1. **Git tags** — an immutable, named pointer to a specific commit. `v0.1.0` means
   "this exact commit is version 0.1.0." We use **annotated** tags (`git tag -a`),
   which carry a message and author and are the correct kind for releases.
2. **GitHub Releases** — a tag plus human-readable notes and auto-generated source
   archives (`.zip` / `.tar.gz`), shown on the repo's *Releases* page and reachable
   at `…/releases/tag/v0.1.0`. This is what turns a tag into a "downloadable
   version" of the software.
3. **GitHub Security Advisories (GHSA)** — a structured, citable record that a
   given version range is vulnerable. This is GitHub's native mechanism for telling
   users "do not use this version" (see §6).

A pushed tag triggers a GitHub Actions workflow that creates the Release
automatically, so the only manual action is producing the tag.

---

## 4. Cutting a release

### 4.1 The normal path: `mise run release`

For every release after the initial baseline, run a single task with the SemVer
part you are bumping:

```bash
mise run release -- patch     # 0.1.0 -> 0.1.1
mise run release -- minor     # 0.1.0 -> 0.2.0
mise run release -- major     # 0.1.0 -> 1.0.0
```

[`.tasks/release.sh`](../.tasks/release.sh) performs, in order:

1. **Guards** — refuses unless you are on `main`, the working tree is clean, and
   local `main` matches `origin/main`.
2. **Changelog guard** — `.tasks/changelog-check.sh` fails if the `[Unreleased]`
   section of [`CHANGELOG.md`](../CHANGELOG.md) is empty. Every release must carry
   notes.
3. **Full check** — runs `mise run check` (format, lint, types, tests). A release
   is never cut from a red tree.
4. **Bump** — `uv version --bump <part>` rewrites `pyproject.toml`.
5. **Roll the changelog** — promotes `[Unreleased]` to a dated `[X.Y.Z]` section,
   opens a fresh empty `[Unreleased]`, and updates the compare/tag link references.
6. **Commit** — `chore(release): vX.Y.Z` (includes `pyproject.toml`, `uv.lock`,
   `CHANGELOG.md`).
7. **Tag** — annotated `vX.Y.Z`.
8. **Push** — `git push --follow-tags`, which sends the commit and the tag.

Pushing the tag hands off to the release workflow.

### 4.2 What the workflow does

[`.github/workflows/release.yml`](../.github/workflows/release.yml) triggers on any
`v*` tag push and:

1. Checks out the tagged commit with full history (`fetch-depth: 0`).
2. Installs tools and dependencies via `mise`.
3. **Verifies the tag matches `pyproject.toml`** — fails fast on any drift.
4. Re-runs `mise run check` against the tagged commit (independent verification,
   not just trust in the local run).
5. Extracts that version's section from `CHANGELOG.md`
   (`.tasks/changelog-extract.sh`) to use as the release notes.
6. Creates the GitHub Release with `gh release create`, flagging pre-release tags
   (`-rc`/`-alpha`/`-beta`) as pre-releases.

### 4.3 The very first release (`v0.1.0`)

`v0.1.0` is the baseline and is published by tagging the current version directly
(the `release` task always *bumps*, so it is for subsequent releases):

```bash
# on an up-to-date main, with pyproject at 0.1.0
git tag -a v0.1.0 -m v0.1.0
git push --follow-tags
```

The workflow then publishes the `v0.1.0` Release from the `0.1.0` changelog section.

---

## 5. Changelog discipline

[`CHANGELOG.md`](../CHANGELOG.md) follows
[Keep a Changelog](https://keepachangelog.com/). The contract:

- The top has an **`[Unreleased]`** section. As you merge work, add bullets under
  the appropriate category: **Added**, **Changed**, **Deprecated**, **Removed**,
  **Fixed**, **Security**.
- `mise run release` turns `[Unreleased]` into the new dated version section and
  re-opens an empty `[Unreleased]`. You should not hand-edit released sections.
- Link references at the bottom point at GitHub `compare/…` and
  `releases/tag/…` URLs and are maintained by the release task.

`mise run changelog-check` enforces that you do not release with an empty
`[Unreleased]`.

---

## 6. Retiring a version (security bugs)

When a released version has a security bug, the honest reality first: **you cannot
truly recall a git tag.** Anyone who already cloned or fetched it still has it, and
rewriting or deleting a published tag breaks their checkouts. So the goal is not
"erase it" but **"loudly supersede it and warn users."** The GitHub-native playbook:

1. **Fix forward.** Patch the bug and cut a new release — normally a `PATCH` bump
   (`mise run release -- patch`). Record the fix under `### Security` in the
   changelog. A safe upgrade target is the most important deliverable.

2. **Publish a GitHub Security Advisory (GHSA).** In the repo, *Security →
   Advisories → New draft advisory*. State the affected version range (e.g.
   `>= 0.2.0, < 0.2.3`) and the patched version. This is the citable,
   machine-readable "this version is unsafe" signal, and it can feed Dependabot
   alerts for anyone depending on the repo.

3. **Mark the bad Release.** Prefer **editing over deleting** so the historical
   record and the warning both survive:

   ```bash
   # Add a prominent banner to the affected release's notes
   gh release edit v0.2.0 \
     --notes $'⚠️ **SECURITY: do not use this release.**\nAffected by GHSA-xxxx. Upgrade to v0.2.3 or later.\n\n<original notes…>'

   # Optionally remove it from "Latest"
   gh release edit v0.2.0 --latest=false
   ```

   Only if a release must not be downloadable at all:

   ```bash
   gh release delete v0.2.0          # removes the Release page + archives;
                                     # add --cleanup-tag to also delete the tag
   ```

   Deleting the **tag** is discouraged — it breaks anyone who pinned it and rewrites
   shared history. Superseding is almost always the right move.

4. **Record it.** Note the advisory and the superseding version under `### Security`
   in `CHANGELOG.md` so the in-repo history is self-explanatory.

Because `finev` is **GitHub-only** (not published to PyPI), there is no registry
"yank" step — the advisory plus the patched release plus the marked Release are the
complete retirement.

---

## 7. Quick reference

| Task / command | Purpose |
|----------------|---------|
| `mise run version` | Print the current version |
| `mise run changelog-check` | Fail if `[Unreleased]` has no entries |
| `mise run release -- {patch\|minor\|major}` | Bump, roll changelog, commit, tag, push |
| `uv version --short` | Read the version |
| `uv version --bump <part> --dry-run` | Preview a bump without writing |
| `git tag -a vX.Y.Z -m vX.Y.Z && git push --follow-tags` | Publish the initial/baseline release |
| `gh release view vX.Y.Z` | Inspect a published Release |
| `gh release edit vX.Y.Z …` | Re-mark a Release (e.g. security banner) |

| File | Role |
|------|------|
| `pyproject.toml` | Canonical version number |
| `CHANGELOG.md` | Human-written history (Keep a Changelog) |
| `.tasks/release.sh` | Bump + changelog + commit + tag + push |
| `.tasks/changelog-check.sh` | Guards a non-empty `[Unreleased]` |
| `.tasks/changelog-extract.sh` | Extracts a version's notes for the Release |
| `.github/workflows/release.yml` | Tag-triggered Release publisher |
| `src/finev/greet.py` | Runtime version read (`get_version`) |
| `src/finev/ui_view.py` | `version_label_text()` shown in the web UI |
