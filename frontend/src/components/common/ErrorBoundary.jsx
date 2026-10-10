import React from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('PERFORMX Uncaught UI Exception:', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    try {
      localStorage.removeItem('performx_profile_display');
      localStorage.removeItem('performx_settings');
    } catch (e) {
      // ignore
    }
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div 
          style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'var(--bg-app, #FAF8F1)',
            color: 'var(--text-primary, #171717)',
            padding: '24px',
            fontFamily: 'var(--font-sans, system-ui, sans-serif)',
          }}
        >
          <div 
            style={{
              maxWidth: '540px',
              width: '100%',
              backgroundColor: 'var(--surface-card, #FFFDF6)',
              border: '1px solid var(--border-subtle, #E6DFCE)',
              borderRadius: '16px',
              padding: '32px',
              boxShadow: '0 8px 30px rgba(0,0,0,0.06)',
              textAlign: 'center',
            }}
          >
            <div 
              style={{
                width: '56px',
                height: '56px',
                borderRadius: '50%',
                backgroundColor: 'rgba(242, 107, 58, 0.12)',
                color: 'var(--primary-orange, #F26B3A)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 20px auto',
              }}
            >
              <AlertTriangle size={28} />
            </div>

            <h1 
              style={{
                fontSize: '1.5rem',
                fontWeight: 700,
                marginBottom: '10px',
                color: 'var(--text-primary, #171717)',
              }}
            >
              Application Encountered an Error
            </h1>

            <p 
              style={{
                fontSize: '0.95rem',
                color: 'var(--text-secondary, #65645F)',
                marginBottom: '24px',
                lineHeight: 1.5,
              }}
            >
              PERFORMX hit an unexpected runtime issue during rendering. Your data and privacy remain safe.
            </p>

            {this.state.error && (
              <div 
                style={{
                  textAlign: 'left',
                  backgroundColor: 'var(--surface-subtle, #F5F1E8)',
                  padding: '12px 16px',
                  borderRadius: '8px',
                  fontSize: '0.82rem',
                  color: 'var(--text-muted, #8E8C85)',
                  marginBottom: '24px',
                  fontFamily: 'monospace',
                  overflowX: 'auto',
                  border: '1px solid var(--border-subtle, #E6DFCE)',
                }}
              >
                {this.state.error.message || String(this.state.error)}
              </div>
            )}

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap' }}>
              <button
                onClick={this.handleReload}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '10px 20px',
                  borderRadius: '8px',
                  border: 'none',
                  backgroundColor: 'var(--primary-orange, #F26B3A)',
                  color: '#FFFFFF',
                  fontWeight: 600,
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                }}
              >
                <RefreshCw size={16} />
                <span>Reload Application</span>
              </button>

              <button
                onClick={this.handleReset}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '10px 20px',
                  borderRadius: '8px',
                  border: '1px solid var(--border-subtle, #E6DFCE)',
                  backgroundColor: 'transparent',
                  color: 'var(--text-primary, #171717)',
                  fontWeight: 600,
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                }}
              >
                <Home size={16} />
                <span>Return to Home</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
