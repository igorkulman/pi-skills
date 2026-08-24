# GitHub Verification Workflow

Use for GitHub PR URLs. Apply the shared scope, evidence, authorization, and mutation rules from `../SKILL.md`.

## 1. Fetch PR and thread state

Extract `<OWNER>`, `<REPO>`, and `<PR_NUMBER>` from `https://github.com/<OWNER>/<REPO>/pull/<PR_NUMBER>`.

```bash
command -v gh
gh auth status
gh pr view <PR_NUMBER> --repo <OWNER>/<REPO> --json number,title,url,state,isDraft,headRefOid,baseRefName,headRefName,reviewDecision,comments,reviews,files > /tmp/pi_verify_pr_<PR_NUMBER>.json
gh pr diff <PR_NUMBER> --repo <OWNER>/<REPO> > /tmp/pi_verify_pr_<PR_NUMBER>_diff.txt
```

Fetch review threads:

```bash
gh api graphql -f owner=<OWNER> -f repo=<REPO> -F number=<PR_NUMBER> -f query='query($owner:String!, $repo:String!, $number:Int!) {
  repository(owner:$owner, name:$repo) {
    pullRequest(number:$number) {
      id
      isDraft
      reviewThreads(first:100) {
        nodes {
          id
          isResolved
          isOutdated
          path
          line
          startLine
          comments(first:50) {
            nodes {
              id
              body
              author { login }
              createdAt
              url
              diffHunk
            }
          }
        }
      }
    }
  }
}' > /tmp/pi_verify_pr_<PR_NUMBER>_threads.json
```

If there are more than 100 threads or 50 comments in a thread, report the pagination limitation and ask before continuing with a custom paginated query.

## 2. Identify scope and assess

Determine the authenticated login from `gh auth status`.

In-scope threads satisfy:

- `isResolved == false`
- the first/original review comment author matches the authenticated login

Count other authors' unresolved threads for reporting only. Do not assess or resolve them unless the user explicitly changes scope.

For each in-scope thread, apply the shared Addressed / Not addressed / Uncertain contract using all replies, the latest PR diff, and surrounding code as needed. Present the shared assessment and authorization gate before mutation.

## 3. Resolve authorized addressed threads

```bash
gh api graphql -f threadId=<THREAD_ID> -f query='mutation($threadId:ID!) { resolveReviewThread(input:{threadId:$threadId}) { thread { id isResolved } } }'
```

Resolve only Addressed threads whose original comment belongs to the authenticated user. Check every result.

## 4. Re-check and optionally approve

Re-fetch review threads. If no in-scope self-authored threads remain and approval was explicitly requested:

```bash
gh pr review <PR_NUMBER> --repo <OWNER>/<REPO> --approve
```

Do not approve when in-scope threads remain. Do not approve a draft unless the user explicitly requested approval despite draft state and GitHub allows it.

## 5. Report

Summarize initial/resolved/remaining in-scope thread IDs, other-author unresolved count, approval status, pagination limits, and failures.
