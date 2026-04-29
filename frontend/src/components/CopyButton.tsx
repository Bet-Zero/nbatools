import { useCallback, useState } from "react";
import { Button } from "../design-system";
import styles from "./CopyButton.module.css";

interface Props {
  text: string;
  label?: string;
  className?: string;
  variant?: "default" | "share";
}

export default function CopyButton({
  text,
  label = "Copy",
  className = "",
  variant = "default",
}: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Fallback for non-secure contexts
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  }, [text]);

  return (
    <Button
      type="button"
      className={[variant === "share" ? styles.share : "", className]
        .filter(Boolean)
        .join(" ")}
      onClick={handleCopy}
      title={copied ? "Copied!" : label}
      size="sm"
      variant="secondary"
    >
      {copied ? "✓ Copied" : label}
    </Button>
  );
}
