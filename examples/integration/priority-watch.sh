#!/bin/sh
# Filesystem watch. Feeds freshness inputs the other two cadences consume:
# which TOUCHES surfaces changed, and when.
#
# It deliberately does not evaluate on every event. An editor writing a file
# thirty times a second would otherwise produce thirty rankings, none of which
# anyone reads. Debounce, then evaluate once.
set -eu
DOC="${PRIORITY_DOCUMENT:-priority.dsl}"
DEBOUNCE="${PRIORITY_DEBOUNCE:-10}"

command -v inotifywait >/dev/null 2>&1 || {
    echo "inotifywait not found; the interval cadence still covers this repo" >&2
    exit 0
}

# Watch only the surfaces the document claims to care about.
SURFACES=$(priority render "$DOC" | awk '/^  TOUCHES /{print $2}' | sort -u)
[ -n "$SURFACES" ] || exit 0

while true; do
    # shellcheck disable=SC2086
    inotifywait -qq -r -e modify,create,delete $SURFACES 2>/dev/null || true
    sleep "$DEBOUNCE"
    priority project "$DOC" --probe --write >/dev/null 2>&1 || true
done
