import React from 'react';

export default function Navbar({ onGoHome }) {
  return (
    <nav className="navbar">
      <div className="navbar-logo" onClick={onGoHome}>
        <h1>Files Sandbox</h1>
        <span>FILES.SAGARTHALAVAR.IN</span>
      </div>
      <a href="https://sagarthalavar.in" target="_blank" rel="noreferrer" className="navbar-cta">
        Back to Portfolio
      </a>
    </nav>
  );
}
