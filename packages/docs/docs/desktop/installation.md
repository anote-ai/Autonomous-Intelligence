# Desktop App Installation

## Download

Download the latest release for your platform from the GitHub releases page.

| Platform | File |
|----------|------|
| macOS | `Anote-AI-x.x.x.dmg` |
| Windows | `Anote-AI-Setup-x.x.x.exe` |
| Linux (deb) | `anote-ai_x.x.x_amd64.deb` |

## Building from Source

```bash
# 1. Bundle the Python backend
cd packages/backend
pip install pyinstaller
pyinstaller ../desktop/app.spec --distpath ../desktop/backend-dist

# 2. Build and package the Electron app
cd packages/desktop
npm install
npm run make
```

The packaged app is in `packages/desktop/out/`.
