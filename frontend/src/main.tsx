import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles/global.css";
import App from "./App.tsx";
import {
  AdminFeedbackRoute,
  ReviewRoute,
  VisualQaRoute,
} from "./InternalRoutes.tsx";

export function resolveRootView(pathname = window.location.pathname) {
  const normalizedPath = pathname.replace(/\/+$/, "") || "/";

  if (normalizedPath === "/review") {
    return <ReviewRoute />;
  }

  if (normalizedPath === "/visual-qa") {
    return <VisualQaRoute />;
  }

  if (normalizedPath === "/admin/feedback") {
    return <AdminFeedbackRoute />;
  }

  return <App />;
}

const rootElement = document.getElementById("root");

if (rootElement) {
  createRoot(rootElement).render(<StrictMode>{resolveRootView()}</StrictMode>);
}
