import { useEffect, useRef, type RefObject } from "react";

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(",");

interface UseModalDialogOptions {
  open: boolean;
  dialogRef: RefObject<HTMLElement | null>;
  returnFocusRef?: RefObject<HTMLElement | null>;
  onClose: () => void;
  closeBlocked?: boolean;
}

/**
 * Supplies the keyboard and focus behavior expected of a modal dialog.
 * The caller remains responsible for dialog semantics and visual presentation.
 */
export function useModalDialog({
  open,
  dialogRef,
  returnFocusRef,
  onClose,
  closeBlocked = false,
}: UseModalDialogOptions) {
  const onCloseRef = useRef(onClose);
  const closeBlockedRef = useRef(closeBlocked);

  useEffect(() => {
    onCloseRef.current = onClose;
    closeBlockedRef.current = closeBlocked;
  });

  useEffect(() => {
    if (!open) return;

    const dialog = dialogRef.current;
    if (!dialog) return;
    const activeDialog = dialog;

    const previousFocus =
      returnFocusRef?.current ??
      (document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null);
    const focusable = () =>
      Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
        (element) => element.getAttribute("aria-hidden") !== "true",
      );
    const initialFocus =
      dialog.querySelector<HTMLElement>('[data-dialog-initial-focus="true"]') ??
      focusable()[0] ??
      dialog;

    initialFocus.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        if (closeBlockedRef.current) return;
        event.preventDefault();
        onCloseRef.current();
        return;
      }

      if (event.key !== "Tab") return;

      const elements = focusable();
      if (elements.length === 0) {
        event.preventDefault();
        activeDialog.focus();
        return;
      }

      const first = elements[0];
      const last = elements[elements.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    dialog.addEventListener("keydown", handleKeyDown);
    return () => {
      dialog.removeEventListener("keydown", handleKeyDown);
      if (previousFocus?.isConnected) previousFocus.focus();
    };
  }, [dialogRef, open, returnFocusRef]);
}
