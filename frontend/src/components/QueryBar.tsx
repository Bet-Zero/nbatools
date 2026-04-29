import { forwardRef, type FormEvent } from "react";
import { Button, IconButton } from "../design-system";
import styles from "./QueryBar.module.css";

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (query: string) => void;
  disabled: boolean;
}

const QueryBar = forwardRef<HTMLInputElement, Props>(function QueryBar(
  { value, onChange, onSubmit, disabled },
  ref,
) {
  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const q = value.trim();
    if (q) onSubmit(q);
  }

  return (
    <form className={styles.queryBar} onSubmit={handleSubmit}>
      <div className={styles.inputWrapper}>
        <input
          ref={ref}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Type an NBA query…"
          autoComplete="off"
          autoFocus
          disabled={disabled}
        />
        {value && !disabled && (
          <IconButton
            type="button"
            className={styles.clearButton}
            onClick={() => onChange("")}
            aria-label="Clear query"
            icon="✕"
            size="sm"
            variant="ghost"
          />
        )}
      </div>
      <Button
        type="submit"
        disabled={disabled || !value.trim()}
        loading={disabled}
        variant="primary"
        size="md"
      >
        {disabled ? "Running…" : "Query"}
      </Button>
    </form>
  );
});

export default QueryBar;
