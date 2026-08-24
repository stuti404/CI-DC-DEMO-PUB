# CodeBuild Runner project setup (GitHub Actions -> Databricks)

This is the "Runner project" alternative to the webhook-triggered
`buildspec-validate/publish/execute.yml` pipeline. Instead of CodeBuild
polling/webhook-triggering off pushes, a CodeBuild project of **type
`RUNNER`** registers itself as a self-hosted GitHub Actions runner for this
repo. GitHub Actions (`.github/workflows/notebook-runner-pipeline.yml`)
then does the triggering/orchestration and simply runs its jobs on that
runner via `runs-on: codebuild-<project-name>-...`.

Do this once per environment (dev/uat/prod can share one runner project or
use one each - one shared runner project is enough for this dummy repo).

## 1. Create the Runner project

Console: CodeBuild -> Create build project -> **Project type: Runner
project** -> Runner type: **GitHub Actions**.

Equivalent CLI (run by whoever owns the target AWS account/role - do **not**
run this with short-lived personal credentials pasted into a chat or ticket -
use a named profile or an assumed role from your own shell):

```bash
aws codebuild create-project \
  --name pfl-databricks-runner \
  --source '{"type":"NO_SOURCE"}' \
  --artifacts '{"type":"NO_ARTIFACTS"}' \
  --environment '{
    "type":"LINUX_CONTAINER",
    "image":"aws/codebuild/amazonlinux-x86_64-standard:5.0",
    "computeType":"BUILD_GENERAL1_SMALL"
  }' \
  --service-role <CodeBuildServiceRoleArn> \
  --project-visibility PRIVATE \
  --auto-retry-limit 1 \
  --region <region>
```

Runner-specific configuration (`runner-modifier`) is set via the console or
`aws codebuild create-project ... --cli-input-json` with:

```json
{
  "buildType": "RUNNER",
  "runnerModifier": {
    "runnerName": "pfl-databricks-runner",
    "runnerType": "GITHUB_ACTIONS",
    "labels": ["pfl-databricks-runner"]
  }
}
```

The label(s) here are what `runs-on:` in the workflow must match (this repo
uses the `codebuild-pfl-databricks-runner-<run-id>-<attempt>` convention,
CodeBuild's documented naming pattern for GitHub-Actions runner labels).

## 2. Connect the runner project to this GitHub repo

CodeBuild Runner projects use the GitHub App connection (the same
`aws-signer/codebuild` GitHub App used by CodeBuild's native GitHub source
integration). In the console, when creating/editing the Runner project:

1. Source connection -> GitHub -> authorize the `AWS Connector for GitHub`
   app for this org/repo if not already authorized (this mirrors the
   webhook-based projects' existing connection - re-use it).
2. Confirm the project appears as an available runner under
   **Repo Settings -> Actions -> Runners** on the GitHub side.

## 3. Secrets and variables

Same values the existing buildspecs already use - just exposed to GitHub
Actions instead of CodeBuild's `env.secrets-manager` block:

| Name | Where | Value |
|---|---|---|
| `DATABRICKS_TOKEN` | Repo secret | same PAT as `databricks-dummy-token-cicd-demo:DATABRICKS_TOKEN` in Secrets Manager |
| `DATABRICKS_HOST_DEV` / `_UAT` / `_PROD` | Repo/environment variable | same hosts already used by the buildspecs |
| `DATABRICKS_SP_CLIENT_ID` | Repo/environment variable | same service principal used by uat/prod targets in `databricks.yml` |

Set these under **Repo Settings -> Secrets and variables -> Actions**.

## 4. Artifact publish role (optional S3 copy)

The workflow always publishes the build artifact to GitHub Actions
(`actions/upload-artifact`). To also copy it to S3, create an OIDC deploy
role instead of using static IAM keys:

```bash
aws iam create-role \
  --role-name pfl-databricks-artifact-publish \
  --assume-role-policy-document file://github-oidc-trust-policy.json
```

Trust policy must scope `token.actions.githubusercontent.com` to this repo
(`repo:<org>/databricks-test-cicd:*`). Attach a policy scoped to
`s3:PutObject` on the target bucket/prefix only. Then set repo variables:

- `ARTIFACT_S3_BUCKET`
- `ARTIFACT_PUBLISH_ROLE_ARN`
- `AWS_REGION`

Leave these unset to skip the S3 step - GitHub Actions artifact publish
still happens either way.

## Security note

Never put static `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` /
`AWS_SESSION_TOKEN` values into workflow files, buildspecs, or chat. If a
set of credentials has been shared in a chat, ticket, or log, treat it as
compromised and rotate/revoke it (`aws sts get-caller-identity` to see whose
it is, then have that principal's owner deactivate/rotate it) even if it is
a short-lived STS token - it is valid until it naturally expires. Use OIDC
federation (as in Step 4) or the CodeBuild service role for everything this
pipeline needs.
