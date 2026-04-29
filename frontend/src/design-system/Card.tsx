import {
  type ElementType,
  type HTMLAttributes,
  type ReactNode,
} from "react";
import styles from "./Card.module.css";

export type CardDepth = "elevated" | "card" | "input";
export type CardPadding = "none" | "sm" | "md" | "lg";
export type CardTone = "neutral" | "danger" | "warning" | "success";

export interface CardProps extends HTMLAttributes<HTMLElement> {
  as?: ElementType;
  depth?: CardDepth;
  padding?: CardPadding;
  tone?: CardTone;
  children: ReactNode;
}

function joinClassNames(...classNames: Array<string | false | undefined>) {
  return classNames.filter(Boolean).join(" ");
}

const DEPTH_CLASS: Record<CardDepth, string> = {
  elevated: styles.depthElevated,
  card: styles.depthCard,
  input: styles.depthInput,
};

const PADDING_CLASS: Record<CardPadding, string> = {
  none: styles.paddingNone,
  sm: styles.paddingSm,
  md: styles.paddingMd,
  lg: styles.paddingLg,
};

const TONE_CLASS: Record<CardTone, string> = {
  neutral: styles.toneNeutral,
  danger: styles.toneDanger,
  warning: styles.toneWarning,
  success: styles.toneSuccess,
};

export function Card({
  as: Component = "div",
  depth = "card",
  padding = "md",
  tone = "neutral",
  className,
  children,
  ...props
}: CardProps) {
  return (
    <Component
      className={joinClassNames(
        styles.card,
        DEPTH_CLASS[depth],
        PADDING_CLASS[padding],
        TONE_CLASS[tone],
        className,
      )}
      {...props}
    >
      {children}
    </Component>
  );
}
