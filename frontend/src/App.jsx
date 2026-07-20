import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Dashboard from './components/Dashboard';
import PdfCompressor from './components/pdf/PdfCompressor';
import PdfOrganizer from './components/pdf/PdfOrganizer';
import PdfSecurity from './components/pdf/PdfSecurity';
import PdfConversion from './components/pdf/PdfConversion';
import CsvAnalyzer from './components/csv/CsvAnalyzer';

export default function App() {
  const [currentTool, setCurrentTool] = useState('dashboard');

  const syncRouteFromHash = () => {
    const hash = window.location.hash.replace('#', '');
    if (!hash || hash === 'dashboard') {
      setCurrentTool('dashboard');
    } else {
      setCurrentTool(hash);
    }
  };

  useEffect(() => {
    syncRouteFromHash();

    const handlePopState = () => syncRouteFromHash();
    const handleHashChange = () => syncRouteFromHash();

    const handleMouseUp = (e) => {
      if (e.button === 3) {
        e.preventDefault();
        navigateTool('dashboard');
      }
    };

    window.addEventListener('popstate', handlePopState);
    window.addEventListener('hashchange', handleHashChange);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('popstate', handlePopState);
      window.removeEventListener('hashchange', handleHashChange);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  const navigateTool = (toolId) => {
    setCurrentTool(toolId);
    if (window.location.hash !== '#' + toolId) {
      window.history.pushState(null, '', '#' + toolId);
    }
  };

  const getToolTitle = () => {
    switch (currentTool) {
      case 'csv_analyzer':
        return { title: 'CSV Analyzer Workspace', sub: 'Upload a local dataset to clean and analyze' };
      case 'pdf_convert_from':
        return { title: 'PDF Conversion Suite', sub: 'Change file formats bidirectional in-memory' };
      case 'pdf_encrypt':
      case 'pdf_decrypt':
      case 'pdf_sign':
        return { title: 'PDF Security Workspace', sub: 'Secure your documents and visual sign credentials' };
      case 'file_size_reducer':
        return { title: 'PDF Page Organizer Workspace', sub: 'Merge, split, rotate, crop, and arrange pages' };
      case 'pdf_merge':
      default:
        if (currentTool === 'dashboard') {
          return { title: 'Platform Dashboard', sub: 'Select a utility module to get started' };
        }
        return { title: 'PDF Page Organizer Workspace', sub: 'Merge, split, rotate, crop, and arrange pages' };
    }
  };

  const { title, sub } = getToolTitle();

  return (
    <div className="shell">
      <Navbar onGoHome={() => navigateTool('dashboard')} />

      <main className="main">
        <header className="header-title" id="main-header-row">
          {currentTool !== 'dashboard' && (
            <button className="btn-back" id="btn-header-back" onClick={() => navigateTool('dashboard')}>
              <span style={{ fontWeight: 800, fontSize: '16px' }}>←</span> Back to Home
            </button>
          )}
          <h2 id="current-tool-header">{title}</h2>
          <p id="current-tool-subtitle">{sub}</p>
        </header>

        {currentTool === 'dashboard' && <Dashboard onSelectTool={navigateTool} />}
        {currentTool === 'csv_analyzer' && <CsvAnalyzer />}
        {currentTool === 'pdf_convert_from' && <PdfConversion />}
        {['pdf_encrypt', 'pdf_decrypt', 'pdf_sign'].includes(currentTool) && <PdfSecurity initialTool={currentTool} />}
        {currentTool === 'file_size_reducer' && <PdfCompressor />}
        {['pdf_merge', 'pdf_split', 'pdf_rotate', 'pdf_delete', 'pdf_num', 'pdf_crop'].includes(currentTool) && <PdfOrganizer initialSubTool={currentTool} />}
      </main>
    </div>
  );
}
