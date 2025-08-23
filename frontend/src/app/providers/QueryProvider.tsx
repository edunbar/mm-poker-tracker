import { QueryClient, QueryClientProvider } from "react-query";
import React from "react";

const client = new QueryClient({
  defaultOptions: {
    queries: { refetchOnWindowFocus: false, retry: 1 },
    mutations: { retry: 0 },
  },
});

export const QueryProvider: React.FC<React.PropsWithChildren<{}>> = ({
  children,
}) => {
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
};
