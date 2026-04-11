import { forwardRef, useState, type FormEvent } from "react";

interface Props {
  onSubmit: (query: string) => void;
  disabled: boolean;
}

const QueryBar = forwardRef<HTMLInputElement, Props>(function QueryBar(
  { onSubmit, disabled },
  ref,
) {
  const [value, setValue] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const q = value.trim();
    if (q) onSubmit(q);
  }

  return (
    <form className="query-bar" onSubmit={handleSubmit}>
      <input
        ref={ref}
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onInput={(e) => setValue((e.target as HTMLInputElement).value)}
        placeholder="Type an NBA query…"
        autoComplete="off"
        autoFocus
        disabled={disabled}
      />
      <button type="submit" disabled={disabled || !value.trim()}>
        Query
      </button>
    </form>
  );
});

export default QueryBar;
