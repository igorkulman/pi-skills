# GitHub Verification Workflow

Use for GitHub PR URLs. Apply the shared scope, evidence, authorization, and mutation rules from `../SKILL.md`.

## 1. Fetch PR and thread state

Extract `<OWNER>`, `<REPO>`, and `<PR_NUMBER>` from `https://github.com/<OWNER>/<REPO>/pull/<PR_NUMBER>`.

```bash
command -v gh
gh auth status
gh pr view <PR_NUMBER> --repo <OWNER>/<REPO> --json number,title,url,state,isDraft,headRefOid,baseRefName,headRefName,reviewDecision,statusCheckRollup,comments,reviews,files > /tmp/pi_verify_pr_<PR_NUMBER>.json
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

Count total in-scope self-authored resolvable threads, including resolved threads. If that total is zero, this reviewer has not reviewed the PR; do not approve it.

Count other authors' unresolved threads for reporting only. Do not assess or resolve them unless the user explicitly changes scope.

For each open in-scope thread, apply the shared Addressed / Not addressed / Uncertain contract using all replies, the latest PR diff, and surrounding code as needed. Present the shared assessment together with draft and check status, then show the shared per-thread resolution selector unless the exact resolutions were already authorized.

## 3. Resolve authorized addressed threads

```bash
gh api graphql -f threadId=<THREAD_ID> -f query='mutation($threadId:ID!) { resolveReviewThread(input:{threadId:$threadId}) { thread { id isResolved } } }'
```

Resolve only Addressed threads whose original comment belongs to the authenticated user. Check every result.

## 4. Re-check and optionally approve

Re-fetch review threads and PR metadata/check status. Apply every shared approval gate: total in-scope thread count must be greater than zero, open in-scope count must be zero, the PR must not be a draft, and checks must be passing or absent.

If all gates pass, obtain explicit approval authorization with `ask_user_question` unless approval was already explicitly requested. Only then run:

```bash
gh pr review <PR_NUMBER> --repo <OWNER>/<REPO> --approve
```

Otherwise do not approve and report every blocker.

## 5. Report

Summarize initial total/open in-scope counts, selected/resolved/remaining thread IDs, other-author unresolved count, draft and check state, approval status, pagination limits, and failures.
