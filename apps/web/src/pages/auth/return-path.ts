const LOCAL_ORIGIN = "https://askflow.invalid";

/** Login continuation is a local product route, never an external redirect. */
export function loginReturnPath(value: string | null, fallback: string) {
  if (!value?.startsWith("/") || value.startsWith("//") || /[\\\u0000-\u001f]/.test(value)) return fallback;
  try {
    const url = new URL(value, LOCAL_ORIGIN);
    const allowed = url.pathname === "/" || /^\/(admin|shop|tickets)(\/|$)/.test(url.pathname);
    return allowed && url.origin === LOCAL_ORIGIN ? url.pathname + url.search + url.hash : fallback;
  } catch { return fallback; }
}
