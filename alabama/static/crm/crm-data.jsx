// CRM Configuration and API Utilities

const CRM_SALESPEOPLE = ['RAFIQ', 'SIYAB', 'MUZAIN', 'AIJAZ', 'MUSHARAF'];
const CRM_PLATFORMS = ['Whatsapp', 'Email', 'Phone Call', 'Website'];
const CRM_LEAD_STATUSES = ['Approved', 'Rejected', 'Will Buy in Future', 'Price too high', 'Not required'];

const CRM_PRODUCTS = [
  'Ariston Boiler /Copper Pipes & Fittings',
  'ARISTON WATER HEATER 50LTR',
  'Ariston PRO1R 50L - 60 pcs/ 80L - 25 pcs',
  'Pipes and fittings enquiry',
  'Cosmoplast UPVC Elbo/ RR Socket/RR-Branch',
  'Pegler Pin 16 Threaded 4" Foot Valve',
  'UPVC pipes/ elbo/socket/ ariston water heater',
  'Lamborghini 100L Water Heater',
  'Automatic Flow Limiting Valve AFL Brand - Arrow Valves',
  'PPR Pipes & Fittings',
  'CPVC Pipes & Fittings',
  'Ball Valve',
  'Gate Valve',
  'Check Valve',
  'Pressure Reducing Valve',
  'Water Pump',
  'Solar Water Heater',
  'Copper Fittings',
  'Brass Fittings',
  'Pipe Insulation',
  'PVC Adhesive',
  'Pipe Clamps & Supports',
  'Storage Tank',
];

const CRM_STATUS_CONFIG = {
  '': { bg: '#f1f5f9', text: '#64748b', label: 'New', dot: '#94a3b8', kanbanBg: '#f8fafc' },
  'Approved': { bg: '#dcfce7', text: '#166534', label: 'Approved', dot: '#22c55e', kanbanBg: '#f0fdf4' },
  'Rejected': { bg: '#fee2e2', text: '#991b1b', label: 'Rejected', dot: '#ef4444', kanbanBg: '#fef2f2' },
  'Will Buy in Future': { bg: '#fef9c3', text: '#854d0e', label: 'Will Buy in Future', dot: '#eab308', kanbanBg: '#fefce8' },
  'Price too high': { bg: '#ede9fe', text: '#5b21b6', label: 'Price too high', dot: '#8b5cf6', kanbanBg: '#faf5ff' },
  'Not required': { bg: '#f3f4f6', text: '#4b5563', label: 'Not required', dot: '#6b7280', kanbanBg: '#f9fafb' },
};

function todayISO() { return new Date().toISOString().split('T')[0]; }

function formatDateDisplay(d) {
  if (!d) return '';
  const parts = d.split('-');
  if (parts.length !== 3) return d;
  return parts[1] + '/' + parts[2] + '/' + parts[0];
}

function getCsrfToken() {
  const name = 'csrftoken';
  const cookies = document.cookie.split(';');
  for (let c of cookies) {
    c = c.trim();
    if (c.startsWith(name + '=')) return decodeURIComponent(c.slice(name.length + 1));
  }
  return '';
}

// ── API functions ─────────────────────────────────────────────────────────────

async function getStoredLeads() {
  const res = await fetch('/api/leads/');
  if (!res.ok) throw new Error('Failed to fetch leads');
  return res.json();
}

async function createLead(data) {
  const res = await fetch('/api/leads/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to create lead');
  return res.json();
}

async function patchLead(id, updates) {
  const res = await fetch(`/api/leads/${id}/`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error('Failed to update lead');
  return res.json();
}

async function removeLead(id) {
  const res = await fetch(`/api/leads/${id}/`, {
    method: 'DELETE',
    headers: { 'X-CSRFToken': getCsrfToken() },
  });
  if (!res.ok) throw new Error('Failed to delete lead');
}

async function uploadFile(id, fileData) {
  // Convert base64 data URL to Blob for upload
  const arr = fileData.data.split(',');
  const mime = arr[0].match(/:(.*?);/)[1];
  const bstr = atob(arr[1]);
  let n = bstr.length;
  const u8arr = new Uint8Array(n);
  while (n--) u8arr[n] = bstr.charCodeAt(n);
  const blob = new Blob([u8arr], { type: mime });

  const form = new FormData();
  form.append('file', blob, fileData.name);

  const res = await fetch(`/api/leads/${id}/upload/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCsrfToken() },
    body: form,
  });
  if (!res.ok) throw new Error('File upload failed');
  return res.json(); // { name, data: url }
}

async function removeFile(id) {
  const res = await fetch(`/api/leads/${id}/upload/`, {
    method: 'DELETE',
    headers: { 'X-CSRFToken': getCsrfToken() },
  });
  if (!res.ok) throw new Error('Failed to remove file');
}

function exportToCSV(leads) {
  const headers = ['Date','Mobile No','Email ID','Name','Platform','Items','Sales Person','Quotation','Quotation File','Quotation Date','Follow Up 1 Date','Follow Up 1 Notes','Follow Up 2 Date','Follow Up 2 Notes','Lead Status'];
  const rows = leads.map(l => [
    l.date, l.mobileNo, l.emailId, l.name, l.platform, l.items, l.salesPerson,
    l.quotation || '',
    (l.quotationFile && l.quotationFile.name) ? l.quotationFile.name : '',
    l.quotationDate, l.followUp1Date, l.followUp1Notes,
    l.followUp2Date, l.followUp2Notes, l.leadStatus
  ].map(v => '"' + (v||'').replace(/"/g, '""') + '"').join(','));
  const csv = [headers.join(','), ...rows].join('\n');
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'leads_export_' + todayISO() + '.csv';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

Object.assign(window, {
  CRM_SALESPEOPLE, CRM_PLATFORMS, CRM_LEAD_STATUSES, CRM_PRODUCTS,
  CRM_STATUS_CONFIG, todayISO, formatDateDisplay, getCsrfToken,
  getStoredLeads, createLead, patchLead, removeLead, uploadFile, removeFile,
  exportToCSV,
});
