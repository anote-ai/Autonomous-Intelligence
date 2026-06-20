# Installation

## CLI

```bash
npm install -g @anote-ai/anote
```

Requires Node.js 18 or later.

## VS Code Extension

Search for **"Anote"** in the VS Code Extensions marketplace, or install via:

```bash
code --install-extension anote-ai.anote-ai-coding
```

## Web App (Self-hosted)

```bash
git clone https://github.com/anote-ai/panacea.git
cd panacea
cp packages/backend/.env.example packages/backend/.env
# Edit .env with your API keys
docker compose up
```

Frontend: http://localhost:3000 · Backend: http://localhost:5000

## Desktop App

Download the latest release from [GitHub Releases](https://github.com/anote-ai/panacea/releases).

Available for: **macOS** (DMG), **Windows** (installer), **Linux** (AppImage/DEB/RPM).

## Python SDK

```bash
pip install anote-ai
```

## TypeScript/JavaScript SDK

```bash
npm install @anote-ai/sdk
```
