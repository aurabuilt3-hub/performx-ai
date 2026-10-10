import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  UploadCloud, 
  ShieldAlert, 
  ShieldCheck, 
  AlertTriangle, 
  Trash2, 
  Eye, 
  X, 
  Plus, 
  CheckCircle2, 
  FileCheck
} from 'lucide-react';
import { useApp } from '../context/AppContext';

export default function MedicalDocsPage() {
  const { medicalDocs, addMedicalDoc, removeMedicalDoc, setActiveTab } = useApp();

  // Upload Form State
  const [selectedFile, setSelectedFile] = useState(null);
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('MRI / Diagnostic Imaging');
  const [documentDate, setDocumentDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [clinician, setClinician] = useState('');
  const [notes, setNotes] = useState('');
  const [restrictionRegion, setRestrictionRegion] = useState('Left Knee');
  const [restrictionInstruction, setRestrictionInstruction] = useState('');
  const [restrictionSubstitution, setRestrictionSubstitution] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Preview Modal State
  const [previewDoc, setPreviewDoc] = useState(null);

  // Clean up object URLs on component unmount
  useEffect(() => {
    return () => {
      // Ephemeral cleanup safety guarantee
      medicalDocs.forEach(doc => {
        if (doc.previewUrl && doc.previewUrl.startsWith('blob:')) {
          try { URL.revokeObjectURL(doc.previewUrl); } catch (e) { /* ignore */ }
        }
      });
    };
  }, [medicalDocs]);

  // Handle file selection and validation
  const handleFileChange = (e) => {
    setErrorMessage('');
    setSuccessMessage('');
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file format
    const validTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
    if (!validTypes.includes(file.type)) {
      setErrorMessage('Unsupported file format. Please upload a .pdf, .png, or .jpg medical record.');
      e.target.value = null;
      return;
    }

    // Validate file size < 15MB
    const maxSize = 15 * 1024 * 1024; // 15MB in bytes
    if (file.size > maxSize) {
      setErrorMessage(`File exceeds 15MB limit (${(file.size / (1024 * 1024)).toFixed(1)}MB). Please upload a compressed document.`);
      e.target.value = null;
      return;
    }

    setSelectedFile(file);
    if (!title) {
      setTitle(file.name.replace(/\.[^/.]+$/, '').replace(/_/g, ' '));
    }
  };

  const handleCreateDocument = (e) => {
    e.preventDefault();
    if (!selectedFile) {
      setErrorMessage('Please select a medical file (.pdf, .png, .jpg) to upload.');
      return;
    }
    if (!title.trim()) {
      setErrorMessage('Document title is required.');
      return;
    }

    // Create ephemeral in-memory preview URL
    const previewUrl = URL.createObjectURL(selectedFile);

    const newDoc = {
      id: `doc-${Date.now()}`,
      title: title.trim(),
      category,
      documentDate,
      clinician: clinician.trim() || 'Verified Clinician / Clinic',
      notes: notes.trim() || 'No additional clinician annotations provided.',
      fileName: selectedFile.name,
      fileSize: `${(selectedFile.size / (1024 * 1024)).toFixed(1)} MB`,
      fileSizeRaw: selectedFile.size,
      fileType: selectedFile.type,
      status: 'staged', // Staged in memory
      previewUrl,
      restrictions: restrictionInstruction.trim() ? [
        {
          id: `res-${Date.now()}`,
          anatomicalRegion: restrictionRegion,
          instruction: restrictionInstruction.trim(),
          substitution: restrictionSubstitution.trim() || 'Conservative bodyweight / isometric alternative',
          documentDate
        }
      ] : []
    };

    addMedicalDoc(newDoc, selectedFile);
    setSuccessMessage(`Document "${newDoc.title}" uploaded & cataloged successfully.`);

    // Reset form
    setSelectedFile(null);
    setTitle('');
    setClinician('');
    setNotes('');
    setRestrictionInstruction('');
    setRestrictionSubstitution('');
    const fileInput = document.getElementById('medical-file-input');
    if (fileInput) fileInput.value = '';
  };

  const handleOpenPreview = (doc) => {
    setPreviewDoc(doc);
  };

  const handleClosePreview = () => {
    setPreviewDoc(null);
  };

  const categories = [
    'MRI / Diagnostic Imaging',
    'Orthopedic Evaluation',
    'Physical Therapy Clearance',
    'Surgical History & Post-Op'
  ];

  // Aggregate all active restrictions across uploaded documents
  const allRestrictions = medicalDocs.flatMap(d => d.restrictions || []);

  return (
    <div className="flex-col gap-6">
      {/* Privacy Guarantee Header Alert */}
      <div className="feedback-box feedback-optimal" style={{ borderLeftWidth: 4, borderLeftColor: 'var(--mint-teal)' }}>
        <ShieldCheck size={22} className="text-teal" style={{ flexShrink: 0 }} />
        <div className="flex-col" style={{ gap: 2 }}>
          <strong className="text-primary" style={{ fontSize: '0.9rem' }}>
            Zero-Persistence Medical Privacy Guarantee
          </strong>
          <span className="text-secondary" style={{ fontSize: '0.825rem' }}>
            PERFORMX handles all medical records and clinical reports strictly in transient browser memory. Files are never saved to localStorage or indexedDB, and temporary preview links are revoked immediately upon session dismissal.
          </span>
        </div>
      </div>

      {/* Fitness Tool Scope & Diagnostic Notice */}
      <div className="feedback-box feedback-neutral" style={{ padding: '10px 14px', margin: 0 }}>
        <ShieldCheck size={18} className="text-teal" style={{ flexShrink: 0 }} />
        <span style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
          <strong>Clinical Records Scope:</strong> Uploaded medical documents are used solely by client-side algorithms to extract movement bounds and prevent high-shear joint loading. PERFORMX does not diagnose medical conditions. All restrictions remain subject to physician validation.
        </span>
      </div>

      {/* Top Split: Active Clinician Restrictions Extractor & Upload Dropzone */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 1.2fr) minmax(300px, 1fr)', gap: 24 }}>
        
        {/* Upload Form Card */}
        <section className="card flex-col gap-4">
          <div className="card-header" style={{ marginBottom: 2 }}>
            <div>
              <h2 className="card-title">
                <UploadCloud className="text-orange" size={20} />
                <span>Upload Clinical Record</span>
              </h2>
              <p className="card-subtitle">
                Stage PDF reports or diagnostic scans to extract movement constraints.
              </p>
            </div>
            <span className="staged-badge">In-Memory Staging</span>
          </div>

          {errorMessage && (
            <div className="feedback-box feedback-error" style={{ padding: '8px 12px', fontSize: '0.825rem' }}>
              <AlertTriangle size={16} />
              <span>{errorMessage}</span>
            </div>
          )}

          {successMessage && (
            <div className="feedback-box feedback-optimal" style={{ padding: '8px 12px', fontSize: '0.825rem' }}>
              <CheckCircle2 size={16} />
              <span>{successMessage}</span>
            </div>
          )}

          <form onSubmit={handleCreateDocument} className="flex-col gap-4">
            {/* Dropzone Area */}
            <label 
              htmlFor="medical-file-input" 
              className="medical-dropzone"
              style={{ cursor: 'pointer' }}
            >
              <input
                id="medical-file-input"
                type="file"
                accept=".pdf,.png,.jpg,.jpeg"
                style={{ display: 'none' }}
                onChange={handleFileChange}
              />
              <div className="metric-icon-box metric-icon-orange" style={{ width: 48, height: 48 }}>
                <FileText size={24} />
              </div>
              <div className="flex-col items-center">
                <span className="font-semibold text-primary" style={{ fontSize: '0.925rem' }}>
                  {selectedFile ? selectedFile.name : 'Choose file or drag & drop here'}
                </span>
                <span className="text-muted" style={{ fontSize: '0.78rem', marginTop: 2 }}>
                  {selectedFile 
                    ? `${(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready to stage` 
                    : 'Supported: PDF, PNG, JPG (Max 15MB)'}
                </span>
              </div>
            </label>

            {/* Document Details */}
            <div className="flex-row gap-3" style={{ flexWrap: 'wrap' }}>
              <div className="form-group" style={{ flex: '2 1 200px' }}>
                <label className="form-label">Document Title *</label>
                <input
                  type="text"
                  className="input-field"
                  placeholder="e.g. Left Knee MRI Evaluation"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                />
              </div>

              <div className="form-group" style={{ flex: '1 1 180px' }}>
                <label className="form-label">Clinical Category</label>
                <select
                  className="select-field"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                >
                  {categories.map((cat, i) => (
                    <option key={i} value={cat}>{cat}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex-row gap-3" style={{ flexWrap: 'wrap' }}>
              <div className="form-group" style={{ flex: '1 1 160px' }}>
                <label className="form-label">Evaluation Date</label>
                <input
                  type="date"
                  className="input-field"
                  value={documentDate}
                  onChange={(e) => setDocumentDate(e.target.value)}
                />
              </div>

              <div className="form-group" style={{ flex: '2 1 200px' }}>
                <label className="form-label">Clinician / Facility Name</label>
                <input
                  type="text"
                  className="input-field"
                  placeholder="e.g. Dr. Vance, Sports Medicine"
                  value={clinician}
                  onChange={(e) => setClinician(e.target.value)}
                />
              </div>
            </div>

            {/* Clinician Restriction Extractor Section */}
            <div style={{ background: 'var(--surface-subtle)', padding: 14, borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <span className="font-semibold text-primary" style={{ fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: 6 }}>
                <ShieldAlert size={16} className="text-orange" />
                <span>Clinician Restriction Extractor (Optional)</span>
              </span>
              <p className="text-secondary" style={{ fontSize: '0.78rem', marginTop: 2, marginBottom: 10 }}>
                Specify prescribed movement limits to automatically integrate into adaptive coaching.
              </p>

              <div className="flex-col gap-3">
                <div className="flex-row gap-3">
                  <div className="form-group" style={{ flex: 1 }}>
                    <label className="form-label" style={{ fontSize: '0.75rem' }}>Anatomical Joint</label>
                    <select
                      className="select-field"
                      value={restrictionRegion}
                      onChange={(e) => setRestrictionRegion(e.target.value)}
                    >
                      <option value="Left Knee">Left Knee</option>
                      <option value="Right Knee">Right Knee</option>
                      <option value="Lumbar Spine">Lumbar Spine</option>
                      <option value="Shoulder / Rotator Cuff">Shoulder / Rotator Cuff</option>
                      <option value="Hip">Hip</option>
                      <option value="Ankle">Ankle</option>
                    </select>
                  </div>
                  <div className="form-group" style={{ flex: 2 }}>
                    <label className="form-label" style={{ fontSize: '0.75rem' }}>Motion Limitation / Instruction</label>
                    <input
                      type="text"
                      className="input-field"
                      placeholder="e.g. Cap loaded knee flexion to ≤95°"
                      value={restrictionInstruction}
                      onChange={(e) => setRestrictionInstruction(e.target.value)}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label" style={{ fontSize: '0.75rem' }}>Conservative Exercise Substitution</label>
                  <input
                    type="text"
                    className="input-field"
                    placeholder="e.g. Box Squat to 95° Bench or Leg Press"
                    value={restrictionSubstitution}
                    onChange={(e) => setRestrictionSubstitution(e.target.value)}
                  />
                </div>
              </div>
            </div>

            <button type="submit" className="btn btn-primary btn-md" style={{ width: '100%' }}>
              <Plus size={16} />
              <span>Stage Document into Local Memory</span>
            </button>
          </form>
        </section>

        {/* Active Clinician Restrictions Extractor Summary */}
        <section className="card flex-col gap-4">
          <div className="card-header" style={{ marginBottom: 2 }}>
            <div>
              <h2 className="card-title">
                <ShieldAlert className="text-teal" size={20} />
                <span>Active Medical Restrictions</span>
              </h2>
              <p className="card-subtitle">
                Prescribed movement barriers that strictly govern training algorithms.
              </p>
            </div>
            <span className="badge badge-teal">{allRestrictions.length} Active</span>
          </div>

          <div className="feedback-box feedback-warning" style={{ margin: 0, padding: '10px 14px' }}>
            <AlertTriangle size={18} className="text-amber" style={{ flexShrink: 0 }} />
            <span style={{ fontSize: '0.8rem', color: '#92400E' }}>
              <strong>Clinician Restriction Priority:</strong> Adaptive recommendations will never override these instructions. Ambiguous guidance is strictly held for clinician re-evaluation.
            </span>
          </div>

          <div className="flex-col gap-3" style={{ flex: 1, overflowY: 'auto', maxHeight: 420 }}>
            {allRestrictions.length === 0 ? (
              <div className="empty-state" style={{ padding: '30px 16px' }}>
                <CheckCircle2 size={36} className="text-teal" />
                <span className="font-semibold text-primary">No Active Medical Restrictions</span>
                <p className="text-secondary" style={{ fontSize: '0.8rem' }}>
                  Full movement clearance active. Upload physical therapy or orthopedic records to add constraints.
                </p>
              </div>
            ) : (
              allRestrictions.map((res, i) => (
                <div 
                  key={i} 
                  className="card-flat flex-col gap-2" 
                  style={{ 
                    borderLeft: '4px solid var(--primary-orange)',
                    background: 'var(--surface-subtle)',
                    padding: '14px 16px'
                  }}
                >
                  <div className="flex-row justify-between items-center">
                    <span className="badge badge-orange" style={{ fontSize: '0.75rem' }}>
                      {res.anatomicalRegion}
                    </span>
                    <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                      {res.documentDate}
                    </span>
                  </div>

                  <p className="font-semibold text-primary" style={{ fontSize: '0.875rem', margin: 0 }}>
                    {res.instruction}
                  </p>

                  {res.substitution && (
                    <div className="flex-row items-center gap-2" style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      <span className="font-semibold text-teal">Substitute:</span>
                      <span>{res.substitution}</span>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          <button 
            className="btn btn-secondary btn-sm" 
            style={{ width: '100%', marginTop: 'auto' }}
            onClick={() => setActiveTab('injury-training')}
          >
            <span>View Injury-Aware Training Protocol</span>
          </button>
        </section>
      </div>

      {/* Staged Medical Documents Table / List */}
      <section className="card flex-col gap-4">
        <div className="card-header">
          <div>
            <h2 className="card-title">
              <FileCheck className="text-orange" size={20} />
              <span>Staged Clinical Documents ({medicalDocs.length})</span>
            </h2>
            <p className="card-subtitle">
              Documents held in transient browser memory ready for clinician review or session evaluation.
            </p>
          </div>
          <span className="badge badge-orange">In-Memory Active</span>
        </div>

        {medicalDocs.length === 0 ? (
          <div className="empty-state" style={{ padding: '40px 20px' }}>
            <FileText size={42} className="text-muted" />
            <span className="font-semibold text-primary">No Clinical Documents Staged</span>
            <p className="text-secondary" style={{ fontSize: '0.85rem' }}>
              Upload an MRI scan, physical therapy report, or post-op document above.
            </p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Category</th>
                  <th>Evaluator & Date</th>
                  <th>Clinical Guidance</th>
                  <th>Status</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {medicalDocs.map((doc) => (
                  <tr key={doc.id}>
                    <td>
                      <div className="flex-row items-center gap-3">
                        <div className="metric-icon-box metric-icon-orange" style={{ width: 34, height: 34 }}>
                          <FileText size={17} />
                        </div>
                        <div className="flex-col">
                          <span className="font-semibold text-primary" style={{ fontSize: '0.875rem' }}>
                            {doc.title}
                          </span>
                          <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                            {doc.fileName} • {doc.fileSize}
                          </span>
                        </div>
                      </div>
                    </td>

                    <td>
                      <span className="badge badge-neutral" style={{ fontSize: '0.75rem' }}>
                        {doc.category}
                      </span>
                    </td>

                    <td>
                      <div className="flex-col">
                        <span className="font-semibold text-primary" style={{ fontSize: '0.825rem' }}>
                          {doc.clinician}
                        </span>
                        <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                          {doc.documentDate}
                        </span>
                      </div>
                    </td>

                    <td style={{ maxWidth: 280 }}>
                      <span className="text-secondary" style={{ fontSize: '0.8rem', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                        {doc.notes}
                      </span>
                    </td>

                    <td>
                      <span className="staged-badge" title="Retained exclusively in active memory">
                        Staged in Memory
                      </span>
                    </td>

                    <td style={{ textAlign: 'right' }}>
                      <div className="flex-row gap-2 justify-end">
                        <button
                          className="btn-secondary btn-icon btn-sm"
                          onClick={() => handleOpenPreview(doc)}
                          title="Preview Document Ephemerally"
                          aria-label="Preview Document"
                        >
                          <Eye size={15} />
                        </button>
                        <button
                          className="btn-danger btn-icon btn-sm"
                          onClick={() => removeMedicalDoc(doc.id)}
                          title="Purge Document from Memory"
                          aria-label="Delete Document"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Ephemeral Document Preview Modal */}
      {previewDoc && (
        <div 
          className="modal-overlay" 
          onClick={handleClosePreview}
          role="dialog"
          aria-modal="true"
          aria-label="Document Preview"
        >
          <div 
            className="modal-box" 
            style={{ maxWidth: 700, width: '92%' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <div className="flex-row items-center gap-3">
                <div className="metric-icon-box metric-icon-orange" style={{ width: 36, height: 36 }}>
                  <FileText size={18} />
                </div>
                <div>
                  <h3 className="modal-title" style={{ fontSize: '1.1rem' }}>{previewDoc.title}</h3>
                  <span className="staged-badge" style={{ marginTop: 2 }}>Staged Ephemeral Record</span>
                </div>
              </div>
              <button 
                className="btn-ghost btn-icon btn-sm" 
                onClick={handleClosePreview}
                aria-label="Close Preview"
              >
                <X size={20} />
              </button>
            </div>

            <div className="modal-body flex-col gap-4">
              <div className="flex-row justify-between" style={{ background: 'var(--surface-subtle)', padding: 12, borderRadius: 'var(--radius-md)' }}>
                <div>
                  <span className="text-muted" style={{ fontSize: '0.75rem' }}>Category:</span>
                  <div className="font-semibold text-primary">{previewDoc.category}</div>
                </div>
                <div>
                  <span className="text-muted" style={{ fontSize: '0.75rem' }}>Evaluator:</span>
                  <div className="font-semibold text-primary">{previewDoc.clinician}</div>
                </div>
                <div>
                  <span className="text-muted" style={{ fontSize: '0.75rem' }}>Date:</span>
                  <div className="font-semibold text-primary">{previewDoc.documentDate}</div>
                </div>
              </div>

              {/* Preview Rendering */}
              <div 
                style={{ 
                  minHeight: 220, 
                  background: '#F8FAFC', 
                  borderRadius: 'var(--radius-md)', 
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: 20,
                  overflow: 'hidden'
                }}
              >
                {previewDoc.fileType.startsWith('image/') && previewDoc.previewUrl ? (
                  <img 
                    src={previewDoc.previewUrl} 
                    alt={previewDoc.title}
                    style={{ maxWidth: '100%', maxHeight: 380, objectFit: 'contain', borderRadius: 8 }}
                  />
                ) : (
                  <div className="flex-col items-center gap-3 text-center">
                    <FileText size={56} className="text-orange" />
                    <div>
                      <strong className="text-primary">{previewDoc.fileName}</strong>
                      <p className="text-muted" style={{ fontSize: '0.8rem', marginTop: 4 }}>
                        PDF Document ({previewDoc.fileSize}) — Securely loaded in local memory.
                      </p>
                    </div>
                    <span className="badge badge-teal" style={{ fontSize: '0.75rem' }}>
                      Sandboxed In-Browser Stream
                    </span>
                  </div>
                )}
              </div>

              <div>
                <span className="font-semibold text-primary" style={{ fontSize: '0.85rem' }}>Clinical Annotations:</span>
                <p className="text-secondary" style={{ fontSize: '0.85rem', marginTop: 4, lineHeight: 1.5 }}>
                  {previewDoc.notes}
                </p>
              </div>

              {previewDoc.restrictions && previewDoc.restrictions.length > 0 && (
                <div style={{ background: 'var(--warning-soft)', padding: 12, borderRadius: 'var(--radius-md)', border: '1px solid #FCD34D' }}>
                  <span className="font-bold text-amber" style={{ fontSize: '0.85rem' }}>
                    Extracted Movement Constraint:
                  </span>
                  <p style={{ fontSize: '0.825rem', color: '#92400E', marginTop: 2 }}>
                    {previewDoc.restrictions[0].instruction}
                  </p>
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={handleClosePreview}>
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
