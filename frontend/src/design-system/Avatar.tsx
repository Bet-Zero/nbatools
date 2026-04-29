import { type HTMLAttributes } from "react";
import styles from "./Avatar.module.css";

export type AvatarSize = "sm" | "md" | "lg";

export interface AvatarProps extends HTMLAttributes<HTMLSpanElement> {
  name: string;
  imageUrl?: string | null;
  size?: AvatarSize;
  unavailable?: boolean;
}

function joinClassNames(...classNames: Array<string | false | undefined>) {
  return classNames.filter(Boolean).join(" ");
}

function initials(name: string): string {
  const parts = name
    .replace(/[^\w\s-]/g, " ")
    .split(/\s+/)
    .filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return parts
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
}

export function Avatar({
  name,
  imageUrl = null,
  size = "md",
  unavailable = false,
  className,
  ...props
}: AvatarProps) {
  const showImage = Boolean(imageUrl) && !unavailable;

  return (
    <span
      aria-label={unavailable ? `${name} avatar unavailable` : `${name} avatar`}
      className={joinClassNames(
        styles.avatar,
        styles[size],
        unavailable && styles.unavailable,
        className,
      )}
      {...props}
    >
      {showImage ? (
        <img className={styles.image} src={imageUrl ?? undefined} alt="" />
      ) : (
        <span aria-hidden="true">{initials(name)}</span>
      )}
    </span>
  );
}
