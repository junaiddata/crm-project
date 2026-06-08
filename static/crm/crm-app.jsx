// CRM Main App — API-backed state management, dashboard, layout

function CrmApp() {
  const [leads, setLeads] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [view, setView] = React.useState('table');
  const [search, setSearch] = React.useState('');
  const [filterSales, setFilterSales] = React.useState('');
  const [filterPlatform, setFilterPlatform] = React.useState('');
  const [filterStatus, setFilterStatus] = React.useState('__all__');
  const [sortBy, setSortBy] = React.useState({ field: 'date', dir: 'desc' });
  const [toast, setToast] = React.useState(null);
  const [confirmDel, setConfirmDel] = React.useState(null);

  function showToast(message, type) {
    setToast({ message, type, key: Date.now() });
  }

  // Load leads from API on mount
  React.useEffect(() => {
    getStoredLeads()
      .then(data => { setLeads(data); setLoading(false); })
      .catch(() => { setLoading(false); showToast('Failed to load leads', 'error'); });
  }, []);

  // --- CRUD ---
  async function addLead() {
    try {
      const newLead = await createLead({ date: todayISO() });
      setLeads(prev => [newLead, ...prev]);
      setView('table');
      showToast('New lead added', 'success');
    } catch (e) {
      showToast('Failed to add lead', 'error');
    }
  }

  async function updateLead(id, updates) {
    // Optimistic update for snappy UI
    setLeads(prev => prev.map(l => l.id === id ? { ...l, ...updates } : l));

    try {
      const { quotationFile, id: _id, ...patchData } = updates;

      // Handle file operations
      if ('quotationFile' in updates) {
        if (quotationFile && quotationFile.data && quotationFile.data.startsWith('data:')) {
          // New file upload
          const result = await uploadFile(id, quotationFile);
          setLeads(prev => prev.map(l => l.id === id ? { ...l, quotationFile: result } : l));
        } else if (quotationFile === null) {
          // File removed
          await removeFile(id);
        }
      }

      // PATCH all non-file fields
      if (Object.keys(patchData).length > 0) {
        await patchLead(id, patchData);
      }
    } catch (e) {
      showToast('Failed to save changes', 'error');
      // Reload to restore server state
      getStoredLeads().then(data => setLeads(data)).catch(() => {});
    }
  }

  function deleteLead(id) {
    setConfirmDel(id);
  }

  async function confirmDelete() {
    const id = confirmDel;
    setConfirmDel(null);
    setLeads(prev => prev.filter(l => l.id !== id));
    try {
      await removeLead(id);
      showToast('Lead deleted', 'success');
    } catch (e) {
      showToast('Failed to delete lead', 'error');
      getStoredLeads().then(data => setLeads(data)).catch(() => {});
    }
  }

  function handleExport() {
    exportToCSV(filteredLeads);
    showToast('Exported ' + filteredLeads.length + ' leads', 'success');
  }

  function reloadData() {
    setLoading(true);
    getStoredLeads()
      .then(data => { setLeads(data); setLoading(false); showToast('Data reloaded', 'success'); })
      .catch(() => { setLoading(false); showToast('Failed to reload', 'error'); });
  }

  // --- Sorting ---
  function handleSort(field) {
    setSortBy(prev => ({
      field,
      dir: prev.field === field && prev.dir === 'asc' ? 'desc' : 'asc'
    }));
  }

  // --- Filtering ---
  const filteredLeads = React.useMemo(() => {
    let result = [...leads];

    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(l =>
        (l.name || '').toLowerCase().includes(q) ||
        (l.emailId || '').toLowerCase().includes(q) ||
        (l.mobileNo || '').toLowerCase().includes(q) ||
        (l.items || '').toLowerCase().includes(q) ||
        (l.salesPerson || '').toLowerCase().includes(q) ||
        (l.quotation || '').toLowerCase().includes(q)
      );
    }

    if (filterSales) result = result.filter(l => l.salesPerson === filterSales);
    if (filterPlatform) result = result.filter(l => l.platform === filterPlatform);
    if (filterStatus !== '__all__') result = result.filter(l => (l.leadStatus || '') === filterStatus);

    if (sortBy.field) {
      result.sort((a, b) => {
        let va = a[sortBy.field] || '';
        let vb = b[sortBy.field] || '';
        if (typeof va === 'string') va = va.toLowerCase();
        if (typeof vb === 'string') vb = vb.toLowerCase();
        if (va < vb) return sortBy.dir === 'asc' ? -1 : 1;
        if (va > vb) return sortBy.dir === 'asc' ? 1 : -1;
        return 0;
      });
    }

    return result;
  }, [leads, search, filterSales, filterPlatform, filterStatus, sortBy]);

  // --- Dashboard stats ---
  const stats = React.useMemo(() => {
    const total = leads.length;
    const approved = leads.filter(l => l.leadStatus === 'Approved').length;
    const pending = leads.filter(l => !l.leadStatus).length;
    const quoted = leads.filter(l => l.quotation || l.quotationFile).length;
    const now = new Date();
    const thisMonth = leads.filter(l => {
      if (!l.date) return false;
      const d = new Date(l.date);
      return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
    }).length;
    const rate = total > 0 ? Math.round((approved / total) * 100) : 0;
    return { total, approved, pending, quoted, thisMonth, rate };
  }, [leads]);

  const hasFilters = search || filterSales || filterPlatform || filterStatus !== '__all__';

  return (
    <div className="crm-root">
      {/* Header */}
      <header className="crm-header">
        <div className="crm-header-left">
          <div className="crm-logo">
            <img src="https://junaidworld.com/wp-content/uploads/2023/09/footer-logo.png.webp"
                 alt="Company Logo"
                 style={{height:'38px', objectFit:'contain', maxWidth:'130px', display:'block'}} />
          </div>
          <div>
            <h1 className="crm-title">CRM Lead Manager</h1>
            <p className="crm-subtitle">{stats.total} total leads · {stats.thisMonth} this month</p>
          </div>
        </div>
        <div className="crm-header-right">
          <a href="/calls/" className="crm-btn crm-btn-outline" style={{textDecoration:'none'}}>
            <svg width="15" height="15" viewBox="0 0 20 20" fill="currentColor"><path d="M2 3a1 1 0 011-1h2.153a1 1 0 01.986.836l.74 4.435a1 1 0 01-.54 1.06l-1.548.773a11.037 11.037 0 006.105 6.105l.774-1.548a1 1 0 011.059-.54l4.435.74a1 1 0 01.836.986V17a1 1 0 01-1 1h-2C7.82 18 2 12.18 2 5V3z"/></svg>
            Incoming Calls
          </a>
          <button className="crm-btn crm-btn-outline" onClick={handleExport}>
            <CrmIcon name="download" size={15} />
            Export CSV
          </button>
          <button className="crm-btn crm-btn-accent" onClick={addLead}>
            <CrmIcon name="plus" size={15} />
            Add Lead
          </button>
        </div>
      </header>

      {/* Dashboard */}
      <div className="crm-dashboard">
        <StatCard label="Total Leads" value={stats.total} icon="users" color="#1d4ed8" />
        <StatCard label="Approved" value={stats.approved} icon="check" color="#059669" subtitle={stats.rate + '% conversion'} />
        <StatCard label="Pending" value={stats.pending} icon="clock" color="#d97706" subtitle="No status yet" />
        <StatCard label="Quoted" value={stats.quoted} icon="chart" color="#7c3aed" subtitle="With quotation" />
        <StatCard label="This Month" value={stats.thisMonth} icon="calendar" color="#0284c7" />
      </div>

      {/* Controls Bar */}
      <div className="crm-controls">
        <div className="crm-controls-left">
          <div className="crm-search-wrap">
            <CrmIcon name="search" size={15} />
            <input className="crm-search" placeholder="Search leads..." value={search}
              onChange={e => setSearch(e.target.value)} />
            {search && (
              <button className="crm-search-clear" onClick={() => setSearch('')}>
                <CrmIcon name="close" size={12} />
              </button>
            )}
          </div>
          <select className="crm-filter-select" value={filterSales} onChange={e => setFilterSales(e.target.value)}>
            <option value="">All Sales People</option>
            {CRM_SALESPEOPLE.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <select className="crm-filter-select" value={filterPlatform} onChange={e => setFilterPlatform(e.target.value)}>
            <option value="">All Platforms</option>
            {CRM_PLATFORMS.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
          <select className="crm-filter-select" value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
            <option value="__all__">All Statuses</option>
            <option value="">New</option>
            {CRM_LEAD_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          {hasFilters && (
            <button className="crm-clear-filters" onClick={() => { setSearch(''); setFilterSales(''); setFilterPlatform(''); setFilterStatus('__all__'); }}>
              Clear filters
            </button>
          )}
        </div>
        <div className="crm-controls-right">
          <span className="crm-result-count">{filteredLeads.length} of {leads.length}</span>
          <div className="crm-view-toggle">
            <button className={`crm-vt-btn ${view === 'table' ? 'crm-vt-active' : ''}`} onClick={() => setView('table')} title="Table view">
              <CrmIcon name="table" size={16} />
            </button>
            <button className={`crm-vt-btn ${view === 'kanban' ? 'crm-vt-active' : ''}`} onClick={() => setView('kanban')} title="Board view">
              <CrmIcon name="board" size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="crm-content">
        {loading ? (
          <div className="crm-loading">Loading leads…</div>
        ) : view === 'table' ? (
          <CrmTable
            leads={filteredLeads}
            onUpdateLead={updateLead}
            onDeleteLead={deleteLead}
            sortBy={sortBy}
            onSort={handleSort}
          />
        ) : (
          <CrmKanban
            leads={filteredLeads}
            onUpdateLead={updateLead}
            onDeleteLead={deleteLead}
          />
        )}
      </div>

      {/* Footer */}
      <div className="crm-footer">
        <span>Data is stored in the Django database</span>
        <button className="crm-reset-btn" onClick={reloadData}>Reload data</button>
      </div>

      {/* Toast */}
      {toast && <CrmToast key={toast.key} message={toast.message} type={toast.type} onClose={() => setToast(null)} />}

      {/* Confirm Delete */}
      {confirmDel && (
        <ConfirmDialog
          message="Are you sure you want to delete this lead? This action cannot be undone."
          onConfirm={confirmDelete}
          onCancel={() => setConfirmDel(null)}
        />
      )}
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<CrmApp />);
