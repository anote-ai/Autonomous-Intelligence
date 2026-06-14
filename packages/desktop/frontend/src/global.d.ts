interface Window {
  electronAPI?: {
    getBackendUrl: () => Promise<string>;
    getAppVersion: () => Promise<string>;
    platform: string;
  };
}
