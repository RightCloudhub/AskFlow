/** Persisted history is the source of truth, including replies from other API workers. */
export const MESSAGE_SYNC_INTERVAL_MS = 3_000;

export const messageSyncOptions = {
  refetchInterval: MESSAGE_SYNC_INTERVAL_MS,
  refetchIntervalInBackground: false,
  refetchOnWindowFocus: true,
  refetchOnReconnect: true,
};
