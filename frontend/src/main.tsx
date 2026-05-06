import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles/global.css";
import App from "./App.tsx";
import ReviewPage from "./ReviewPage.tsx";

const normalizedPath = window.location.pathname.replace(/\/+$/, "") || "/";
const rootView = normalizedPath === "/review" ? <ReviewPage /> : <App />;

createRoot(document.getElementById("root")!).render(
  <StrictMode>{rootView}</StrictMode>,
);
