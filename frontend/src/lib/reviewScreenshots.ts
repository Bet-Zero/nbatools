import { toPng } from "html-to-image";
import JSZip from "jszip";

const TRANSPARENT_IMAGE_PLACEHOLDER =
  "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==";

export interface ReviewScreenshotTarget {
  element: HTMLElement;
  shapeName: string;
}

export interface ReviewScreenshotProgress {
  current: number;
  total: number;
}

function slugify(value: string): string {
  return (
    value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "shape"
  );
}

function localDateStamp(now = new Date()): string {
  const year = String(now.getFullYear());
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function pngDataUrlToBase64(dataUrl: string): string {
  const marker = "base64,";
  const markerIndex = dataUrl.indexOf(marker);
  if (markerIndex === -1) {
    throw new Error("Screenshot capture did not return a base64 PNG.");
  }
  return dataUrl.slice(markerIndex + marker.length);
}

async function waitForCaptureAssets(targets: ReviewScreenshotTarget[]) {
  await document.fonts?.ready;

  const images = targets.flatMap((target) =>
    Array.from(target.element.querySelectorAll("img")).filter(
      (image) => !image.complete,
    ),
  );
  await Promise.all(
    images.map(
      (image) =>
        new Promise<void>((resolve) => {
          const done = () => {
            window.clearTimeout(timeout);
            resolve();
          };
          const timeout = window.setTimeout(done, 5000);
          image.addEventListener("load", done, { once: true });
          image.addEventListener("error", done, { once: true });
        }),
    ),
  );
}

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export async function downloadReviewScreenshots(
  targets: ReviewScreenshotTarget[],
  onProgress: (progress: ReviewScreenshotProgress) => void,
  now = new Date(),
) {
  if (targets.length === 0) return;

  await waitForCaptureAssets(targets);

  const zip = new JSZip();
  const prefixWidth = Math.max(2, String(targets.length).length);

  for (const [index, target] of targets.entries()) {
    onProgress({ current: index + 1, total: targets.length });
    const dataUrl = await toPng(target.element, {
      cacheBust: true,
      fontEmbedCSS: "",
      imagePlaceholder: TRANSPARENT_IMAGE_PLACEHOLDER,
      onImageErrorHandler: () => undefined,
      pixelRatio: 2,
    });
    const prefix = String(index + 1).padStart(prefixWidth, "0");
    zip.file(
      `${prefix}-${slugify(target.shapeName)}.png`,
      pngDataUrlToBase64(dataUrl),
      { base64: true },
    );
  }

  const blob = await zip.generateAsync({ type: "blob" });
  saveBlob(blob, `review-screenshots-${localDateStamp(now)}.zip`);
}
