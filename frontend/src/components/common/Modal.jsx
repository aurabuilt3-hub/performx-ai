import React, { useEffect } from 'react';
import { X } from 'lucide-react';

export default function Modal({ isOpen, onClose, title, subtitle, children, wide = false }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div 
        className={`modal-content ${wide ? 'wide' : ''}`} 
        onClick={(e) => e.stopPropagation()}
      >
        <button 
          className="modal-close-btn" 
          onClick={onClose}
          aria-label="Close dialog"
        >
          <X size={20} />
        </button>

        {(title || subtitle) && (
          <div style={{ marginBottom: 20 }}>
            {title && <h2 style={{ fontSize: '1.35rem', marginBottom: 4 }}>{title}</h2>}
            {subtitle && <p style={{ fontSize: '0.875rem' }}>{subtitle}</p>}
          </div>
        )}

        {children}
      </div>
    </div>
  );
}
