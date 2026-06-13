#!/bin/bash
# Quick surgical commit + push for cron jobs
# Usage: ./scripts/quick_commit.sh P0 "feat: description" file1.py file2.html
#
# Example:
#   ./scripts/quick_commit.sh P0 "feat: use multi_source in fetch_chart_data" app.py services/stock_data.py

set -e

TAG="${1:?Usage: $0 <P0|P1|P2> <message> [files...]}"
MSG="${2:?Usage: $0 <P0|P1|P2> <message> [files...]}"
shift 2
FILES=("$@")

cd ~/repos/Stocker

# If no files specified, show status and exit
if [ ${#FILES[@]} -eq 0 ]; then
    echo "📋 No files specified. Current status:"
    python3 scripts/stage_commit.py --status
    exit 1
fi

# Stage, commit, push
python3 scripts/stage_commit.py \
    --tag "$TAG" \
    --message "$MSG" \
    --files "${FILES[@]}" \
    --push
