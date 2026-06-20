// Shared UI Components for CRM

// --- SVG Icons ---
function CrmIcon({ name, size = 16 }) {
  const s = { width: size, height: size, display: 'inline-block', verticalAlign: 'middle', flexShrink: 0 };
  const icons = {
    search: <svg style={s} viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd"/></svg>,
    plus: <svg style={s} viewBox="0 0 20 20" fill="currentColor"><path d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"/></svg>,
    download: <svg style={s} viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd"/></svg>,
    trash: <svg style={s} viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd"/></svg>,
    sortAsc: <svg style={s} viewBox="0 0 20 20" fill="currentColor"><path d="M5.293 7.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L10 4.414l-3.293 3.293a1 1 0 01-1.414 0z"/></svg>,
    sortDesc: <svg style={s} viewBox="0 0 20 20" fill="currentColor"><path d="M14.707 12.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L10 15.586l3.293-3.293a1 1 0 011.414 0z"/></svg>,
    table: <svg style={s} viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M5 4a3 3 0 00-3 3v6a3 3 0 003 3h10a3 3 0 003-3V7a3 3 0 00-3-3H5zm-1 9v-1h5v2H5a1 1 0 01-1-1zm7 1h4a1 1 0 001-1v-1h-5v2zm0-4h5V8h-5v2zM9 8H4v2h5V8z" clipRule="evenodd"/></svg>,
    board: <svg style={s} viewBox="0 0 20 20" fill="currentColor"><path d="M2 4a1 1 0 011-1h3a1 1 0 011 1v12a1 1 0 01-1 1H3a1 1 0 01-1-1V4zm5 0a1 1 0 011-1h3a1 1 0 011 1v8a1 1 0 01-1 1H8a1 1 0 01-1-1V4zm6-1a1 1 0 00-1 1v6a1 1 0 001 1h3a1 1 0 001-1V4a1 1 0 00-1-1h-3z"/></svg>,
    edit: <svg style={s} viewBox="0 0 20 20" fill="currentColor"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/></svg>,
    close: <svg style={s} viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd"/></svg>,
    chevDown: <svg style={s} viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd"/></svg>,
    users: <svg style={s} viewBox="0 0 20 20" fill="currentColor"><path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z"/></svg>,
    check: <svg style={s} viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/></svg>,
    clock: <svg style={s} viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd"/></svg>,
    chart: <svg style={s} viewBox="0 0 20 20" fill="currentColor"><path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"/></svg>,
    calendar: <svg style={s} viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd"/></svg>,
  };
  return icons[name] || null;
}

// --- Searchable Dropdown ---
function SearchableDropdown({ value, onChange, options, placeholder }) {
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState(value || '');
  const ref = React.useRef(null);
  const inputRef = React.useRef(null);

  React.useEffect(() => { setSearch(value || ''); }, [value]);

  React.useEffect(() => {
    if (inputRef.current) inputRef.current.focus();
    function handler(e) {
      if (ref.current && !ref.current.contains(e.target)) {
        onChange(search);
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [search]);

  const filtered = options.filter(o => o.toLowerCase().includes(search.toLowerCase()));

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <input
        ref={inputRef}
        className="crm-cell-input"
        value={search}
        onChange={e => { setSearch(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onKeyDown={e => {
          if (e.key === 'Enter') { onChange(search); setOpen(false); e.target.blur(); }
          if (e.key === 'Escape') { setOpen(false); e.target.blur(); }
        }}
        placeholder={placeholder}
      />
      {open && filtered.length > 0 && (
        <div className="crm-dd-menu">
          {filtered.slice(0, 8).map(opt => (
            <div key={opt} className="crm-dd-item"
              onMouseDown={e => { e.preventDefault(); setSearch(opt); onChange(opt); setOpen(false); }}>
              {opt}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// --- Status Badge ---
function StatusBadge({ status, compact }) {
  const c = CRM_STATUS_CONFIG[status] || CRM_STATUS_CONFIG[''];
  return (
    <span className={`crm-badge ${compact ? 'crm-badge-sm' : ''}`} style={{ background: c.bg, color: c.text }}>
      <span className="crm-badge-dot" style={{ background: c.dot }}></span>
      {c.label}
    </span>
  );
}

// --- Stat Card ---
function StatCard({ label, value, icon, color, subtitle }) {
  return (
    <div className="crm-stat-card">
      <div className="crm-stat-icon" style={{ background: color + '18', color: color }}>
        <CrmIcon name={icon} size={20} />
      </div>
      <div className="crm-stat-body">
        <div className="crm-stat-value">{value}</div>
        <div className="crm-stat-label">{label}</div>
        {subtitle && <div className="crm-stat-sub">{subtitle}</div>}
      </div>
    </div>
  );
}

// --- Toast ---
function CrmToast({ message, type, onClose }) {
  React.useEffect(() => {
    const t = setTimeout(onClose, 2800);
    return () => clearTimeout(t);
  }, []);
  const bg = type === 'success' ? '#059669' : type === 'error' ? '#dc2626' : '#1d4ed8';
  return (
    <div className="crm-toast" style={{ background: bg }}>
      <span>{message}</span>
      <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', marginLeft: 12, padding: 2 }}>
        <CrmIcon name="close" size={14} />
      </button>
    </div>
  );
}

// --- Confirm Dialog ---
function ConfirmDialog({ message, onConfirm, onCancel }) {
  return (
    <div className="crm-overlay" onClick={onCancel}>
      <div className="crm-dialog" onClick={e => e.stopPropagation()}>
        <div className="crm-dialog-icon">
          <CrmIcon name="trash" size={24} />
        </div>
        <p className="crm-dialog-msg">{message}</p>
        <div className="crm-dialog-actions">
          <button className="crm-btn crm-btn-ghost" onClick={onCancel}>Cancel</button>
          <button className="crm-btn crm-btn-danger" onClick={onConfirm}>Delete</button>
        </div>
      </div>
    </div>
  );
}

// --- Lead Detail Modal (for Kanban card click) ---
function LeadDetailModal({ lead, onUpdate, onClose }) {
  const [form, setForm] = React.useState({ ...lead });
  const set = (k, v) => setForm(prev => ({ ...prev, [k]: v }));

  function handleSave() {
    onUpdate(form);
    onClose();
  }

  const fieldStyle = { display: 'flex', flexDirection: 'column', gap: 4 };
  const labelStyle = { fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em' };
  const inputStyle = { padding: '7px 10px', border: '1px solid #e2e8f0', borderRadius: 6, fontSize: 13, outline: 'none', fontFamily: 'inherit' };

  return (
    <div className="crm-overlay" onClick={onClose}>
      <div className="crm-modal" onClick={e => e.stopPropagation()}>
        <div className="crm-modal-header">
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>Edit Lead</h3>
          <button className="crm-icon-btn" onClick={onClose}><CrmIcon name="close" size={18} /></button>
        </div>
        <div className="crm-modal-body">
          <div className="crm-modal-grid">
            <div style={fieldStyle}>
              <label style={labelStyle}>Date</label>
              <input type="date" value={form.date} onChange={e => set('date', e.target.value)} style={inputStyle} />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Mobile No</label>
              <input value={form.mobileNo} onChange={e => set('mobileNo', e.target.value)} style={inputStyle} placeholder="Phone number" />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Email</label>
              <input value={form.emailId} onChange={e => set('emailId', e.target.value)} style={inputStyle} placeholder="Email" />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Name</label>
              <input value={form.name} onChange={e => set('name', e.target.value)} style={inputStyle} placeholder="Company / Contact" />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Platform</label>
              <select value={form.platform} onChange={e => set('platform', e.target.value)} style={inputStyle}>
                <option value="">Select...</option>
                {CRM_PLATFORMS.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Sales Person</label>
              <select value={form.salesPerson} onChange={e => set('salesPerson', e.target.value)} style={inputStyle}>
                <option value="">Select...</option>
                {CRM_SALESPEOPLE.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
          </div>
          <div style={{ ...fieldStyle, marginTop: 12 }}>
            <label style={labelStyle}>Items</label>
            <input value={form.items} onChange={e => set('items', e.target.value)} style={inputStyle} placeholder="Product / Enquiry" />
          </div>
          <div className="crm-modal-grid" style={{ marginTop: 12 }}>
            <div style={fieldStyle}>
              <label style={labelStyle}>Quotation</label>
              <input value={form.quotation} onChange={e => set('quotation', e.target.value)} style={inputStyle} placeholder="Amount" />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Quotation Date</label>
              <input type="date" value={form.quotationDate} onChange={e => set('quotationDate', e.target.value)} style={inputStyle} />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Lead Status</label>
              <select value={form.leadStatus} onChange={e => set('leadStatus', e.target.value)} style={inputStyle}>
                <option value="">New</option>
                {CRM_LEAD_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>
          <div style={{ marginTop: 16, padding: '12px 0', borderTop: '1px solid #e2e8f0' }}>
            <div style={{ ...labelStyle, marginBottom: 8 }}>Follow Up 1</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <input type="date" value={form.followUp1Date} onChange={e => set('followUp1Date', e.target.value)} style={{ ...inputStyle, flex: '0 0 150px' }} />
              <input value={form.followUp1Notes} onChange={e => set('followUp1Notes', e.target.value)} style={{ ...inputStyle, flex: 1 }} placeholder="Notes..." />
            </div>
          </div>
          <div style={{ paddingTop: 8 }}>
            <div style={{ ...labelStyle, marginBottom: 8 }}>Follow Up 2</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <input type="date" value={form.followUp2Date} onChange={e => set('followUp2Date', e.target.value)} style={{ ...inputStyle, flex: '0 0 150px' }} />
              <input value={form.followUp2Notes} onChange={e => set('followUp2Notes', e.target.value)} style={{ ...inputStyle, flex: 1 }} placeholder="Notes..." />
            </div>
          </div>
        </div>
        <div className="crm-modal-footer">
          <button className="crm-btn crm-btn-ghost" onClick={onClose}>Cancel</button>
          <button className="crm-btn crm-btn-primary" onClick={handleSave}>Save Changes</button>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, {
  CrmIcon, SearchableDropdown, StatusBadge, StatCard, CrmToast, ConfirmDialog, LeadDetailModal
});
