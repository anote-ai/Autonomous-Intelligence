# Anote AI — Mobile (Expo)

## EAS Build / Submit setup (one-time, requires an Expo account)

`eas.json` (build/submit profiles) is checked in, but the project still needs
to be linked to a real Expo/EAS project before `eas build` will work, since
that step requires an interactive login:

```bash
cd packages/mobile
npx eas login
npx eas init        # writes extra.eas.projectId into app.json
npx eas build:configure
```

After `eas init`, commit the resulting `extra.eas.projectId` addition to
`app.json`.

## Building

```bash
npx eas build --platform ios --profile production
npx eas build --platform android --profile production
npx eas submit --platform ios
npx eas submit --platform android
```
