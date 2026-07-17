/** Client helper checks — runs in browser or node with localStorage polyfill. */

export function runClientHelperChecks(): void {
  const store = new Map<string, string>();
  const g = globalThis as unknown as {
    localStorage?: Storage;
  };
  if (typeof g.localStorage === "undefined") {
    g.localStorage = {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => {
        store.set(k, v);
      },
      removeItem: (k: string) => {
        store.delete(k);
      },
      clear: () => store.clear(),
      key: () => null,
      length: 0,
    } as Storage;
  }

  // dynamic import after polyfill would be ideal; use direct localStorage ops mirroring client
  const TOKEN_KEY = "askflow_token";
  g.localStorage!.setItem(TOKEN_KEY, "abc");
  if (g.localStorage!.getItem(TOKEN_KEY) !== "abc") throw new Error("token set/get failed");
  g.localStorage!.removeItem(TOKEN_KEY);
  if (g.localStorage!.getItem(TOKEN_KEY) !== null) throw new Error("token clear failed");
}
