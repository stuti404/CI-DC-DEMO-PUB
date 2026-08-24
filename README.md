# CI/CD Demo: Databricks Pipeline Migration (Azure DevOps -> GitHub + AWS)

This repo is a **dummy, no-real-data proving ground** for the Azure DevOps ->
GitHub + AWS CodeBuild migration described in `Production_Deployment_Runbook.docx`
and `Migration_Conventions_and_Branching.docx`. Nothing here touches a real
catalogue or production workspace. Its only job is to prove that the
pipeline plumbing - branches, gates, buildspecs, webhooks, IAM, secrets,
artifacts - actually works, *before* a real Databricks pipeline repo gets
pointed at this setup.

This document walks through **everything that was built, in the order it
was built, and why** - so anyone picking this up later understands not just
what exists, but the reasoning and the real bugs hit along the way. Two
independent end-to-end pipelines exist side by side; both are documented
below with their own benefits and gaps.

---

## 1. Why this exists

The migration docs describe a target architecture (GitHub branches with
gated protection, AWS CodeBuild running `databricks bundle` commands,
CodePipeline approval gates) but describing an architecture on paper and
having it actually run are different things. Rather than migrate a real
pipeline repo straight into this and find out what breaks in production,
this dummy repo exists to find every integration bug first, in a
disposable, data-free environment.

**Benefit:** every bug found here is a bug that never happens during a real
migration. **Limitation:** a dummy repo can't perfectly reproduce every
condition of a real one - see the Gaps section for the differences that
still need re-testing once a real repo is migrated (a real service
principal, a real production catalogue, a real admin-owned workspace).

---

## 2. The dummy pipeline content

**What:** `databricks.yml` (bundle config), `PFL/notebooks/*.py` (one dummy
notebook per branch), `PFL/resources/dummy_job.yml` (the job the bundle
deploys), `PFL_EXECUTE/dummy_execute_script.py` (the execute artefact), and
three buildspecs (`buildspec-validate.yml`, `buildspec-publish.yml`,
`buildspec-execute.yml`).

**Why one notebook per branch:** each notebook prints a distinct log line
naming its own branch and the approval gate it should have passed through
to get there (e.g. `dummy_smoke_test_prod.py` logs "L2 merge review + L3
manual approval both passed to get here"). That makes it possible to look
at *only the notebook's own execution log* and confirm the pipeline took
the right path, without cross-referencing GitHub separately.

| File | Branch | Gate it asserts already happened |
|---|---|---|
| `dummy_smoke_test_feature.py` | `feature/*` | None - unprotected, `buildspec-validate` only, never deployed |
| `dummy_smoke_test_dev.py` | `dev` | Level 1 review only, auto-deploy |
| `dummy_smoke_test_uat.py` | `uat` | PR from `dev`, QA/business validation before promoting |
| `dummy_smoke_test_prod.py` | `main` | Level 2 merge review + Level 3 manual approval |
| `dummy_smoke_test_hotfix.py` | `hotfix/*` | Fast-track review, must back-merge into `uat`/`dev` same day |

**Why three separate buildspecs instead of one:** they have different blast
radii and different triggers. `validate` never touches a real workspace, so
it's safe to run on *every* push/PR on *every* branch - it's the fast,
side-effect-free required check that gates merges. `publish`/`execute` do
touch real infrastructure (Databricks deploys, job runs), so they're scoped
to only fire on `main`/`uat`/`dev` and only when their respective path
(`PFL/**` or `PFL_EXECUTE/**`) actually changed.

**Benefit:** PR feedback is fast and never risks touching a workspace by
accident; deploys only happen on the branches that are supposed to deploy.

---

## 3. GitHub branch protection

**What:** `main`, `uat`, `dev` each got a branch protection rule requiring
a PR, a required `buildspec-validate` status check, and (for `main`/`uat`)
a required approving review + "require approval of the most recent push".

**Why:** this is the GitHub-side enforcement of the same approval model the
docs describe (L1/L2/L3 review levels) - without it, the CI/CD pipeline
could be bypassed just by pushing straight to `main`.

**A real, non-obvious bug found here:** GitHub's classic *Protected tags*
feature is deprecated. It has been replaced by **Repository Rulesets**
(`target: "tag"`), which use a different API (`POST /repos/{owner}/{repo}/rulesets`,
not the old `tags/protection` endpoint, which now 404s). The equivalent
tag-protection ruleset for this repo blocks deletion and force-updates on
every tag.

**Another real, non-obvious limitation found:** GitHub's *classic* branch
protection has no native "require this PR to come from branch X" setting
(needed because Doc Sec 2.1 requires PRs into `uat` to come specifically
from `dev`). That had to be built as a custom GitHub Actions workflow
(`.github/workflows/enforce-uat-source-branch.yml`) added as an extra
required status check - see Section 6 for the bugs hit getting *that*
actually enforced.

**Gap:** on GitHub's free plan, branch protection is only available on
**public** repos - private repos need GitHub Pro/Team/Enterprise. This demo
repo is public as a result. A real production migration repo would need a
paid plan/org to keep the repo private *and* enforce these rules.

---

## 4. Getting a Databricks workspace to actually run against

**What:** got access to a real (but non-production) Databricks workspace,
generated a personal access token, and used it in place of a proper service
principal.

**Why it isn't a service principal:** creating a service principal requires
Databricks *workspace admin* rights (`only accessible by admins`), which
this account doesn't have - it's a member of the `users` group, not
`admins`. A personal access token was the only way to actually exercise the
pipeline without waiting on an admin.

**Real bugs found from this constraint alone:**
- The account also can't write to the workspace root (`/PFL`) - only under
  its own `/Users/<email>/...` path. `databricks.yml`'s `root_path` had to
  be pointed there instead of `/Workspace/PFL/` as the docs specify.
- The account also lacks "allow cluster creation" entitlement, so the dummy
  job had to run on **serverless compute** instead of a classic job cluster
  (which also fixed an unrelated Azure-vs-AWS node-type mismatch -
  `Standard_DS3_v2` doesn't exist on AWS Databricks).

**Benefit:** the pipeline was provably testable *today*, without blocking on
an admin grant.

**Gap - this is the single biggest thing not yet re-tested:** a real
migration is specified to use a service principal (Doc Sec 5.1), deploying
to `/Workspace/PFL/` with `CAN_MANAGE` granted explicitly (Doc Sec 8.3).
None of that is exercised here. Before a real migration, get an admin to
create the SP, grant it `CAN_MANAGE` on `/Workspace/PFL/`, and re-run this
whole test procedure with the SP's credentials instead of a personal token.

---

## 5. Wiring up AWS CodeBuild (the "Default project" pipeline)

**What:** three CodeBuild projects - `<repo>-publish`, `<repo>-execute`,
`<repo>-validate` (per Doc Sec 4's "standard 2 (+1) projects per repo"),
each with a GitHub webhook, wired to the buildspecs in Section 2.

**Real bugs found and fixed while making this actually run (not just look
configured):**

1. **`databricks.yml`'s `workspace.host: ${DATABRICKS_HOST_DEV}` doesn't
   work.** The Databricks CLI explicitly refuses `${VAR}` interpolation on
   authentication fields. Fixed by removing `host:` entirely and relying on
   the `DATABRICKS_HOST` *environment variable* at deploy time instead -
   `buildspec-publish.yml`/`buildspec-execute.yml` export it per-branch
   before invoking `databricks bundle`.
2. **The `env.secrets-manager` block resolves *before* `pre_build` runs.**
   The original buildspec tried to build a per-branch secret path
   (`databricks/${BUNDLE_TARGET}/sp`) where `BUNDLE_TARGET` was only set
   later, in `pre_build` - so it always resolved to the literal, nonexistent
   secret `databricks//sp`. Fixed by using one fixed `DATABRICKS_TOKEN`
   secret instead of a templated per-target path.
3. **A colon inside a quoted buildspec command string breaks CodeBuild's
   YAML parser.** `echo "buildspec-validate: OK"` was misread as a nested
   YAML mapping key, not a plain string, causing `Expected Commands[2] to be
   of string type: found subkeys instead`. Fixed by rewording the message
   to avoid the colon.
4. **A shared IAM role's CloudWatch Logs permission silently narrowed to
   one project.** After creating the second and third CodeBuild projects
   reusing the same service role, the role's auto-generated base policy
   ended up scoped to only the most-recently-touched project's log group -
   breaking logging (and therefore the build) for the other two. Fixed with
   an explicit inline policy covering all three projects' log groups,
   report groups, the S3 artifact bucket, and the Secrets Manager secret.
5. **The CodeBuild-to-GitHub source credential can go stale independently
   of everything else looking correct.** Webhook creation failed with a
   generic `OAuthProviderException` even though the stored PAT had the
   right scopes and wasn't rate-limited - the credential *object* itself
   needed to be refreshed (`import-source-credentials`) before webhooks
   would create successfully.
6. **CodeBuild reports GitHub status under an auto-generated context name**
   (`AWS CodeBuild <region> (<project>)`), not whatever name you intend -
   unless you explicitly set `source.buildStatusConfig.context`. Without
   that, a branch protection rule that requires a context literally named
   `buildspec-validate` will wait forever for a check that will never
   report under that name.

**Benefit:** every one of these is exactly the kind of bug that would
otherwise surface for the first time during a real, high-stakes migration
cutover. Finding and fixing them here, against dummy data, cost nothing.

**Gap:** the CodeBuild service role here is broader than Doc Sec 5.3's
least-privilege spec would allow in production (it was built incrementally
to unblock testing, not designed top-down). Before reuse in production,
audit and tighten it to exactly the actions/resources actually needed.

---

## 6. Testing the full branch lifecycle, including the hotfix path

**What:** propagated the fixes in Section 5 to `main`, `uat`, and `hotfix`
(not just `dev`, where they were first found), then actually rehearsed a
hotfix: branch off `main`, PR straight to `main`, merge, then same-day
back-merge into `uat` and `dev` (Doc Sec 10.1).

**Real bugs found doing this rehearsal (each one only surfaces if you
actually run the flow end-to-end, not just read the docs):**

1. **git can't have a branch literally named `hotfix` coexist with
   `hotfix/<ticket>` branches.** A ref can't be both a leaf and a directory
   in git's namespace. Since `hotfix` was made a persistent branch earlier
   (to test its own protection rule, mirroring `dev`/`uat`/`main`), the
   *real* `hotfix/<ticket>-<desc>` naming convention from the docs can never
   be used in this specific repo. Worked around with a one-off differently
   named branch for the rehearsal; a real repo should never create a bare
   `hotfix` branch in the first place.
2. **GitHub Actions was completely disabled at the repo level** - zero
   workflow runs, ever. This silently made the custom `check-source-branch`
   required check (Section 3) wait forever, since a required check that
   never runs can never merge. Not obvious from the PR UI alone (it just
   says "waiting for status to be reported", identical to what a slow CI
   run looks like).
3. **The `enforce-uat-source-branch.yml` workflow file only existed on
   `main`, never on `uat`.** For `pull_request`-triggered workflows, GitHub
   needs the workflow file to exist on the ref it's evaluating against - it
   isn't enough for the file to exist somewhere else in the repo, even the
   default branch.
4. **The source-branch check's own logic didn't account for its own
   requirement.** Doc Sec 2.1 says `uat` only accepts PRs from `dev`; Doc
   Sec 10.1 says hotfixes must *also* back-merge directly into `uat`. Those
   two rules conflict unless the check explicitly allows both. Fixed by
   allowing the source branch to be `dev` **or** contain `hotfix` -
   which took two attempts: the first fix used a `hotfix*` (starts-with)
   pattern, but the actual back-merge branch name was
   `backmerge-hotfix-pfl-0000-uat`, which contains "hotfix" but doesn't
   start with it.

**Benefit:** this is the single most valuable phase of the whole exercise -
it's the difference between "the docs describe a hotfix process" and "a
hotfix has actually been pushed through this exact pipeline, hit real
friction, and the friction got fixed."

**Gap:** the hotfix rehearsal used a workaround branch name
(`hotfix-ticket-0000`), not the real `hotfix/<ticket>-<desc>` convention,
for the git-namespace reason above. A real repo should not create a bare
`hotfix` branch, so this collision shouldn't recur there - but that's
untested; confirm on the first real hotfix in production.

---

## 7. The second pipeline: GitHub Actions + CodeBuild Runner project

**What:** a completely independent second pipeline
(`.github/workflows/notebook-runner-pipeline.yml`) where **GitHub Actions**
does the orchestration (not CodeBuild webhooks) and a CodeBuild project of
type **"Runner project"** just supplies self-hosted compute for the
Actions jobs to run on.

**Why build a second pipeline at all:** AWS CodeBuild's console offers
"Runner project" as an explicit, separate option from the classic "Default
project" used in Section 5. Whether an organisation's approved AWS setup
uses one, the other, or both is a real decision point - so both were built
and proven, rather than assuming one approach.

**A real API-discovery bug, not just a config bug:** "Runner project" is
**not** a distinct API-level project type. There is no `buildType: RUNNER`
field and no `runnerModifier` object on `codebuild:CreateProject` - those
don't exist in the API at all (multiple botocore/boto3 versions, including
the latest available, confirm this). The console's "Runner project" wizard
is a UX wrapper over the *ordinary* `CreateProject` call (`GITHUB` source,
pointed at the real repo) plus a `CreateWebhook` call filtered on the
`WORKFLOW_JOB_QUEUED` event - nothing more exotic than that.

**Getting an artifact into S3 from this pipeline (via OIDC, no static AWS
keys) surfaced one more real bug:** the trust policy on the deploy role used
the textbook `repo:owner/repo:*` `sub`-claim pattern - which works for
GitHub-hosted runners, but **jobs running on a CodeBuild Runner project get
a different `sub` claim shape**: `repo:owner@<ownerId>/repo@<repoId>:ref:...`
(numeric owner/repo IDs embedded, presumably to disambiguate against
renames for this runner type). The trust policy's `StringLike` condition
had to be widened to `repo:stuti404*/CI-DC-DEMO-PUB*:*` to match both
shapes. This was only findable by reading the exact denied request from
CloudTrail (`aws cloudtrail lookup-events` on `AssumeRoleWithWebIdentity`) -
the GitHub Actions log alone only ever showed a generic "not authorized"
message.

**Benefit:** the artifact this pipeline produces is published to **two**
independent locations - a downloadable GitHub Actions artifact *and* an S3
object - giving two different consumption paths (a human downloading it
from the Actions run, or another AWS process pulling it from S3) without
needing to pick just one.

**Gap:** this pipeline's `runs-on:` label
(`codebuild-pfl-databricks-runner-...`) and its CodeBuild project share one
IAM service role and one Databricks personal token with the first pipeline
- fine for a dummy demo proving both work, but a real deployment should
decide whether these two pipeline types are meant to coexist long-term or
whether one should be retired, and give each its own least-privilege role
if they do coexist.

---

## 8. What's genuinely working right now

- Full `validate -> publish -> execute` lifecycle, on real (non-production)
  Databricks infrastructure, via **two independent pipeline mechanisms**.
- Branch protection with required reviews + required status checks on
  `main`, `uat`, `dev`.
- A custom, tested enforcement of the "uat only accepts PRs from dev (or a
  hotfix back-merge)" rule that classic branch protection can't express.
- A full hotfix rehearsal: branch -> PR to main -> merge -> deploy ->
  back-merge into uat and dev -> checks re-verified on both.
- AWS resource tagging (`Owner`/`Project`/`Environment`/`CostCentre`) across
  every CodeBuild project, the S3 bucket, IAM roles, and the Secrets
  Manager secret.
- Tag protection (via Ruleset, not the deprecated classic feature) blocking
  tag deletion/force-update.
- Build artifacts published to GitHub Actions **and** S3, via OIDC with no
  static AWS credentials in the workflow.

## 9. Where this demo is still lacking (read before reusing any of this)

1. **No real service principal was ever used.** Everything ran on a
   personal access token because this account isn't a workspace admin.
   Re-test with a real SP, deploying to `/Workspace/PFL/` with `CAN_MANAGE`
   explicitly granted, before trusting this against a real migration.
2. **The `hotfix` branch-naming collision is unresolved**, only worked
   around. Confirm a real repo (which shouldn't have a bare `hotfix`
   branch) doesn't hit the same issue - it shouldn't, but it's unverified.
3. **The CodeBuild service role is broader than least-privilege.** It grew
   incrementally to unblock testing rather than being scoped top-down per
   Doc Sec 5.3. Audit before reuse.
4. **This repo is public**, which was necessary only because GitHub's free
   plan doesn't support branch protection on private repos. A real
   migration repo needs a paid GitHub plan/org to be both private and
   protected.
5. **CodePipeline's manual-approval (L3) gate was never built or tested
   here** - only the GitHub-side L1/L2 review gates and the CodeBuild
   deploy steps. The docs' full approval chain (Doc Sec 6) includes an SNS
   notification to a named prod release approver via CodePipeline, which is
   outside what these two pipelines currently do.
6. **Two pipeline types now exist side by side with no decision made on
   which is the long-term one.** Both work; picking (or explicitly keeping
   both) is a decision for whoever owns this migration, not something this
   demo settles.
7. **AWS credentials used throughout this exercise were short-lived STS
   tokens pasted directly into a chat session at several points.** They
   were never written into any file, buildspec, or workflow - but as a
   process matter, credentials shared this way should always be treated as
   compromised and the owner should rotate/revoke them, even though they
   expire on their own.

---

## 10. File map

| Path | Purpose |
|---|---|
| `databricks.yml` | Bundle config, all three targets, no `host`/`run_as` interpolation |
| `PFL/notebooks/dummy_smoke_test_*.py` | One dummy notebook per branch/gate |
| `PFL/resources/dummy_job.yml` | The job resource the bundle deploys (serverless compute) |
| `PFL_EXECUTE/dummy_execute_script.py` | The dummy execute artefact |
| `buildspec-validate.yml` | Runs on every push/PR, all branches - the required check |
| `buildspec-publish.yml` | Runs on push to `main`/`uat`/`dev` under `PFL/**` |
| `buildspec-execute.yml` | Runs on push to `main`/`uat`/`dev` under `PFL_EXECUTE/**` |
| `.github/workflows/enforce-uat-source-branch.yml` | Custom required check: PRs into `uat` must come from `dev` or be a hotfix back-merge |
| `.github/workflows/notebook-runner-pipeline.yml` | The second, independent GitHub-Actions/CodeBuild-Runner pipeline |
| `docs/codebuild-runner-setup.md` | How the Runner project + OIDC role were actually provisioned |
