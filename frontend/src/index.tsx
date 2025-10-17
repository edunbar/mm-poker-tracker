import { ClerkProvider } from "@clerk/clerk-react";
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./app/App";
import AppErrorBoundary from "./app/errors/AppErrorBoundary";
import { QueryProvider } from "./app/providers/QueryProvider";
import "./index.css";

// Get Clerk publishable key from environment
const clerkPubKey = process.env.REACT_APP_CLERK_PUBLISHABLE_KEY;

if (!clerkPubKey) {
  throw new Error(
    'Missing REACT_APP_CLERK_PUBLISHABLE_KEY environment variable. ' +
    'Please add it to your .env.local file.'
  );
}

const container = document.getElementById("root");
if (!container) throw new Error("Root element #root not found");

const root = createRoot(container);
root.render(
  <React.StrictMode>
    <ClerkProvider
      publishableKey={clerkPubKey}
      appearance={{
        variables: {
          colorPrimary: '#8A2BE2',
          colorBackground: '#1a1a1a',
          colorInputBackground: '#2a2a2a',
          colorInputText: '#FFFFFF',
          colorText: '#FFFFFF',
          colorTextSecondary: '#B0B0B0',
          colorDanger: '#DC2626',
          colorSuccess: '#53d337',
          colorWarning: '#D4B574',
          borderRadius: '0.5rem',
        },
        elements: {
          rootBox: 'mx-auto',
          card: 'bg-[#242424] border border-[#404040] shadow-lg',
          headerTitle: 'text-white',
          headerSubtitle: 'text-[#B0B0B0]',
          socialButtonsBlockButton: 'border-[#404040] hover:bg-[#2a2a2a]',
          formButtonPrimary: 'bg-[#8A2BE2] hover:bg-[#7B27CC] text-white',
          footerActionLink: 'text-[#8A2BE2] hover:text-[#7B27CC]',
          identityPreviewText: 'text-white',
          identityPreviewEditButton: 'text-[#8A2BE2]',
          formFieldLabel: 'text-white',
          formFieldInput: 'bg-[#2a2a2a] border-[#404040] text-white',
          dividerLine: 'bg-[#404040]',
          dividerText: 'text-[#B0B0B0]',
          otpCodeFieldInput: 'bg-[#2a2a2a] border-[#404040] text-white',
        }
      }}
    >
      <AppErrorBoundary>
        <QueryProvider>
          <App />
        </QueryProvider>
      </AppErrorBoundary>
    </ClerkProvider>
  </React.StrictMode>
);
