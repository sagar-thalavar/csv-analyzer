import React, { useState, useEffect, useRef } from 'react';
import * as pdfjsLib from 'pdfjs-dist';

pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;

export default function PdfOrganizer({ initialSubTool = 'pdf_merge' }) {
  const [op, setOp] = useState(initialSubTool);
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [ranges, setRanges] = useState('1-2');
  const [selectedPages, setSelectedPages] = useState('');
  const [angle, setAngle] = useState(90);
  const [style, setStyle] = useState('bottom_right');
  const [crop, setCrop] = useState({ left: 10, right: 10, top: 10, bottom: 10 });
  const [pdfDoc, setPdfDoc] = useState(null);
  const [pageCount, setPageCount] = useState(0);

  const containerRef = useRef(null);

  const handleFileChange = async (e) => {
    if (e.target.files && e.target.files.length > 0) {
      const selected = Array.from(e.target.files);
      setFiles(selected);

      if (op !== 'pdf_merge' && selected[0]) {
        try {
          const ab = await selected[0].arrayBuffer();
          const doc = await pdfjsLib.getDocument({ data: ab }).promise;
          setPdfDoc(doc);
          setPageCount(doc.numPages);
        } catch (err) {
          console.error('Failed to load PDF preview:', err);
        }
      } else {
        setPdfDoc(null);
        setPageCount(0);
      }
    }
  };

  // Render PDF.js pages inside previewer
  useEffect(() => {
    if (!pdfDoc || !containerRef.current || op === 'pdf_merge') return;

    const renderPages = async () => {
      const wrap = containerRef.current;
      wrap.innerHTML = '';

      for (let p = 1; p <= pdfDoc.numPages; p++) {
        const page = await pdfDoc.getPage(p);
        const unscaledVp = page.getViewport({ scale: 1.0 });
        const targetWidth = Math.min(wrap.clientWidth - 40 || 460, 500);
        const scale = targetWidth / unscaledVp.width;
        const viewport = page.getViewport({ scale });

        const pageDiv = document.createElement('div');
        pageDiv.className = 'pdf-page-container';
        pageDiv.style.position = 'relative';
        pageDiv.style.width = '100%';
        pageDiv.style.maxWidth = `${targetWidth}px`;
        pageDiv.style.minHeight = `${Math.round(viewport.height)}px`;
        pageDiv.style.background = '#fff';
        pageDiv.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)';

        const canvas = document.createElement('canvas');
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        canvas.style.width = '100%';
        canvas.style.height = 'auto';

        const ctx = canvas.getContext('2d');
        await page.render({ canvasContext: ctx, viewport }).promise;

        pageDiv.appendChild(canvas);
        wrap.appendChild(pageDiv);
      }
    };

    renderPages();
  }, [pdfDoc, op]);

  const executeAction = async () => {
    if (files.length === 0) return;
    setLoading(true);
    const formData = new FormData();

    try {
      let endpoint = '';
      let filename = 'result.pdf';

      if (op === 'pdf_merge') {
        endpoint = '/pdf/merge';
        files.forEach((f) => formData.append('files', f));
        filename = 'merged.pdf';
      } else {
        formData.append('file', files[0]);

        if (op === 'pdf_split') {
          endpoint = '/pdf/split';
          const parsed = ranges.split(',').map(r => {
            const p = r.trim().split('-').map(Number);
            return p.length === 2 ? p : [p[0], p[0]];
          });
          formData.append('ranges', JSON.stringify(parsed));
          filename = 'split.pdf';
        } else if (op === 'pdf_delete') {
          endpoint = '/pdf/delete';
          const pList = selectedPages.split(',').map(p => parseInt(p.trim())).filter(Boolean);
          formData.append('pages', JSON.stringify(pList));
          filename = 'pages_deleted.pdf';
        } else if (op === 'pdf_rotate') {
          endpoint = '/pdf/rotate';
          const pList = selectedPages ? selectedPages.split(',').map(p => parseInt(p.trim())).filter(Boolean) : [];
          formData.append('pages', JSON.stringify(pList));
          formData.append('angle', angle);
          filename = 'rotated.pdf';
        } else if (op === 'pdf_num') {
          endpoint = '/pdf/numbering';
          formData.append('style', style);
          filename = 'numbered.pdf';
        } else if (op === 'pdf_crop') {
          endpoint = '/pdf/crop';
          formData.append('pages', JSON.stringify([]));
          formData.append('left', crop.left);
          formData.append('right', crop.right);
          formData.append('top', crop.top);
          formData.append('bottom', crop.bottom);
          filename = 'cropped.pdf';
        }
      }

      const res = await fetch(endpoint, { method: 'POST', body: formData });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || 'Action failed');
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getToolTitle = () => {
    switch (op) {
      case 'pdf_merge': return 'PDF Merger Panel';
      case 'pdf_split': return 'PDF Splitter';
      case 'pdf_delete': return 'Delete Pages';
      case 'pdf_rotate': return 'Rotate Page canvas';
      case 'pdf_crop': return 'Crop Margins';
      case 'pdf_num': return 'Page Stamp Numbers';
      default: return 'PDF Page Organizer';
    }
  };

  return (
    <div className="workspace">
      {/* Control Pane */}
      <div className="control-pane">
        <div className="form-group">
          <label>SELECT OPERATION</label>
          <select value={op} onChange={(e) => { setOp(e.target.value); setPdfDoc(null); }}>
            <option value="pdf_merge">Merge PDF Files</option>
            <option value="pdf_split">Split PDF</option>
            <option value="pdf_rotate">Rotate Page canvas</option>
            <option value="pdf_delete">Delete Pages</option>
            <option value="pdf_crop">Crop Margins</option>
            <option value="pdf_num">Page Stamp Numbers</option>
          </select>
        </div>

        <div className="panel-header">
          <span className="panel-title">{getToolTitle()}</span>
        </div>

        {/* Dropzone */}
        <div 
          className="dropzone" 
          onClick={() => document.getElementById('organizer-file-input').click()}
        >
          <h4>Upload PDF document{op === 'pdf_merge' ? 's' : ''}</h4>
          <p>{files.length > 0 ? `${files.length} file(s) selected` : op === 'pdf_merge' ? 'Drop files here or click to browse (Select multiple)' : 'Drop file here or click to browse (up to 4MB supported)'}</p>
          <input 
            type="file" 
            id="organizer-file-input" 
            className="file-input" 
            accept=".pdf" 
            multiple={op === 'pdf_merge'} 
            onChange={handleFileChange}
          />
        </div>

        {files.length > 0 && (
          <div className="form-group">
            <label>Selected Document(s)</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {files.map((f, i) => (
                <span key={i} style={{ padding: '6px 12px', fontWeight: 700, border: '2px solid var(--border)', borderRadius: '8px', display: 'inline-block', fontSize: '12px' }}>
                  {f.name} ({(f.size / 1024).toFixed(1)} KB)
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Dynamic Controls */}
        {op === 'pdf_split' && (
          <div className="form-group">
            <label>Page Ranges (e.g. 1-2, 3-5)</label>
            <input type="text" value={ranges} onChange={(e) => setRanges(e.target.value)} />
          </div>
        )}

        {op === 'pdf_rotate' && (
          <>
            <div className="form-group">
              <label>Rotation Angle</label>
              <select value={angle} onChange={(e) => setAngle(Number(e.target.value))}>
                <option value={90}>90° Clockwise</option>
                <option value={180}>180° Flip</option>
                <option value={270}>270° Counter-Clockwise</option>
              </select>
            </div>
            <div className="form-group">
              <label>Target Pages (e.g. 1, 3 or leave blank for all)</label>
              <input type="text" value={selectedPages} onChange={(e) => setSelectedPages(e.target.value)} placeholder="All pages" />
            </div>
          </>
        )}

        {op === 'pdf_delete' && (
          <div className="form-group">
            <label>Pages to Delete (e.g. 2, 4)</label>
            <input type="text" value={selectedPages} onChange={(e) => setSelectedPages(e.target.value)} />
          </div>
        )}

        {op === 'pdf_num' && (
          <div className="form-group">
            <label>Placement Style</label>
            <select value={style} onChange={(e) => setStyle(e.target.value)}>
              <option value="bottom_right">Bottom Right</option>
              <option value="bottom_center">Bottom Center</option>
              <option value="top_right">Top Right</option>
            </select>
          </div>
        )}

        {files.length > 0 && (
          <button className="btn btn-primary" onClick={executeAction} disabled={loading} style={{ marginTop: '12px' }}>
            {loading ? 'Processing...' : op === 'pdf_merge' ? 'Merge Documents' : 'Apply Operation & Download'}
          </button>
        )}
      </div>

      {/* Preview Pane */}
      <div className="preview-pane">
        <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="panel-title">{op === 'pdf_merge' ? 'File order directory' : 'Visual Workspace Preview'}</span>
          {pageCount > 0 && op !== 'pdf_merge' && (
            <span style={{ fontWeight: 800, fontFamily: 'var(--font-mono)', fontSize: '12px', background: 'var(--bg)', border: '2px solid var(--border)', borderRadius: '8px', padding: '4px 8px' }}>
              Page 1 of {pageCount}
            </span>
          )}
        </div>
        
        {op === 'pdf_merge' ? (
          <div>
            <p className="text-muted" style={{ marginBottom: '10px', fontSize: '12px' }}>
              Drag and drop elements to rearrange the merge order.
            </p>
            {files.length > 0 ? (
              <div className="order-list">
                {files.map((f, idx) => (
                  <div key={idx} className="order-item">
                    <span>{idx + 1}. {f.name}</span>
                    <span className="handle">☰</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="chart-placeholder">No files loaded yet.</div>
            )}
          </div>
        ) : pdfDoc ? (
          <div className="pdf-render-scroll-wrap" ref={containerRef} style={{ flex: 1 }} />
        ) : (
          <div className="chart-out">
            <div className="chart-placeholder">
              Upload a PDF file to begin operations. All manipulations run statelessly in memory.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
