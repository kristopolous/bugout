#!/bin/bash

for i in microsoft/PowerToys microsoft/vscode microsoft/TypeScript facebook/react facebook/react-native facebook/docusaurus facebook/zstd; do
what=$(basename $i)
[[ -s "${what}.csv" ]] && continue
gh issue list --repo $i --limit 250 --json number,title,state,labels,body,author,createdAt,comments \
  | jq -r '
    ["issue_number","issue_title","state","labels","author","created_at","type","text"],
    (
      .[] | . as $issue |
      (
        # Issue body as first row
        [$issue.number, $issue.title, $issue.state, ($issue.labels | map(.name) | join(";")), $issue.author.login, $issue.createdAt, "issue", $issue.body],
        # Then each comment
        ($issue.comments[] | [$issue.number, $issue.title, $issue.state, ($issue.labels | map(.name) | join(";")), .author.login, .createdAt, "comment", .body])
      )
    )
    | @csv
  ' > ${what}.csv
done
exit

grabeach() {
    project="$1"
    set -x
    cat "$project/list" | cut -d ',' -f 1 | while read i; do
        mkdir -p $project
        gh issue view $i --repo $project --json comments | jq -r '.comments[] | [.author.login, .createdAt, .body] | @csv' > $project/$i
    done
}


for i in microsoft/PowerToys microsoft/vscode microsoft/TypeScript; do
    mkdir -p $i
    gh issue list --repo $i --limit 100 --json number,title,comments --jq 'sort_by(.comments | length) | reverse | .[] | [.number, (.comments | length), .title] | @csv' > $i/list
    grabeach $i
done

