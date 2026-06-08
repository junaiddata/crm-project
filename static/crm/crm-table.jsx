// CRM Table View — inline editing, sorting, add/delete rows

const TABLE_COLUMNS = [
  { key: 'date',         label: 'Date',         type: 'date',       w: 108 },
  { key: 'mobileNo',     label: 'Mobile No',    type: 'text',       w: 118 },
  { key: 'emailId',      label: 'Email ID',     type: 'text',       w: 165 },
  { key: 'name',         label: 'Name',         type: 'text',       w: 195 },
  { key: 'platform',     label: 'Platform',     type: 'select',     options: () => CRM_PLATFORMS,    w: 108 },
  { key: 'items',        label: 'Items',        type: 'text',       w: 240 },
  { key: 'salesPerson',  label: 'Sales Person', type: 'select',     options: () => CRM_SALESPEOPLE, w: 118 },
  { key: 'quotation',    label: 'Quotation',    type: 'file',       w: 155 },
  { key: 'quotationDate',label: 'Quote Date',   type: 'date',       w: 108 },
  { key: 'followUp1',    label: 'Follow Up 1',  type: 'followup',   dateKey: 'followUp1Date', notesKey: 'followUp1Notes', w: 165 },
  { key: 'followUp2',    label: 'Follow Up 2',  type: 'followup',   dateKey: 'followUp2Date', notesKey: 'followUp2Notes', w: 165 },
  { key: 'leadStatus',   label: 'Status',       type: 'status',     w: 148 },
];

// ── File Cell (self-contained, own ref) ─────────────────────────────────────
function FileCell({ lead, onUpdateLead }) {
  const inputRef = React.useRef(null);
  const fd = lead.quotationFile;

  function handleFile(e) {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 8 * 1024 * 1024) {
      alert('File is too large (max 8 MB). Please compress or use a smaller file.');
      return;
    }
    const reader = new FileReader();
    reader.onload = ev => {
      onUpdateLead(lead.id, { quotationFile: { name: file.name, data: ev.target.result, mime: file.type } });
    };
    reader.readAsDataURL(file);
    // reset so same file can be re-selected
    e.target.value = '';
  }

  function removeFile(e) {
    e.stopPropagation();
    onUpdateLead(lead.id, { quotationFile: null });
  }

  return (
    <div className="crm-file-cell" onClick={e => e.stopPropagation()}>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png"
        style={{ display: 'none' }}
        onChange={handleFile}
      />
      {fd && fd.name ? (
        <div className="crm-file-info">
          <a href={fd.data} target="_blank" rel="noopener noreferrer"
             className="crm-file-link" title={fd.name} onClick={e => e.stopPropagation()}>
            <svg width="13" height="13" viewBox="0 0 20 20" fill="currentColor" style={{flexShrink:0}}>
              <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd"/>
            </svg>
            <span>{fd.name}</span>
          </a>
          <button className="crm-file-del" title="Remove file" onClick={removeFile}>×</button>
        </div>
      ) : (
        <button className="crm-upload-btn" onClick={() => inputRef.current && inputRef.current.click()}>
          <svg width="12" height="12" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clipRule="evenodd"/>
          </svg>
          Upload
        </button>
      )}
    </div>
  );
}

// ── Main Table ───────────────────────────────────────────────────────────────
function CrmTable({ leads, onUpdateLead, onDeleteLead, sortBy, onSort }) {
  const [editCell, setEditCell] = React.useState(null);
  const [editVal,  setEditVal]  = React.useState('');
  const [editVal2, setEditVal2] = React.useState('');
  const [hoveredRow, setHoveredRow] = React.useState(null);

  function startEdit(rowId, col, lead) {
    if (col.type === 'file') return; // handled by FileCell itself
    if (col.type === 'followup') {
      setEditCell({ rowId, field: col.key });
      setEditVal(lead[col.dateKey] || '');
      setEditVal2(lead[col.notesKey] || '');
    } else {
      setEditCell({ rowId, field: col.key });
      setEditVal(col.type === 'status' ? (lead.leadStatus || '') : (lead[col.key] || ''));
    }
  }

  function commitEdit(rowId, col) {
    if (col.type === 'followup') {
      onUpdateLead(rowId, { [col.dateKey]: editVal, [col.notesKey]: editVal2 });
    } else if (col.type === 'status') {
      onUpdateLead(rowId, { leadStatus: editVal });
    } else {
      onUpdateLead(rowId, { [col.key]: editVal });
    }
    setEditCell(null);
  }

  function isEditing(rowId, field) {
    return editCell && editCell.rowId === rowId && editCell.field === field;
  }

  function handleSort(col) {
    if (col.type === 'followup' || col.type === 'file') return;
    onSort(col.type === 'status' ? 'leadStatus' : col.key);
  }

  function getSortIcon(col) {
    if (col.type === 'followup' || col.type === 'file') return null;
    const key = col.type === 'status' ? 'leadStatus' : col.key;
    if (!sortBy || sortBy.field !== key)
      return <span className="crm-sort-icon muted"><CrmIcon name="chevDown" size={12}/></span>;
    return <span className="crm-sort-icon"><CrmIcon name={sortBy.dir === 'asc' ? 'sortAsc' : 'sortDesc'} size={12}/></span>;
  }

  function renderCell(lead, col) {
    const rowId = lead.id;

    // ── File cell ──
    if (col.type === 'file') {
      return <FileCell lead={lead} onUpdateLead={onUpdateLead} />;
    }

    // ── Editing state ──
    if (isEditing(rowId, col.key)) {
      if (col.type === 'text') {
        return (
          <input className="crm-cell-input" value={editVal} autoFocus
            onChange={e => setEditVal(e.target.value)}
            onBlur={() => commitEdit(rowId, col)}
            onKeyDown={e => { if (e.key === 'Enter') commitEdit(rowId, col); if (e.key === 'Escape') setEditCell(null); }}
          />
        );
      }
      if (col.type === 'date') {
        return (
          <input type="date" className="crm-cell-input" value={editVal} autoFocus
            onChange={e => setEditVal(e.target.value)}
            onBlur={() => commitEdit(rowId, col)}
            onKeyDown={e => { if (e.key === 'Escape') setEditCell(null); }}
          />
        );
      }
      // ── SELECT fix: capture value directly, skip stale-closure ──
      if (col.type === 'select') {
        return (
          <select className="crm-cell-input" value={editVal} autoFocus
            onChange={e => {
              const val = e.target.value;
              onUpdateLead(rowId, { [col.key]: val });
              setEditCell(null);
            }}
            onKeyDown={e => { if (e.key === 'Escape') setEditCell(null); }}>
            <option value="">—</option>
            {(col.options ? col.options() : []).map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        );
      }
      if (col.type === 'searchable') {
        return (
          <SearchableDropdown value={editVal} options={CRM_PRODUCTS} placeholder="Search items..."
            onChange={v => { onUpdateLead(rowId, { [col.key]: v }); setEditCell(null); }}
          />
        );
      }
      // ── STATUS fix: same direct-value approach ──
      if (col.type === 'status') {
        return (
          <select className="crm-cell-input" value={editVal} autoFocus
            onChange={e => {
              const val = e.target.value;
              onUpdateLead(rowId, { leadStatus: val });
              setEditCell(null);
            }}
            onKeyDown={e => { if (e.key === 'Escape') setEditCell(null); }}>
            <option value="">New</option>
            {CRM_LEAD_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        );
      }
      if (col.type === 'followup') {
        return (
          <div className="crm-followup-edit">
            <input type="date" className="crm-cell-input crm-cell-input-sm" value={editVal} autoFocus
              onChange={e => setEditVal(e.target.value)}
              onKeyDown={e => { if (e.key === 'Escape') setEditCell(null); }}
            />
            <input className="crm-cell-input crm-cell-input-sm" value={editVal2} placeholder="Notes..."
              onChange={e => setEditVal2(e.target.value)}
              onBlur={() => commitEdit(rowId, col)}
              onKeyDown={e => { if (e.key === 'Enter') commitEdit(rowId, col); if (e.key === 'Escape') setEditCell(null); }}
            />
          </div>
        );
      }
    }

    // ── Display mode ──
    if (col.type === 'followup') {
      const dt = lead[col.dateKey], nt = lead[col.notesKey];
      if (!dt && !nt) return <span className="crm-cell-empty">—</span>;
      return (
        <div className="crm-followup-display">
          {dt && <span className="crm-fu-date">{formatDateDisplay(dt)}</span>}
          {nt && <span className="crm-fu-notes">{nt}</span>}
        </div>
      );
    }
    if (col.type === 'status') return <StatusBadge status={lead.leadStatus} compact />;
    if (col.type === 'date') {
      const v = formatDateDisplay(lead[col.key]);
      return v ? <span>{v}</span> : <span className="crm-cell-empty">—</span>;
    }
    const val = lead[col.key];
    if (!val) return <span className="crm-cell-empty">—</span>;
    return <span className="crm-cell-text" title={val}>{val}</span>;
  }

  return (
    <div className="crm-table-wrap">
      <table className="crm-table">
        <thead>
          <tr>
            <th className="crm-th crm-th-num">#</th>
            {TABLE_COLUMNS.map(col => (
              <th key={col.key} className="crm-th" style={{ width: col.w, minWidth: col.w }}
                onClick={() => handleSort(col)}>
                <div className="crm-th-inner">{col.label}{getSortIcon(col)}</div>
              </th>
            ))}
            <th className="crm-th crm-th-actions" style={{ width: 48 }}></th>
          </tr>
        </thead>
        <tbody>
          {leads.map((lead, idx) => (
            <tr key={lead.id}
              className={`crm-row ${hoveredRow === lead.id ? 'crm-row-hover' : ''}`}
              onMouseEnter={() => setHoveredRow(lead.id)}
              onMouseLeave={() => setHoveredRow(null)}>
              <td className="crm-td crm-td-num">{idx + 1}</td>
              {TABLE_COLUMNS.map(col => (
                <td key={col.key}
                  className={`crm-td ${isEditing(lead.id, col.key) ? 'crm-td-editing' : ''} ${col.type === 'file' ? 'crm-td-file' : ''}`}
                  style={{ width: col.w, minWidth: col.w }}
                  onClick={() => { if (!isEditing(lead.id, col.key)) startEdit(lead.id, col, lead); }}>
                  {renderCell(lead, col)}
                </td>
              ))}
              <td className="crm-td crm-td-actions">
                {hoveredRow === lead.id && (
                  <button className="crm-del-btn" title="Delete lead"
                    onClick={e => { e.stopPropagation(); onDeleteLead(lead.id); }}>
                    <CrmIcon name="trash" size={14} />
                  </button>
                )}
              </td>
            </tr>
          ))}
          {leads.length === 0 && (
            <tr><td colSpan={TABLE_COLUMNS.length + 2} className="crm-empty-row">No leads found</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

Object.assign(window, { CrmTable, TABLE_COLUMNS, FileCell });
