// CRM Kanban Board View

function CrmKanban({ leads, onUpdateLead, onDeleteLead }) {
  const [editingLead, setEditingLead] = React.useState(null);

  const columns = [
    { status: '', label: 'New', color: '#94a3b8' },
    { status: 'Approved', label: 'Approved', color: '#22c55e' },
    { status: 'Rejected', label: 'Rejected', color: '#ef4444' },
    { status: 'Will Buy in Future', label: 'Will Buy in Future', color: '#eab308' },
    { status: 'Price too high', label: 'Price too high', color: '#8b5cf6' },
    { status: 'Not required', label: 'Not required', color: '#6b7280' },
  ];

  function getColumnLeads(status) {
    return leads.filter(l => (l.leadStatus || '') === status);
  }

  function handleStatusChange(leadId, newStatus) {
    onUpdateLead(leadId, { leadStatus: newStatus });
  }

  return (
    <div className="crm-kanban">
      {columns.map(col => {
        const colLeads = getColumnLeads(col.status);
        const cfg = CRM_STATUS_CONFIG[col.status] || CRM_STATUS_CONFIG[''];
        return (
          <div key={col.status} className="crm-kanban-col">
            <div className="crm-kanban-header">
              <div className="crm-kanban-header-left">
                <span className="crm-kanban-dot" style={{ background: col.color }}></span>
                <span className="crm-kanban-title">{col.label}</span>
              </div>
              <span className="crm-kanban-count">{colLeads.length}</span>
            </div>
            <div className="crm-kanban-body" style={{ background: cfg.kanbanBg }}>
              {colLeads.map(lead => (
                <div key={lead.id} className="crm-kanban-card" onClick={() => setEditingLead(lead)}>
                  <div className="crm-kc-top">
                    <span className="crm-kc-name">{lead.name || '(Unnamed)'}</span>
                  </div>
                  {lead.items && <div className="crm-kc-items">{lead.items}</div>}
                  <div className="crm-kc-meta">
                    {lead.salesPerson && (
                      <span className="crm-kc-chip crm-kc-chip-sales">
                        <CrmIcon name="users" size={11} />
                        {lead.salesPerson}
                      </span>
                    )}
                    {lead.platform && (
                      <span className="crm-kc-chip">
                        {lead.platform}
                      </span>
                    )}
                  </div>
                  <div className="crm-kc-bottom">
                    <span className="crm-kc-date">
                      <CrmIcon name="calendar" size={11} />
                      {formatDateDisplay(lead.date)}
                    </span>
                    {lead.quotation && <span className="crm-kc-quote">{lead.quotation}</span>}
                  </div>
                  {(lead.followUp1Date || lead.followUp1Notes) && (
                    <div className="crm-kc-fu">
                      <CrmIcon name="clock" size={11} />
                      <span>
                        {lead.followUp1Date ? formatDateDisplay(lead.followUp1Date) : ''}
                        {lead.followUp1Notes ? (lead.followUp1Date ? ' · ' : '') + lead.followUp1Notes : ''}
                      </span>
                    </div>
                  )}
                  <div className="crm-kc-status-row" onClick={e => e.stopPropagation()}>
                    <select className="crm-kc-status-select" value={lead.leadStatus || ''}
                      onChange={e => handleStatusChange(lead.id, e.target.value)}>
                      <option value="">New</option>
                      {CRM_LEAD_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                </div>
              ))}
              {colLeads.length === 0 && (
                <div className="crm-kanban-empty">No leads</div>
              )}
            </div>
          </div>
        );
      })}
      {editingLead && (
        <LeadDetailModal
          lead={editingLead}
          onUpdate={updated => { onUpdateLead(updated.id, updated); setEditingLead(null); }}
          onClose={() => setEditingLead(null)}
        />
      )}
    </div>
  );
}

Object.assign(window, { CrmKanban });
