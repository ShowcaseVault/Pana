import React, { useEffect } from 'react';
import '../styles/dialog.css';

const ConfirmDialog = ({ 
  isOpen, 
  onClose, 
  onConfirm, 
  title = "Confirm Action", 
  message = "Are you sure you want to proceed?", 
  confirmLabel = "Delete",
  cancelLabel = "Cancel",
}) => {
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="dialog" onClick={onClose} role="presentation">
      <div
        className="dialog__panel"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
      >
        <h2 className="dialog__title" id="dialog-title">
          {title}
        </h2>
        <p className="dialog__body">{message}</p>

        <div className="dialog__actions">
          <button type="button" className="dialog__button" onClick={onClose}>
            {cancelLabel}
          </button>
          <button
            type="button"
            className="dialog__button dialog__button--destructive"
            onClick={() => {
              onConfirm();
              onClose();
            }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmDialog;
