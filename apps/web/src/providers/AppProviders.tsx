import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider, App as AntApp } from "antd";
import zhCN from "antd/locale/zh_CN";
import type { ReactNode } from "react";
import { adminTheme } from "../components/admin";
import { FeaturesProvider } from "../plugins/features";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhCN} theme={adminTheme}>
        <AntApp>
          <FeaturesProvider>{children}</FeaturesProvider>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>
  );
}
