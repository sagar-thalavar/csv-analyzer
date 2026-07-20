import React, { useState, useRef, useEffect } from 'react';

export default function PdfSecurity({ initialTool = 'pdf_sign' }) {
  const [op, setOp] = useState(initialTool);
  const [file, setFile] = useState(null);
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  
  // Visual Signer state
  const [sigMode, setSigMode] = useState('draw'); // 'draw', 'type', 'upload', 'camera'
  const [penColor, setPenColor] = useState('#1a1a24');
  const [typedText, setTypedText] = useState('Sagar Thalavar');
  const [sigImage, setSigImage] = useState(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [pageNum, setPageNum] = useState(1);
  const [coords, setCoords] = useState({ x: 100, y: 100, width: 150, height: 80 });

  const canvasRef = useRef(null);

  useEffect(() => {
    if (op === 'pdf_sign' && sigMode === 'draw' && canvasRef.current) {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      ctx.lineWidth = 2.5;
      ctx.lineCap = 'round';
      ctx.strokeStyle = penColor;
    }
  }, [op, sigMode, penColor]);

  const startDrawing = (e) => {
    setIsDrawing(true);
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    ctx.beginPath();
    ctx.moveTo(e.clientX - rect.left, e.clientY - rect.top);
  };

  const draw = (e) => {
    if (!isDrawing) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    ctx.lineTo(e.clientX - rect.left, e.clientY - rect.top);
    ctx.stroke();
  };

  const stopDrawing = () => {
    setIsDrawing(false);
  };

  const clearCanvas = () => {
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  };

  const handleImageUpload = (e) => {
    if (e.target.files && e.target.files[0]) {
      const reader = new FileReader();
      reader.onload = (ev) => setSigImage(ev.target.result);
      reader.readAsDataURL(e.target.files[0]);
    }
  };

  const executeSecurityAction = async () => {
    if (!file) {
      alert('Please upload a PDF document first.');
      return;
    }
    setLoading(true);

    try {
      if (op === 'pdf_sign') {
        // Prepare Signature Blob
        let sigBlob = null;
        if (sigMode === 'draw') {
          sigBlob = await new Promise((res) => canvasRef.current.toBlob(res, 'image/png'));
        } else if (sigMode === 'type') {
          const off = document.createElement('canvas');
          off.width = 300;
          off.height = 120;
          const ctx = off.getContext('2d');
          ctx.font = '42px Caveat, cursive';
          ctx.fillStyle = penColor;
          ctx.fillText(typedText, 20, 70);
          sigBlob = await new Promise((res) => off.toBlob(res, 'image/png'));
        } else if (sigImage) {
          const r = await fetch(sigImage);
          sigBlob = await r.blob();
        }

        if (!sigBlob) {
          alert('Please create or upload a signature first.');
          setLoading(false);
          return;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('signature', sigBlob, 'signature.png');
        formData.append('page', pageNum);
        formData.append('x', coords.x);
        formData.append('y', coords.y);
        formData.append('width', coords.width);
        formData.append('height', coords.height);

        const res = await fetch('/pdf/sign', { method: 'POST', body: formData });
        if (!res.ok) throw new Error('Signing failed');
        const blob = await res.blob();
        downloadBlob(blob, 'signed.pdf');
      } else {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('action', op === 'pdf_encrypt' ? 'encrypt' : 'decrypt');
        formData.append('password', password);

        const res = await fetch('/pdf/security', { method: 'POST', body: formData });
        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.error || 'Action failed');
        }
        const blob = await res.blob();
        downloadBlob(blob, op === 'pdf_encrypt' ? 'secured.pdf' : 'unlocked.pdf');
      }
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  const downloadBlob = (blob, filename) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="workspace">
      {/* Control Pane */}
      <div className="control-pane">
        <div className="form-group">
          <label>SELECT OPERATION</label>
          <select value={op} onChange={(e) => setOp(e.target.value)}>
            <option value="pdf_sign">Visual Sign PDF</option>
            <option value="pdf_encrypt">Password Protect</option>
            <option value="pdf_decrypt">Remove Security</option>
          </select>
        </div>

        <div className="panel-header">
          <span className="panel-title">
            {op === 'pdf_sign' ? 'Visual Sign PDF' : op === 'pdf_encrypt' ? 'Password Protect' : 'Remove Security'}
          </span>
        </div>

        {/* File Dropzone */}
        <div 
          className="dropzone" 
          onClick={() => document.getElementById('security-file-input').click()}
        >
          <h4>Upload PDF document</h4>
          <p>{file ? `${file.name} (${(file.size / 1024).toFixed(1)} KB)` : 'Drop file here or click to browse (up to 4MB supported)'}</p>
          <input 
            type="file" 
            id="security-file-input" 
            className="file-input" 
            accept=".pdf" 
            onChange={(e) => setFile(e.target.files[0])} 
          />
        </div>

        {/* Visual Signer Specific Controls */}
        {op === 'pdf_sign' && (
          <div style={{ marginTop: '16px' }}>
            <div className="form-group">
              <label>Signature Type</label>
              <select value={sigMode} onChange={(e) => setSigMode(e.target.value)}>
                <option value="draw">Draw Ink</option>
                <option value="type">Type Handwriting</option>
                <option value="upload">Upload PNG Graphic</option>
              </select>
            </div>

            {sigMode === 'draw' && (
              <div className="canvas-container">
                <canvas 
                  ref={canvasRef} 
                  id="signature-pad" 
                  width={300} 
                  height={150} 
                  onMouseDown={startDrawing}
                  onMouseMove={draw}
                  onMouseUp={stopDrawing}
                  onMouseLeave={stopDrawing}
                />
                <div className="canvas-tools" style={{ padding: '8px' }}>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    {['#1a1a24', '#1d4ed8', '#b91c1c', '#047857'].map((c) => (
                      <div 
                        key={c} 
                        className={`color-dot ${penColor === c ? 'active' : ''}`}
                        style={{ background: c }}
                        onClick={() => setPenColor(c)}
                      />
                    ))}
                  </div>
                  <button type="button" onClick={clearCanvas} style={{ border: 'none', background: 'none', color: 'var(--muted)', fontSize: '11px', fontWeight: '700', cursor: 'pointer' }}>
                    Clear
                  </button>
                </div>
              </div>
            )}

            {sigMode === 'type' && (
              <div className="form-group">
                <label>Handwriting Signature Text</label>
                <input 
                  type="text" 
                  value={typedText} 
                  onChange={(e) => setTypedText(e.target.value)} 
                  style={{ fontFamily: 'Caveat, cursive', fontSize: '22px' }}
                />
              </div>
            )}

            {sigMode === 'upload' && (
              <div className="form-group">
                <label>Upload PNG Graphic</label>
                <input type="file" accept="image/*" onChange={handleImageUpload} />
              </div>
            )}

            <div className="form-row">
              <div className="form-group">
                <label>Page Number</label>
                <input type="number" min="1" value={pageNum} onChange={(e) => setPageNum(Number(e.target.value))} />
              </div>
              <div className="form-group">
                <label>X Position (pt)</label>
                <input type="number" value={coords.x} onChange={(e) => setCoords({...coords, x: Number(e.target.value)})} />
              </div>
            </div>
          </div>
        )}

        {/* Encrypt / Decrypt Controls */}
        {op !== 'pdf_sign' && (
          <div className="form-group" style={{ marginTop: '16px' }}>
            <label>{op === 'pdf_encrypt' ? 'Document Password' : 'Password (leave blank for owner unlock)'}</label>
            <input 
              type="password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              placeholder={op === 'pdf_encrypt' ? 'Set document password' : 'Enter password if required'}
            />
          </div>
        )}

        <button className="btn btn-primary" onClick={executeSecurityAction} disabled={loading} style={{ marginTop: '12px' }}>
          {loading ? 'Processing...' : op === 'pdf_sign' ? 'Sign PDF Document' : op === 'pdf_encrypt' ? 'Encrypt PDF' : 'Unlock PDF Document'}
        </button>
      </div>

      {/* Preview Pane */}
      <div className="preview-pane">
        <div className="panel-header">
          <span className="panel-title">Visual Workspace Preview</span>
        </div>
        <div className="chart-out">
          <div className="chart-placeholder">
            {file ? `Document ${file.name} ready.` : 'Upload a PDF file to begin security operations. All actions run statelessly in memory.'}
          </div>
        </div>
      </div>
    </div>
  );
}
