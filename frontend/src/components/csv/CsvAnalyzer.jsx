import React, { useState } from 'react';

export default function CsvAnalyzer() {
  const [file, setFile] = useState(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleUpload = async (e) => {
    const selected = e.target.files?.[0];
    if (!selected) return;

    setFile(selected);
    setLoading(true);

    const formData = new FormData();
    formData.append('file', selected);

    try {
      const res = await fetch('/upload_csv', { method: 'POST', body: formData });
      const data = await res.json();
      if (data.error) {
        alert(data.error);
        setFile(null);
      } else {
        setInfo(data);
      }
    } catch (err) {
      alert('Upload failed: ' + err.message);
      setFile(null);
    } finally {
      setLoading(false);
    }
  };

  const handleClean = async (strategy) => {
    setLoading(true);
    try {
      const res = await fetch('/clean_data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fill_missing: strategy, remove_duplicates: true }),
      });
      const data = await res.json();
      if (data.error) {
        alert(data.error);
      } else {
        setInfo(prev => ({ ...prev, ...data }));
      }
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {/* Initial Stage: Standalone Dropzone (Matching Original index.html) */}
      {!file || !info ? (
        <div 
          className="dropzone" 
          onClick={() => document.getElementById('csv-single-input').click()}
          style={{ maxWidth: '800px', margin: '0 auto' }}
        >
          <h4>Drop your CSV file here</h4>
          <p>or click to browse local files (up to 4MB supported)</p>
          <input 
            type="file" 
            id="csv-single-input" 
            className="file-input" 
            accept=".csv" 
            onChange={handleUpload} 
          />
        </div>
      ) : (
        /* Workspace 2-Column Split Stage */
        <div className="workspace">
          <div className="control-pane">
            <div className="panel-header">
              <span className="panel-title">Data Cleaning Controls</span>
            </div>

            <div className="form-group">
              <label>Selected Dataset</label>
              <div style={{ padding: '8px 12px', fontWeight: 700, border: '2px solid var(--border)', borderRadius: '8px', fontSize: '12px' }}>
                {file.name} ({(file.size / 1024).toFixed(1)} KB)
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '12px' }}>
              <button className="btn btn-secondary" onClick={() => handleClean('drop')} disabled={loading}>
                Drop Missing Rows
              </button>
              <button className="btn btn-secondary" onClick={() => handleClean('mean')} disabled={loading}>
                Fill Missing with Mean
              </button>
              <button className="btn btn-secondary" onClick={() => handleClean('mode')} disabled={loading}>
                Fill Missing with Mode
              </button>
            </div>

            <a href="/download_cleaned" target="_blank" rel="noreferrer" style={{ textDecoration: 'none', display: 'block', marginTop: '16px' }}>
              <button className="btn btn-primary">Download Cleaned CSV</button>
            </a>
            
            <button className="btn btn-secondary" onClick={() => { setFile(null); setInfo(null); }} style={{ marginTop: '8px' }}>
              Upload New CSV
            </button>
          </div>

          <div className="preview-pane">
            <div className="panel-header">
              <span className="panel-title">Data Profiling & Table Preview</span>
            </div>

            <div className="stats-grid">
              <div className="stat-card">
                <div className="label">TOTAL ROWS</div>
                <div className="value">{info.rows}</div>
              </div>
              <div className="stat-card">
                <div className="label">TOTAL COLUMNS</div>
                <div className="value">{info.columns}</div>
              </div>
              <div className="stat-card">
                <div className="label">DUPLICATES</div>
                <div className="value">{info.duplicates}</div>
              </div>
            </div>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    {info.column_names?.map((col) => (
                      <th key={col}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {info.preview?.map((row, idx) => (
                    <tr key={idx}>
                      {info.column_names?.map((col) => (
                        <td key={col}>{row[col]?.toString() ?? ''}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
