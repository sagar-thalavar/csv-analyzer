import React, { useState, useEffect, useRef } from 'react';
import * as pdfjsLib from 'pdfjs-dist';

pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;

export default function PdfConversion() {
  const [direction, setDirection] = useState('pdf_to_other');
  const [targetFormat, setTargetFormat] = useState('word');
  const [imageCodec, setImageCodec] = useState('PNG');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [pdfDoc, setPdfDoc] = useState(null);
  const [pageCount, setPageCount] = useState(0);

  const containerRef = useRef(null);

  const handleFileChange = async (e) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);

      if (direction === 'pdf_to_other' && selectedFile.name.endsWith('.pdf')) {
        try {
          const ab = await selectedFile.arrayBuffer();
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

  // Lazy render PDF.js pages inside canvas previewer
  useEffect(() => {
    if (!pdfDoc || !containerRef.current) return;

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
  }, [pdfDoc]);

  const handleExecute = async () => {
    if (!file) {
      alert('Please upload a document first.');
      return;
    }
    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      if (direction === 'pdf_to_other') {
        formData.append('format', targetFormat === 'images' ? 'images' : targetFormat);
        if (targetFormat === 'images') {
          formData.append('image_format', imageCodec);
        }
        const res = await fetch('/pdf/convert-from', { method: 'POST', body: formData });
        if (!res.ok) throw new Error('Conversion failed');
        const blob = await res.blob();
        const ext = targetFormat === 'word' ? 'docx' : targetFormat === 'excel' ? 'xlsx' : targetFormat === 'text' ? 'txt' : targetFormat === 'html' ? 'html' : 'zip';
        downloadBlob(blob, `extracted.${ext}`);
      } else {
        const ext = file.name.split('.').pop().toLowerCase();
        let srcFormat = 'images';
        if (['doc', 'docx'].includes(ext)) srcFormat = 'docx';
        else if (['xls', 'xlsx'].includes(ext)) srcFormat = 'xlsx';
        else if (ext === 'txt') srcFormat = 'txt';
        
        formData.append('source_format', srcFormat);
        const res = await fetch('/pdf/convert-to', { method: 'POST', body: formData });
        if (!res.ok) throw new Error('Conversion to PDF failed');
        const blob = await res.blob();
        downloadBlob(blob, 'converted.pdf');
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

  const getDetectedFormat = () => {
    if (!file) return 'none';
    const ext = file.name.split('.').pop().toLowerCase();
    if (['xls', 'xlsx'].includes(ext)) return 'XLSX File (excel)';
    if (['doc', 'docx'].includes(ext)) return 'DOCX File (word)';
    if (['jpg', 'jpeg', 'png', 'webp', 'gif'].includes(ext)) return 'Image File (graphics)';
    if (ext === 'txt') return 'TXT File (plaintext)';
    if (ext === 'html') return 'HTML Web Page';
    return `${ext.toUpperCase()} File`;
  };

  return (
    <div className="workspace">
      {/* Control Pane */}
      <div className="control-pane">
        <div className="form-group">
          <label>CONVERSION DIRECTION</label>
          <select value={direction} onChange={(e) => { setDirection(e.target.value); setFile(null); setPdfDoc(null); }}>
            <option value="pdf_to_other">PDF to Other Formats</option>
            <option value="other_to_pdf">Other Formats to PDF</option>
          </select>
        </div>

        <div className="panel-header">
          <span className="panel-title">
            {direction === 'pdf_to_other' ? 'Export PDF Elements' : 'Convert to PDF'}
          </span>
        </div>

        {/* Dropzone */}
        <div className="dropzone" onClick={() => document.getElementById('conv-file-input').click()}>
          <h4>{direction === 'pdf_to_other' ? 'Upload PDF document' : 'Upload source file'}</h4>
          <p>
            {file ? `${file.name} (${(file.size / 1024).toFixed(1)} KB)` : direction === 'pdf_to_other' ? 'Drop file here or click to browse (up to 4MB supported)' : 'Drop Image, Word (docx), Excel (xlsx), HTML, Text, or RTF here'}
          </p>
          <input 
            type="file" 
            id="conv-file-input" 
            className="file-input" 
            accept={direction === 'pdf_to_other' ? '.pdf' : '.jpg,.jpeg,.png,.bmp,.gif,.docx,.xlsx,.html,.txt,.rtf'} 
            onChange={handleFileChange} 
          />
        </div>

        {direction === 'pdf_to_other' ? (
          <>
            <div className="form-group" style={{ marginTop: '16px' }}>
              <label>TARGET EXPORT FORMAT</label>
              <select value={targetFormat} onChange={(e) => setTargetFormat(e.target.value)}>
                <option value="word">Microsoft Word (.docx)</option>
                <option value="excel">Microsoft Excel (.xlsx)</option>
                <option value="images">Render to Image grid (ZIP / PNG)</option>
                <option value="text">Plain Text (.txt)</option>
                <option value="html">HTML Web Page (.html)</option>
              </select>
            </div>

            {targetFormat === 'images' && (
              <div className="form-group">
                <label>IMAGE CODEC</label>
                <select value={imageCodec} onChange={(e) => setImageCodec(e.target.value)}>
                  <option value="PNG">PNG Image</option>
                  <option value="JPEG">JPEG Image</option>
                </select>
              </div>
            )}
          </>
        ) : (
          <div className="form-group" style={{ marginTop: '16px' }}>
            <label>DETECTED SOURCE FORMAT</label>
            <div style={{ padding: '8px 12px', fontWeight: 700, border: '2px solid var(--border)', borderRadius: '8px', display: 'inline-block', fontSize: '12px', background: 'var(--bg)' }}>
              {getDetectedFormat()}
            </div>
          </div>
        )}

        <button className="btn btn-primary" onClick={handleExecute} disabled={loading} style={{ marginTop: '12px' }}>
          {loading ? 'Processing...' : direction === 'pdf_to_other' ? 'Extract Elements' : 'Compile to PDF'}
        </button>
      </div>

      {/* Preview Pane with Live PDF.js Canvas Rendering */}
      <div className="preview-pane">
        <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="panel-title">Visual Workspace Preview</span>
          {pageCount > 0 && (
            <span style={{ fontWeight: 800, fontFamily: 'var(--font-mono)', fontSize: '12px', background: 'var(--bg)', border: '2px solid var(--border)', borderRadius: '8px', padding: '4px 8px' }}>
              Page 1 of {pageCount}
            </span>
          )}
        </div>

        {pdfDoc ? (
          <div className="pdf-render-scroll-wrap" ref={containerRef} style={{ flex: 1 }} />
        ) : (
          <div className="chart-out">
            <div className="chart-placeholder">
              {file ? `Source document ${file.name} ready for conversion.` : 'Upload files on the left to begin rendering previews. All conversions are performed in memory.'}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
