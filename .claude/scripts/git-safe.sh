#!/bin/bash
# Safe git wrapper that blocks commits

if [[ "$1" == "commit" ]] || [[ "$1" == "push" ]]; then
    echo "❌ Git $1 blocked by git-safe wrapper!" >&2
    echo "🔧 Use '/usr/bin/git $*' to bypass if explicitly authorized." >&2
    echo "💡 Or set ALLOW_COMMITS=1 environment variable." >&2
    
    if [[ "${ALLOW_COMMITS}" == "1" ]]; then
        echo "✅ ALLOW_COMMITS=1 detected, proceeding..." >&2
        /usr/bin/git "$@"
    else
        exit 1
    fi
else
    # Pass through all other git commands
    /usr/bin/git "$@"
fi