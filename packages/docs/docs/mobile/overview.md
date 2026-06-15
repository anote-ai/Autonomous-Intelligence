# Mobile App Overview

The Anote AI mobile app is built with [Expo](https://expo.dev) and React Native.

## Features

- Native iOS and Android support
- Light/dark mode (follows system preference)
- Chat interface with streaming responses
- Session history with slide-in sidebar
- Secure JWT storage via `expo-secure-store`

## Running Locally

```bash
cd packages/mobile
npm install
npx expo start
```

Scan the QR code with the Expo Go app or run in a simulator.

## Configuration

Set the API URL via environment variable:

```bash
EXPO_PUBLIC_API_URL=https://api.anote.ai npx expo start
```
