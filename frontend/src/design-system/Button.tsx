import {
  forwardRef,
  type ButtonHTMLAttributes,
  type ReactNode,
} from "react";
import styles from "./Button.module.css";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md";

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  fullWidth?: boolean;
}

function joinClassNames(...classNames: Array<string | false | undefined>) {
  return classNames.filter(Boolean).join(" ");
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    {
      variant = "secondary",
      size = "md",
      loading = false,
      fullWidth = false,
      className,
      disabled,
      children,
      type = "button",
      ...props
    },
    ref,
  ) {
    return (
      <button
        ref={ref}
        type={type}
        className={joinClassNames(
          styles.button,
          styles[variant],
          styles[size],
          fullWidth && styles.fullWidth,
          loading && styles.loading,
          className,
        )}
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        {...props}
      >
        {loading && <span className={styles.spinner} aria-hidden="true" />}
        <span className={styles.content}>{children}</span>
      </button>
    );
  },
);

export interface IconButtonProps extends Omit<ButtonProps, "children"> {
  "aria-label": string;
  icon: ReactNode;
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  function IconButton({ icon, className, ...props }, ref) {
    return (
      <Button
        ref={ref}
        className={joinClassNames(styles.iconButton, className)}
        {...props}
      >
        <span className={styles.icon} aria-hidden="true">
          {icon}
        </span>
      </Button>
    );
  },
);
