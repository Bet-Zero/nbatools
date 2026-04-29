import { type HTMLAttributes, type ReactNode } from "react";
import styles from "./Badge.module.css";

export type BadgeVariant =
  | "neutral"
  | "accent"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "win"
  | "loss";

export type BadgeSize = "sm" | "md";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: BadgeSize;
  uppercase?: boolean;
  children: ReactNode;
}

function joinClassNames(...classNames: Array<string | false | undefined>) {
  return classNames.filter(Boolean).join(" ");
}

export function Badge({
  variant = "neutral",
  size = "md",
  uppercase = false,
  className,
  children,
  ...props
}: BadgeProps) {
  return (
    <span
      className={joinClassNames(
        styles.badge,
        styles[variant],
        styles[size],
        uppercase && styles.uppercase,
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}
