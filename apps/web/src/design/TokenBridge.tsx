import { useLayoutEffect } from "react";
import { theme } from "antd";
import { designVariables } from "./css-variables";

/** Portals and custom markup inherit the same ConfigProvider tokens. */
export function TokenBridge() {
  const { token } = theme.useToken();
  useLayoutEffect(() => {
    const root = document.documentElement.style;
    const variables = Object.entries(designVariables(token));
    const previous = variables.map(([key]) => [key, root.getPropertyValue(key)]);
    variables.forEach(([key, value]) => root.setProperty(key, value));
    return () => previous.forEach(([key, value]) => {
      if (value) root.setProperty(key, value);
      else root.removeProperty(key);
    });
  }, [token]);
  return null;
}
