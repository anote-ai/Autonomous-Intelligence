# Anote AI Desktop

A private desktop AI assistant. All data stays on your machine.

## Development

```bash
# Install dependencies
npm install
cd frontend && npm install

# Start (dev mode - requires Python backend running separately)
cd packages/backend && python app.py --port 5099 &
npm run dev
```

## Building

```bash
# Bundle Python backend
cd packages/backend
pyinstaller ../desktop/app.spec --distpath ../desktop/backend-dist

# Build Electron app
cd packages/desktop
npm run make
```

Outputs in `out/` directory.
