/**
 * A confirmation, as a sheet from the bottom of the screen.
 *
 * The web app asks with a centred dialog. On a handset the same question
 * belongs at the bottom, within reach of the thumb that is about to answer
 * it: a dialog centred on a tall screen puts its buttons where the hand is
 * not.
 *
 * Destructive by default, because that is the only thing worth interrupting
 * someone for. The confirm button carries the action's own word -- "Delete",
 * not "OK" -- so the answer is readable without the question.
 *
 * @module components/ConfirmSheet
 */

import { useEffect } from 'react';
import '../styles/confirm-sheet.css';

export default function ConfirmSheet({
  open,
  onCancel,
  onConfirm,
  title,
  message,
  confirmLabel = 'Delete',
  cancelLabel = 'Cancel',
}) {
  // The pane behind the sheet scrolls; locking it stops the question sliding
  // away under the answer.
  useEffect(() => {
    if (!open) return undefined;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="sheet" role="presentation" onClick={onCancel}>
      <div
        className="sheet__panel"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="sheet-title"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 className="sheet__title" id="sheet-title">
          {title}
        </h2>
        <p className="sheet__body">{message}</p>

        <div className="sheet__actions">
          <button
            type="button"
            className="sheet__button sheet__button--destructive"
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
          <button type="button" className="sheet__button" onClick={onCancel}>
            {cancelLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
