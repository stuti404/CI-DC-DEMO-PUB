# CI/CD Pipeline: dev → uat → main

Industry-grade GitHub Actions + AWS CodeBuild pipeline for the Databricks migration, hardened against the common failure modes of a three-environment (`dev`/`uat`/`main` = staging/UAT/prod) branching model: direct-to-prod merges, stale approvals, secret leaks, and unbounded build overhead.

## 1. What was done

| Area | Change |
|---|---|
| Merge-direction enforcement | `enforce-uat-source-branch.yml` / `enforce-main-source-branch.yml` — custom head-ref status checks that only accept PRs into `uat` from `dev`, and into `main` from `uat` or `hotfix/*`. Anything else auto-closes with an explanatory comment. |
| Stale-branch handling | `auto-update-pr-branches.yml` — on every push to `dev`/`uat`/`main`, calls the GitHub `update-branch` API for all open PRs targeting that branch, so PRs don't sit "out of date" waiting on a human to click a button. |
| Hotfix flow | `backport-hotfix.yml` — a hotfix merged into `main` is automatically cherry-picked back into `dev` via a bot-opened PR. |
| Code ownership | `CODEOWNERS` — path-split (`/databricks.yml`, `/PFL/resources/`, `/PFL/notebooks/`, `/.github/`), single owner today, pre-staged for a second reviewer to take `/PFL/notebooks/` with a one-line change. |
| Selective builds | `notebook-runner-pipeline.yml` packages only the files that actually changed (`git diff --diff-filter=ACMR` scoped to `PFL/` and `databricks.yml`) into the deploy artifact, instead of re-bundling everything on every push. |
| Secret-leak defense | GitHub secret scanning + push protection enabled repo-wide; a Gitleaks job added to the pipeline (advisory, full-history scan on every PR). |
| Deployment gating | A `production` GitHub Environment with a required-reviewer gate in front of `publish-prod`, independent of branch protection. |

## 2. Why this approach over the alternatives

- **Custom head-ref check instead of a paid app.** GitHub has no native "only accept PRs from branch X" setting. Mergify/Kodiak-style merge queues and bots solve a different problem (serializing merges under contention) and are premature at this PR volume. A ~15-line status-check step, gated as a required check, is the standard DIY pattern real orgs use for this and costs nothing.
- **`update-branch` API instead of a merge queue.** A merge queue is the right tool once multiple PRs are landing on the same branch daily and racing each other. At this repo's PR volume, that's overhead without benefit — the auto-update workflow gets the same practical outcome (no PR silently going stale) without the queueing infrastructure.
- **Single CODEOWNERS file, path-split, not forked per branch.** GitHub reads CODEOWNERS from the PR's *base* branch, so forking its content across `dev`/`uat`/`main` is technically possible — but it's a drift trap: three files that are supposed to converge but can silently diverge. A single file with path-level splits gets the same future flexibility (hand off `/PFL/notebooks/` to a second reviewer with a one-line change) without three sources of truth.
- **`Stuti-Ganit` is never a CODEOWNERS entry.** GitHub structurally blocks a PR author from approving their own PR. Since `Stuti-Ganit` opens nearly every PR into `dev`/`uat`, adding them as an owner would never function as a real second reviewer — it would silently no-op back to `stuti404`. Documented in `CODEOWNERS` itself so a future reader doesn't "fix" this by adding them.
- **Case-sensitive, exact-match `HEAD_REF` comparison — not relaxed.** Considered and rejected: git ref names cannot contain whitespace, and folding case would treat a typo'd branch (`Dev`) as equivalent to `dev`, which is a strictness *regression*, not a hardening.
- **Gitleaks added as a job inside the existing required pipeline, not a new standalone workflow.** A new workflow file would need its own required-check registration across three branches, doubling what has to stay in sync. Adding a job to the file that's already required on every PR keeps one source of truth, while the job itself is *not* added to the required-checks list — so it reports findings without being able to block merges yet.

## 3. Concrete benefits

- A public repo now has real secret-leak defenses (push protection + secret scanning + Gitleaks) at zero licensing cost.
- `CODEOWNERS` no longer references three files that were deleted from the repo months ago.
- The notebook path structure is pre-staged for a second reviewer with no future restructuring.
- Selective packaging means a PR that only touches `PFL_EXECUTE/` doesn't rebuild and re-upload the entire bundle.
- Direct-to-prod and reverse-direction merges are structurally impossible to land silently — they're rejected in seconds, with an explanation, not caught later in a review.

## 4. Known trade-offs and real gaps found during verification

These aren't hypothetical — they were hit and confirmed while testing this pass:

- **Single-approver bottleneck.** `stuti404` is the only real CODEOWNERS approver today (see §2's rationale on `Stuti-Ganit`). This is fine for a 2-account demo; it's the first thing to change when a second real reviewer joins.
- **`uat` has no automated hotfix backport.** `backport-hotfix.yml` only targets `dev`. A hotfix merged straight into `main` leaves `uat` behind until someone runs the normal `dev → uat` promotion — and if `dev` itself hasn't picked up the hotfix yet either, `uat` can drift for a while. This surfaced directly during this hardening pass: `main` had accumulated 5 commits that neither `uat` nor `dev` had, entirely from earlier governance work pushed straight to `main`. It was fixed with a one-time admin-bypass sync (temporarily disabling `enforce_admins`, pushing a merge commit, restoring it) rather than a permanent process — the durable fix is a second backport target on `uat`, tracked in the backlog below.
- **Backport PRs require a manual workflow-run approval.** PRs opened by `github-actions[bot]` (the backport action) triggered `action_required` workflow runs with zero jobs dispatched — GitHub treated the bot-authored PR similarly to a first-time-contributor PR. A human has to hit "approve and run" via `POST /actions/runs/{id}/approve` before the backport PR's checks even execute. The backport is *opened* automatically; it isn't *merged* automatically.
- **Squash-merge required on `main` (linear history) plus multi-branch promotion produces phantom drift.** After a squash merge, `git compare`'s `ahead_by`/`behind_by` counts show divergence even when file content is byte-identical across branches — the commit graphs differ even though the trees match. Verify actual content (`compare_url`'s `files` list, or direct file diffs), not commit counts, when checking whether branches are "in sync."
- **GitHub's native secret scanning didn't flag a synthetic-but-realistic fake AWS key** (stricter format/checksum validation than Gitleaks' regex matching); Gitleaks did. Push protection + secret scanning are the first line of defense for genuine leaked credentials; Gitleaks is the wider net that also catches synthetic or malformed-but-plausible patterns.
- **Gitleaks is advisory only, by design, for now** — it reports on every PR but cannot block a merge until it has a burn-in period with zero false positives.

## 5. Backlog (not in this pass, with explicit triggers)

| Item | Trigger condition |
|---|---|
| GitHub native Merge Queue | 2+ PRs/day merging into the same branch, causing real auto-update-then-conflict churn |
| Turborepo/Nx-style affected-graph selective builds | Repo grows past "one file per folder"; Databricks bundles gain partial-deploy support |
| Automated hotfix backport to `uat`, not just `dev` | Now — this is the direct cause of the drift found during this pass; next priority |
| Promote Gitleaks to a required/blocking check | After a burn-in period with zero false positives |
| Hand `/PFL/notebooks/` CODEOWNERS to a second real reviewer | As soon as a second real reviewer account exists |
| Raise required-approval-count above 1 on any branch | As soon as 2+ non-author reviewers are consistently available |
| TruffleHog scheduled deep-history scan | Once Gitleaks is stable and blocking — catches secrets that predate Gitleaks' PR-time introduction |
| Auto-approve backport workflow runs (or use a PAT instead of `GITHUB_TOKEN` for the backport action) | Now, if manual approval on every hotfix backport becomes a real friction point |

## 6. Verification evidence (this pass)

All tests below were run against the live repo with disposable branches, deleted immediately after:

- **CODEOWNERS gate**: a PR touching `/PFL/notebooks/` auto-requested `stuti404` as reviewer; `Stuti-Ganit` (author) got `422 Can not approve your own pull request`; `stuti404`'s approval alone made the PR mergeable.
- **Secret-leak defense**: AWS's own documented example key was correctly *not* flagged (known allowlisted pattern); a random fake key pattern was flagged by Gitleaks (job failed) while the PR remained mergeable (`unstable`, not `blocked`) — confirming advisory-only behavior.
- **HEAD_REF regression**: a spoofed branch name (`not-a-hotfix-totally-legit-2`) into `main` was still correctly auto-rejected and auto-closed.
- **Positive flows**: `dev → uat`, `uat → main`, and `hotfix/* → main` (including the automatic backport PR into `dev`) all completed successfully.
- **Negative flows**: a random branch into `uat`, `dev` directly into `main` (skipping `uat`), and `main` into `uat` (reverse direction) were all auto-rejected and auto-closed with the correct explanatory comment.
