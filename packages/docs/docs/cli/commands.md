# CLI Commands

## `anote ask`

Ask any question about your code.

```bash
anote ask "how does the authentication middleware work?"
anote ask --file src/auth.ts "explain this file"
anote ask --compare  # side-by-side across multiple models
cat file.py | anote ask "find bugs"
```

## `anote fix`

Fix bugs in the current directory.

```bash
anote fix
anote fix --loop                    # iterate until tests pass
anote fix --max-iterations 5        # cap iterations
anote fix --file src/broken.ts      # fix a specific file
```

## `anote review`

Review code for bugs, security issues, and quality.

```bash
anote review                        # review current directory
anote review --file src/handler.ts  # review a specific file
anote review --pr 42                # post AI review on GitHub PR
```

## `anote index`

Build a TF-IDF semantic search index of your codebase.

```bash
anote index              # index current directory
anote index --watch      # watch for changes and re-index
anote index /path/to/dir # index a specific directory
```

## `anote search`

Search your indexed codebase semantically.

```bash
anote search "JWT token validation"
anote search "database connection" --top 10
anote search "auth middleware" --json
```

## `anote doctor`

Check your environment for configuration issues.

```bash
anote doctor
```

Checks: Node.js version, API keys, config file, CLAUDE.md, semantic index, Anote server, git, gh CLI.

## `anote changelog`

Generate a CHANGELOG.md entry from git history.

```bash
anote changelog
anote changelog --since v1.2.0
anote changelog --dry-run
```

## `anote docs`

Generate documentation for undocumented code.

```bash
anote docs
anote docs src/api.ts
anote docs --style jsdoc
anote docs --dry-run
```

## `anote migrate`

AI-assisted codebase migration.

```bash
anote migrate --from "React 17" --to "React 18"
anote migrate --from "axios" --to "fetch"
anote migrate --dry-run
```

## `anote security`

Security audit of your codebase (OWASP Top 10).

```bash
anote security
anote security --severity high
anote security --fix
```

## `anote perf`

Performance analysis.

```bash
anote perf
anote perf --focus "database,bundle"
anote perf --fix
```
