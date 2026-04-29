import { type HTMLAttributes } from "react";
import styles from "./Skeleton.module.css";

export type SkeletonRadius = "sm" | "md" | "lg" | "xl";

export interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  width?: string;
  height?: string;
  radius?: SkeletonRadius;
}

export interface SkeletonTextProps extends HTMLAttributes<HTMLDivElement> {
  lines?: number;
  width?: string | string[];
}

export interface SkeletonBlockProps extends HTMLAttributes<HTMLDivElement> {
  rows?: number;
}

function joinClassNames(...classNames: Array<string | false | undefined>) {
  return classNames.filter(Boolean).join(" ");
}

function lineWidth(width: string | string[], index: number): string {
  if (Array.isArray(width)) return width[index] ?? width[width.length - 1];
  return width;
}

export function Skeleton({
  width = "100%",
  height = "var(--space-4)",
  radius = "md",
  className,
  style,
  ...props
}: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={joinClassNames(styles.skeleton, styles[radius], className)}
      style={{ ...style, width, height }}
      {...props}
    />
  );
}

export function SkeletonText({
  lines = 3,
  width = "100%",
  className,
  ...props
}: SkeletonTextProps) {
  return (
    <div className={joinClassNames(styles.text, className)} {...props}>
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          height="var(--space-3)"
          width={lineWidth(width, index)}
          radius="sm"
        />
      ))}
    </div>
  );
}

export function SkeletonBlock({
  rows = 3,
  className,
  ...props
}: SkeletonBlockProps) {
  return (
    <div className={joinClassNames(styles.block, className)} {...props}>
      <Skeleton height="var(--space-5)" width="38%" />
      <div className={styles.rows}>
        {Array.from({ length: rows }).map((_, index) => (
          <div key={index} className={styles.row}>
            <Skeleton height="var(--space-4)" radius="sm" />
            <Skeleton height="var(--space-4)" radius="sm" />
            <Skeleton height="var(--space-4)" radius="sm" />
          </div>
        ))}
      </div>
    </div>
  );
}
