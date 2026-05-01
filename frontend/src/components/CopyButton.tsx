import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "../design-system";
import styles from "./CopyButton.module.css";

interface Props {
  text: string;
  label?: string;
  className?: string;
  variant?: "default" | "share";
}

type CopyStatus = "idle" | "copied" | "failed";

export default function CopyButton({
  text,
  label = "Copy",
  className = "",
  variant = "default",
}: Props) {
  const [status, setStatus] = useState<CopyStatus>("idle");
  const resetTimerRef = useRef<number | null>(null);

  const clearResetTimer = useCallback(() => {
    if (resetTimerRef.current !== null) {
      window.clearTimeout(resetTimerRef.current);
      resetTimerRef.current = null;
    }
  }, []);

  const scheduleReset = useCallback(() => {
    clearResetTimer();
    resetTimerRef.current = window.setTimeout(() => {
      setStatus("idle");
      resetTimerRef.current = null;
    }, 1500);
  }, [clearResetTimer]);

  useEffect(() => clearResetTimer, [clearResetTimer]);

  const copyWithFallback = useCallback((): boolean => {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    textarea.setAttribute("readonly", "");
    document.body.appendChild(textarea);
    textarea.select();

    try {
      return document.execCommand("copy");
    } catch {
      return false;
    } finally {
      document.body.removeChild(textarea);
    }
  }, [text]);

  const handleCopy = useCallback(async () => {
    clearResetTimer();
    try {
      if (!navigator.clipboard?.writeText) {
        throw new Error("Clipboard API unavailable");
      }
      await navigator.clipboard.writeText(text);
      setStatus("copied");
    } catch {
      setStatus(copyWithFallback() ? "copied" : "failed");
    }
    scheduleReset();
  }, [clearResetTimer, copyWithFallback, scheduleReset, text]);

  const copied = status === "copied";
  const failed = status === "failed";
  const statusMessage = copied
    ? `${label} copied to clipboard.`
    : failed
      ? `${label} failed to copy.`
      : "";
  const buttonLabel = copied ? "✓ Copied" : failed ? "Copy Failed" : label;
  const buttonTitle = copied ? "Copied!" : failed ? "Copy failed" : label;

  return (
    <>
      <Button
        type="button"
        className={[
          variant === "share" ? styles.share : "",
          failed ? styles.failed : "",
          className,
        ]
          .filter(Boolean)
          .join(" ")}
        onClick={handleCopy}
        title={buttonTitle}
        size="sm"
        variant="secondary"
      >
        {buttonLabel}
      </Button>
      <span className={styles.feedback} role="status">
        {statusMessage}
      </span>
    </>
  );
}
