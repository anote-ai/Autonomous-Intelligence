# Quick Start

## 1. Initialize

```bash
anote init
```

This walks you through setting your API key and preferred LLM provider.

## 2. Ask a question

```bash
# General question
anote ask "how does authentication work in this codebase?"

# Focus on a file
anote ask --file src/auth.ts "explain this"

# Pipe code
cat src/handler.py | anote ask "what could go wrong here?"
```

## 3. Fix bugs automatically

```bash
# Fix and iterate until tests pass (up to 5 rounds)
anote fix --loop --max-iterations 5
```

## 4. Index for semantic search

```bash
# Index your codebase (run once, then keep updated)
anote index

# Search semantically
anote search "JWT token validation"
anote search "database connection pool"
```

## 5. Review a PR

```bash
anote review --pr 42
```

## 6. Generate a changelog

```bash
anote changelog --since v1.2.0
```
