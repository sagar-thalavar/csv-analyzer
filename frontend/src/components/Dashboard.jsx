import React from 'react';

export default function Dashboard({ onSelectTool }) {
  return (
    <div className="tools-grid">
      {/* Yellow Card: CSV & Data Tools */}
      <div className="card-shape card-yellow" onClick={() => onSelectTool('csv_analyzer')}>
        <div>
          <h3 className="card-title">CSV & Data Tools</h3>
          <p className="card-desc">
            Clean databases, inspect row metadata, apply query filters, run mathematical aggregations, render outlier fences, plot custom charts, and export to spreadsheet tables.
          </p>
        </div>
        <span className="card-action">Open workspace ↗</span>
      </div>

      {/* Green Card: PDF Conversion Suite */}
      <div className="card-shape card-green" onClick={() => onSelectTool('pdf_convert_from')}>
        <div>
          <h3 className="card-title">PDF Conversion Suite</h3>
          <p className="card-desc">
            Extract data elements bidirectional. Convert PDF documents to editable Microsoft Word files, Excel spreadsheets, html syntax pages, plaintext strings, or pixel image grids.
          </p>
        </div>
        <span className="card-action">Open workspace ↗</span>
      </div>

      {/* Purple Card: PDF Page Organizer */}
      <div className="card-shape card-purple" onClick={() => onSelectTool('pdf_merge')}>
        <div>
          <h3 className="card-title">PDF Page Organizer</h3>
          <p className="card-desc">
            Organize pages and compile sequences. Merge multiple documents, slice split ranges, delete pages, rotate canvases, crop bounds, and stamp page numbers.
          </p>
        </div>
        <span className="card-action">Open workspace ↗</span>
      </div>

      {/* Coral Card: PDF Security & Sign */}
      <div className="card-shape card-coral" onClick={() => onSelectTool('pdf_encrypt')}>
        <div>
          <h3 className="card-title">PDF Security & Sign</h3>
          <p className="card-desc">
            Lock credentials and sign agreements. Draw signatures, place coordinates tokens visually, add strong password protection, and remove security restrictions.
          </p>
        </div>
        <span className="card-action">Open workspace ↗</span>
      </div>

      {/* Blue Card: File Size Reducer */}
      <div className="card-shape card-blue" onClick={() => onSelectTool('file_size_reducer')}>
        <div>
          <h3 className="card-title">File Size Reducer</h3>
          <p className="card-desc">
            Compress images, PDFs, Word (.docx), PowerPoint (.pptx), Excel (.xlsx), SVG, and general files with intelligent pixel, clarity, dimension, and stream optimization.
          </p>
        </div>
        <span className="card-action">Open workspace ↗</span>
      </div>
    </div>
  );
}
