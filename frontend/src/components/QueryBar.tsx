import { forwardRef, type FormEvent, type KeyboardEvent } from "react";
import { Button, IconButton } from "../design-system";
import styles from "./QueryBar.module.css";

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (query: string) => void;
  onHistoryPrevious?: () => boolean;
  onHistoryNext?: () => boolean;
  disabled: boolean;
}

const QueryBar = forwardRef<HTMLInputElement, Props>(function QueryBar(
  {
    value,
    onChange,
    onSubmit,
    onHistoryPrevious,
    onHistoryNext,
    disabled,
  },
  ref,
) {
  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const q = value.trim();
    if (q) onSubmit(q);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.nativeEvent.isComposing) return;
    if (e.metaKey || e.ctrlKey || e.altKey || e.shiftKey) return;

    if (e.key === "Escape" && value) {
      e.preventDefault();
      onChange("");
      return;
    }

    if (e.currentTarget.selectionStart !== e.currentTarget.selectionEnd) {
      return;
    }

    if (e.key === "ArrowUp" && onHistoryPrevious?.()) {
      e.preventDefault();
      return;
    }

    if (e.key === "ArrowDown" && onHistoryNext?.()) {
      e.preventDefault();
    }
  }

  return (
    <form className={styles.queryBar} onSubmit={handleSubmit}>
      <div className={styles.queryIntro}>
        <div className={styles.eyebrow}>Ask anything</div>
        <label className={styles.label} htmlFor="nba-query-input">
          Search NBA performance
        </label>
      </div>
      <div className={styles.inputWrapper}>
        <input
          id="nba-query-input"
          ref={ref}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
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
        className={styles.submitButton}
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
