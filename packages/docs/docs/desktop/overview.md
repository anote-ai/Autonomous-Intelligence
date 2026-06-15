# Desktop App Overview

The Anote AI desktop app is a private, offline-capable AI assistant built with Electron.

## Key Properties

- **Private**: all data stays on your machine
- **Offline capable**: works with local Ollama models
- **Cross-platform**: Windows, macOS, Linux
- **Bundled backend**: Python Flask backend is packaged as a standalone executable

## Architecture

```
Electron shell
  └─ React frontend (Vite + Tailwind)
  └─ Bundled Python backend (PyInstaller executable)
       └─ Flask API on port 5099
       └─ SQLite database (local)
       └─ ChromaDB vector store (local)
```
