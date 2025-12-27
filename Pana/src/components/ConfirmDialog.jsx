import React, { useEffect } from 'react';
import { AlertTriangle, X } from 'lucide-react';

const ConfirmDialog = ({ 
  isOpen, 
  onClose, 
  onConfirm, 
  title = "Confirm Action", 
  message = "Are you sure you want to proceed?", 
  confirmLabel = "Delete",
  cancelLabel = "Cancel",
  variant = "danger" 
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
    <div className="confirm-dialog-overlay" onClick={onClose}>
      <div className="confirm-dialog-content" onClick={e => e.stopPropagation()}>
        <button className="confirm-dialog-close" onClick={onClose}>
          <X size={18} />
        </button>
        
        <div className="confirm-dialog-body">
          <div className={`confirm-dialog-icon ${variant}`}>
            <AlertTriangle size={24} />
          </div>
          <div className="confirm-dialog-text">
            <h3 className="confirm-dialog-title">{title}</h3>
            <p className="confirm-dialog-message">{message}</p>
          </div>
        </div>

        <div className="confirm-dialog-footer">
          <button className="confirm-dialog-btn cancel" onClick={onClose}>
            {cancelLabel}
          </button>
          <button 
            className={`confirm-dialog-btn confirm ${variant}`} 
            onClick={() => {
              onConfirm();
              onClose();
            }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>

      <style>{`
        .confirm-dialog-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.4);
          backdrop-filter: blur(4px);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
          animation: fadeIn 0.2s ease-out;
        }

        .confirm-dialog-content {
          background: var(--bg-card);
          width: 100%;
          max-width: 400px;
          border-radius: 12px;
          padding: 1.5rem;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
          position: relative;
          animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }

        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        @keyframes slideUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .confirm-dialog-close {
          position: absolute;
          top: 1rem;
          right: 1rem;
          background: transparent;
          border: none;
          color: var(--text-tertiary);
          cursor: pointer;
          padding: 4px;
          border-radius: 50%;
          transition: all 0.2s ease;
        }

        .confirm-dialog-close:hover {
          background: var(--bg-tertiary);
          color: var(--text-primary);
        }

        .confirm-dialog-body {
          display: flex;
          gap: 1rem;
          margin-bottom: 2rem;
          padding-top: 0.5rem;
        }

        .confirm-dialog-icon {
          width: 48px;
          height: 48px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }

        .confirm-dialog-icon.danger {
          background: #fef2f2;
          color: #ef4444;
        }

        .confirm-dialog-text {
          flex: 1;
        }

        .confirm-dialog-title {
          font-size: 1.125rem;
          font-weight: 600;
          color: var(--text-primary);
          margin: 0 0 0.5rem 0;
        }

        .confirm-dialog-message {
          font-size: 0.875rem;
          color: var(--text-secondary);
          line-height: 1.5;
          margin: 0;
        }

        .confirm-dialog-footer {
          display: flex;
          justify-content: flex-end;
          gap: 0.75rem;
        }

        .confirm-dialog-btn {
          padding: 0.625rem 1.25rem;
          border-radius: 8px;
          font-size: 0.875rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
          border: none;
        }

        .confirm-dialog-btn.cancel {
          background: var(--bg-tertiary);
          color: var(--text-primary);
        }

        .confirm-dialog-btn.cancel:hover {
          background: #e5e7eb;
        }

        .confirm-dialog-btn.confirm.danger {
          background: #ef4444;
          color: white;
        }

        .confirm-dialog-btn.confirm.danger:hover {
          background: #dc2626;
          box-shadow: 0 4px 6px -1px rgba(239, 68, 68, 0.2);
        }
      `}</style>
    </div>
  );
};

export default ConfirmDialog;
