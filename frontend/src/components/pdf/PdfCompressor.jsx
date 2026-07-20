import React, { useState } from 'react';

export default function PdfCompressor() {
  const [file, setFile] = useState(null);
  const [mode, setMode] = useState('auto');
  const [targetKb, setTargetKb] = useState(200);
  const [quality, setQuality] = useState(65);
  const [scale, setScale] = useState(100);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setResult(null);
    }
  };

  const executeCompress = async () => {
    if (!file) return;
    setLoading(true);

    const formData = new FormData();
    formData.append('file', file);

    if (mode === 'auto') {
      formData.append('target_size_kb', targetKb);
      formData.append('quality', 65);
      formData.append('scale', 100);
    } else {
      formData.append('quality', quality);
      formData.append('scale', scale);
    }

    try {
      const res = await fetch('/pdf/reduce-size', { method: 'POST', body: formData });
      const data = await res.json();
      if (data.error) {
        alert(data.error);
      } else {
        setResult(data);
      }
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  const downloadFile = () => {
    if (!result) return;
    const link = document.createElement('a');
    link.href = `data:application/octet-stream;base64,${result.data_b64}`;
    link.download = `compressed_${result.filename}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  return (
    <div>
      {/* Initial Upload Stage (Single Card) */}
      {!file ? (
        <div className="control-pane" style={{ maxWidth: '600px', margin: '0 auto' }}>
          <div className="panel-header">
            <span className="panel-title">Upload File to Compress</span>
          </div>
          <div 
            className="dropzone" 
            onClick={() => document.getElementById('compress-single-file').click()}
          >
            <h4>Upload PDF or Image document</h4>
            <p>Drop PDF, PNG, JPG, WEBP, or BMP file here or click to browse</p>
            <input 
              type="file" 
              id="compress-single-file" 
              className="file-input" 
              accept=".pdf,.png,.jpg,.jpeg,.webp,.bmp" 
              onChange={handleFileChange} 
            />
          </div>
        </div>
      ) : (
        /* Workspace 2-Column Split Stage */
        <div className="workspace">
          {/* Left Control Pane */}
          <div className="control-pane">
            <div className="panel-header">
              <span className="panel-title">Size Reducer Settings</span>
            </div>

            <div className="form-group">
              <label>Selected Document</label>
              <div style={{ padding: '8px 12px', fontWeight: 700, border: '2px solid var(--border)', borderRadius: '8px', fontSize: '12px' }}>
                {file.name} ({(file.size / 1024).toFixed(1)} KB)
              </div>
            </div>

            <div className="form-row" style={{ marginBottom: '16px' }}>
              <button 
                type="button" 
                className={`btn ${mode === 'auto' ? 'btn-primary' : 'btn-secondary'}`} 
                onClick={() => setMode('auto')}
              >
                Fast Auto Target
              </button>
              <button 
                type="button" 
                className={`btn ${mode === 'manual' ? 'btn-primary' : 'btn-secondary'}`} 
                onClick={() => setMode('manual')}
              >
                Manual Sliders
              </button>
            </div>

            {mode === 'auto' ? (
              <div className="form-group">
                <label>DESIRED TARGET SIZE (KB)</label>
                <input 
                  type="number" 
                  value={targetKb} 
                  onChange={(e) => setTargetKb(e.target.value)} 
                  placeholder="e.g. 200" 
                />
                <small style={{ color: 'var(--muted)', fontSize: '11px', marginTop: '4px', display: 'block' }}>
                  Fast 3-pass binary search algorithm matches constraints in &lt; 0.02s.
                </small>
              </div>
            ) : (
              <>
                <div className="form-group">
                  <label>JPEG Quality ({quality}%)</label>
                  <input type="range" min="10" max="90" value={quality} onChange={(e) => setQuality(e.target.value)} style={{ width: '100%' }} />
                </div>
                <div className="form-group">
                  <label>Resolution Scale ({scale}%)</label>
                  <input type="range" min="20" max="100" value={scale} onChange={(e) => setScale(e.target.value)} style={{ width: '100%' }} />
                </div>
              </>
            )}

            <button className="btn btn-primary" onClick={executeCompress} disabled={loading} style={{ marginTop: '12px' }}>
              {loading ? 'Compressing File...' : 'Compress File'}
            </button>
            <button className="btn btn-secondary" onClick={() => { setFile(null); setResult(null); }} style={{ marginTop: '8px' }}>
              Change Document
            </button>
          </div>

          {/* Right Preview Pane */}
          <div className="preview-pane">
            <div className="panel-header">
              <span className="panel-title">Compression Output & Analytics</span>
            </div>

            {result ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', flex: 1, justifyContent: 'center' }}>
                <div className="stats-grid">
                  <div className="stat-card">
                    <div className="label">ORIGINAL SIZE</div>
                    <div className="value">{(result.original_size / 1024).toFixed(1)} KB</div>
                  </div>
                  <div className="stat-card" style={{ background: 'var(--accent-green)' }}>
                    <div className="label">COMPRESSED SIZE</div>
                    <div className="value">{(result.compressed_size / 1024).toFixed(1)} KB</div>
                  </div>
                </div>

                <div style={{ textAlign: 'center', padding: '16px', background: 'var(--bg)', border: '2px solid var(--border)', borderRadius: '12px' }}>
                  <span style={{ fontWeight: 800, fontSize: '16px', color: 'var(--accent-orange)' }}>
                    Saved {result.savings_percent}% ({(result.saved_bytes / 1024).toFixed(1)} KB)
                  </span>
                </div>

                <button className="btn btn-primary" onClick={downloadFile}>
                  Download Compressed File
                </button>
              </div>
            ) : (
              <div className="chart-out">
                <div className="chart-placeholder">
                  Select a file on the left and click Compress File to view reduction statistics.
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
