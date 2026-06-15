module.exports = {
  packagerConfig: {
    asar: true,
    name: "Anote AI",
    icon: "./assets/icon",
    extraResource: ["./backend-dist"],
  },
  rebuildConfig: {},
  makers: [
    { name: "@electron-forge/maker-squirrel", config: { name: "anote_ai" } },
    { name: "@electron-forge/maker-dmg", config: { format: "ULFO" } },
    { name: "@electron-forge/maker-deb", config: {} },
  ],
};
