// CRM Kanban Board View

function CrmKanban({ leads, onUpdateLead, onDeleteLead }) {
  const [editingLead, setEditingLead] = React.useState(null);

  const columns = [
    { status: '', label: 'No status', color: '#94a3b8', bg: '#f8fafc' },
    ...CRM_LEAD_PROGRESS.map(s => ({ status: s, label: s, color: CRM_PROGRESS_CONFIG[s].dot, bg: CRM_PROGRESS_CONFIG[s].bg + '55' })),
  ];

  function getColumnLeads(status) {
    return leads.filter(l => (l.leadProgress || '') === status);
  }

  function handleStatusChange(leadId, newStatus) {
    onUpdateLead(leadId, { leadProgress: newStatus });
  }

  return (
    <div className="crm-kanban">
      {columns.map(col => {
        const colLeads = getColumnLeads(col.status);
        return (
          <div key={col.status} className="crm-kanban-col">
            <div className="crm-kanban-header">
              <div className="crm-kanban-header-left">
                <span className="crm-kanban-dot" style={{ background: col.color }}></span>
                <span className="crm-kanban-title">{col.label}</span>
              </div>
              <span className="crm-kanban-count">{colLeads.length}</span>
            </div>
            <div className="crm-kanban-body" style={{ background: col.bg }}>
              {colLeads.map(lead => (
                <div key={lead.id} className="crm-kanban-card" onClick={() => setEditingLead(lead)}>
                  <div className="crm-kc-top">
                    <span className="crm-kc-name">{lead.name || '(Unnamed)'}</span>
                  </div>
                  {lead.items && <div className="crm-kc-items"><ItemsCell text={lead.items} /></div>}
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
                    <select className="crm-kc-status-select" value={lead.leadProgress || ''}
                      onChange={e => handleStatusChange(lead.id, e.target.value)}>
                      <option value="">No status</option>
                      {CRM_LEAD_PROGRESS.map(s => <option key={s} value={s}>{s}</option>)}
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
