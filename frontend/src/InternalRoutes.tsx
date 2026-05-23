import { lazy, Suspense } from "react";

const ReviewPage = lazy(() => import("./ReviewPage.tsx"));
const VisualQaPage = lazy(() => import("./VisualQaPage.tsx"));
const AdminFeedbackPage = lazy(() => import("./AdminFeedbackPage.tsx"));

function InternalRouteFallback() {
  return (
    <main aria-busy="true" aria-live="polite">
      Loading...
    </main>
  );
}

export function ReviewRoute() {
  return (
    <Suspense fallback={<InternalRouteFallback />}>
      <ReviewPage />
    </Suspense>
  );
}

export function VisualQaRoute() {
  return (
    <Suspense fallback={<InternalRouteFallback />}>
      <VisualQaPage />
    </Suspense>
  );
}

export function AdminFeedbackRoute() {
  return (
    <Suspense fallback={<InternalRouteFallback />}>
      <AdminFeedbackPage />
    </Suspense>
  );
}
