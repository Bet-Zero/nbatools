import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles/global.css";
import App from "./App.tsx";
import ReviewPage from "./ReviewPage.tsx";
import VisualQaPage from "./VisualQaPage.tsx";

export function resolveRootView(pathname = window.location.pathname) {
  const normalizedPath = pathname.replace(/\/+$/, "") || "/";

  if (normalizedPath === "/review") return <ReviewPage />;
  if (normalizedPath === "/visual-qa") return <VisualQaPage />;
  return <App />;
}

const rootElement = document.getElementById("root");

if (rootElement) {
  createRoot(rootElement).render(<StrictMode>{resolveRootView()}</StrictMode>);
}
