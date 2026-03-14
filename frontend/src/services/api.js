const BASE = 'http://127.0.0.1:8000/api/v1';

// ─── Base request ─────────────────────────────────────────────────────────────
async function request(method, path, body) {
  const token = localStorage.getItem('access_token');
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) {
    localStorage.clear();
    window.location.replace('/login');
    return;
  }

  if (res.status === 204) return null;

  const data = await res.json();
  if (!res.ok) throw data;
  return data;
}

const get    = (path, params) => request('GET',    path + (params ? '?' + new URLSearchParams(params) : ''));
const post   = (path, body)   => request('POST',   path, body);
const put    = (path, body)   => request('PUT',    path, body);
const patch  = (path, body)   => request('PATCH',  path, body);
const del    = (path)         => request('DELETE', path);

// ─── File download helper ─────────────────────────────────────────────────────
function download(path, filename) {
  const token = localStorage.getItem('access_token');
  const sep   = path.includes('?') ? '&' : '?';
  const url   = `${BASE}${path}${sep}token=${encodeURIComponent(token)}`;
  const a     = document.createElement('a');
  a.href      = url;
  a.download  = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => a.remove(), 100);
}



// ─── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  login:  (data) => post('/accounts/auth/login/', data),
  logout: ()     => post('/accounts/auth/logout/'),
};

// ─── Users ────────────────────────────────────────────────────────────────────
export const usersApi = {
  list:       (p)     => get('/accounts/users/', p),
  retrieve:   (id)    => get(`/accounts/users/${id}/`),
  create:     (data)  => post('/accounts/users/', data),
  update:     (id, d) => patch(`/accounts/users/${id}/`, d),
  activate:   (id)    => post(`/accounts/users/${id}/activate/`),
  deactivate: (id)    => post(`/accounts/users/${id}/deactivate/`),
  resetPw:    (id, d) => post(`/accounts/users/${id}/reset_password/`, d),
  me:         ()      => get('/accounts/users/me/'),
  delete:     (id)    => del(`/accounts/users/${id}/`),
};

// ─── Equipment Categories ─────────────────────────────────────────────────────
export const categoriesApi = {
  list:   (p)     => get('/equipment/equipment-categories/', p),
  create: (data)  => post('/equipment/equipment-categories/', data),
  update: (id, d) => put(`/equipment/equipment-categories/${id}/`, d),
  delete: (id)    => del(`/equipment/equipment-categories/${id}/`),
};

// ─── Equipment Statuses ───────────────────────────────────────────────────────
export const statusesApi = {
  list:   (p)     => get('/equipment/equipment-statuses/', p),
  create: (data)  => post('/equipment/equipment-statuses/', data),
  update: (id, d) => put(`/equipment/equipment-statuses/${id}/`, d),
  delete: (id)    => del(`/equipment/equipment-statuses/${id}/`),
};

// ─── Brands ───────────────────────────────────────────────────────────────────
export const brandsApi = {
  list:   (p)     => get('/equipment/brands/', p),
  create: (data)  => post('/equipment/brands/', data),
  update: (id, d) => put(`/equipment/brands/${id}/`, d),
  delete: (id)    => del(`/equipment/brands/${id}/`),
};

// ─── Region Offices (HQs) ────────────────────────────────────────────────────
export const regionOfficesApi = {
  list:   (p)     => get('/equipment/region-offices/', p),
  create: (data)  => post('/equipment/region-offices/', data),
  update: (id, d) => put(`/equipment/region-offices/${id}/`, d),
  delete: (id)    => del(`/equipment/region-offices/${id}/`),
};

// ─── Regions ──────────────────────────────────────────────────────────────────
export const regionsApi = {
  list:   (p)     => get('/equipment/regions/', p),
  create: (data)  => post('/equipment/regions/', data),
  update: (id, d) => put(`/equipment/regions/${id}/`, d),
  delete: (id)    => del(`/equipment/regions/${id}/`),
};

// ─── DPU Offices (HQs) ───────────────────────────────────────────────────────
export const dpuOfficesApi = {
  list:   (p)     => get('/equipment/dpu-offices/', p),
  create: (data)  => post('/equipment/dpu-offices/', data),
  update: (id, d) => put(`/equipment/dpu-offices/${id}/`, d),
  delete: (id)    => del(`/equipment/dpu-offices/${id}/`),
};

// ─── DPUs ─────────────────────────────────────────────────────────────────────
export const dpusApi = {
  list:   (p)     => get('/equipment/dpus/', p),
  create: (data)  => post('/equipment/dpus/', data),
  update: (id, d) => put(`/equipment/dpus/${id}/`, d),
  delete: (id)    => del(`/equipment/dpus/${id}/`),
};

// ─── Stations ─────────────────────────────────────────────────────────────────
export const stationsApi = {
  list:   (p)     => get('/equipment/stations/', p),
  create: (data)  => post('/equipment/stations/', data),
  update: (id, d) => put(`/equipment/stations/${id}/`, d),
  delete: (id)    => del(`/equipment/stations/${id}/`),
};

// ─── Units ────────────────────────────────────────────────────────────────────
export const unitsApi = {
  list:   (p)     => get('/equipment/units/', p),
  create: (data)  => post('/equipment/units/', data),
  update: (id, d) => put(`/equipment/units/${id}/`, d),
  delete: (id)    => del(`/equipment/units/${id}/`),
};

// ─── Directorates ─────────────────────────────────────────────────────────────
export const directoratesApi = {
  list:   (p)     => get('/equipment/directorates/', p),
  create: (data)  => post('/equipment/directorates/', data),
  update: (id, d) => put(`/equipment/directorates/${id}/`, d),
  delete: (id)    => del(`/equipment/directorates/${id}/`),
};

// ─── Departments ──────────────────────────────────────────────────────────────
export const departmentsApi = {
  list:   (p)     => get('/equipment/departments/', p),
  create: (data)  => post('/equipment/departments/', data),
  update: (id, d) => put(`/equipment/departments/${id}/`, d),
  delete: (id)    => del(`/equipment/departments/${id}/`),
};

// ─── Offices ──────────────────────────────────────────────────────────────────
export const officesApi = {
  list:   (p)     => get('/equipment/offices/', p),
  create: (data)  => post('/equipment/offices/', data),
  update: (id, d) => put(`/equipment/offices/${id}/`, d),
  delete: (id)    => del(`/equipment/offices/${id}/`),
};

// ─── Equipment (unified single endpoint) ─────────────────────────────────────
export const equipmentApi = {
  list:    (p)     => get('/equipment/equipment/', p),
  retrieve:(id)    => get(`/equipment/equipment/${id}/`),
  create:  (data)  => post('/equipment/equipment/', data),
  update:  (id, d) => put(`/equipment/equipment/${id}/`, d),
  patch:   (id, d) => patch(`/equipment/equipment/${id}/`, d),
  delete:  (id)    => del(`/equipment/equipment/${id}/`),
};

// ─── Stock ────────────────────────────────────────────────────────────────────
export const stockApi = {
  list:    (p)     => get('/equipment/stock/', p),
  retrieve:(id)    => get(`/equipment/stock/${id}/`),
  create:  (data)  => post('/equipment/stock/', data),
  update:  (id, d) => put(`/equipment/stock/${id}/`, d),
  delete:  (id)    => del(`/equipment/stock/${id}/`),
};

// ─── Deployments ──────────────────────────────────────────────────────────────
export const deploymentsApi = {
  list:    (p)     => get('/equipment/deployments/', p),
  retrieve:(id)    => get(`/equipment/deployments/${id}/`),
  create:  (data)  => post('/equipment/deployments/', data),
  update:  (id, d) => put(`/equipment/deployments/${id}/`, d),
  patch:   (id, d) => patch(`/equipment/deployments/${id}/`, d),
  delete:  (id)    => del(`/equipment/deployments/${id}/`),
};

// ─── Maintenance ──────────────────────────────────────────────────────────────
export const maintenanceApi = {
  // Maintenance requests (user-submitted)
  requests: {
    list:       (p)     => get('/maintenance/requests/', p),
    myRequests: (p)     => get('/maintenance/requests/my_requests/', p),
    pending:    ()      => get('/maintenance/requests/pending/'),
    create:     (data)  => post('/maintenance/requests/', data),
    update:     (id, d) => patch(`/maintenance/requests/${id}/`, d),
    updateStatus: (id,d) => post(`/maintenance/requests/${id}/update_status/`, d),
    delete:     (id)    => del(`/maintenance/requests/${id}/`),
  },
  // Notifications
  notifications: {
    list:        (p)  => get('/maintenance/notifications/', p),
    markRead:    (id) => post(`/maintenance/notifications/${id}/mark_read/`),
    markAllRead: ()   => post('/maintenance/notifications/mark_all_read/'),
    unreadCount: ()   => get('/maintenance/notifications/unread_count/'),
  },
};

// ─── Convenience re-exports ───────────────────────────────────────────────────
export const settingsApi = {
  brands:       brandsApi,
  regions:      regionsApi,
  dpus:         dpusApi,
  stations:     stationsApi,
  units:        unitsApi,
  categories:   categoriesApi,
  statuses:     statusesApi,
  directorates: directoratesApi,
  departments:  departmentsApi,
  offices:      officesApi,
};

// ─── Reports ──────────────────────────────────────────────────────────────────
const date = () => new Date().toISOString().slice(0, 10).replace(/-/g, '');
export const reportsApi = {
  excelAll:      () => download('/equipment/reports/excel/',  `equipment_report_${date()}.xlsx`),
  pdfAll:        () => download('/equipment/reports/pdf/',    `equipment_report_${date()}.pdf`),
  excelByType:   (type) => download(`/equipment/reports/excel/${encodeURIComponent(type)}/`, `${type.replace(/ /g,'_').toLowerCase()}_${date()}.xlsx`),
  pdfByType:     (type) => download(`/equipment/reports/pdf/${encodeURIComponent(type)}/`,   `${type.replace(/ /g,'_').toLowerCase()}_${date()}.pdf`),
  // Stock exports
  stockExcelAll:    () => download('/equipment/reports/stock/excel/',  `stock_report_${date()}.xlsx`),
  stockPdfAll:      () => download('/equipment/reports/stock/pdf/',    `stock_report_${date()}.pdf`),
  stockExcelByType: (type) => download(`/equipment/reports/stock/excel/${encodeURIComponent(type)}/`, `stock_${type.replace(/ /g,'_').toLowerCase()}_${date()}.xlsx`),
  stockPdfByType:   (type) => download(`/equipment/reports/stock/pdf/${encodeURIComponent(type)}/`,   `stock_${type.replace(/ /g,'_').toLowerCase()}_${date()}.pdf`),
  // Unit-based exports
  unitExcelAll:   ()             => download('/equipment/reports/unit/excel/',     `units_all_${date()}.xlsx`),
  unitPdfAll:     ()             => download('/equipment/reports/unit/pdf/',       `units_all_${date()}.pdf`),
  unitExcelById:  (id, name)     => download(`/equipment/reports/unit/excel/${id}/`, `unit_${(name||'report').replace(/ /g,'_').toLowerCase()}_${date()}.xlsx`),
  unitPdfById:    (id, name)     => download(`/equipment/reports/unit/pdf/${id}/`,   `unit_${(name||'report').replace(/ /g,'_').toLowerCase()}_${date()}.pdf`),

  // Region-based exports
  regionExcelAll:   ()             => download('/equipment/reports/region/excel/',     `regions_all_${date()}.xlsx`),
  regionPdfAll:     ()             => download('/equipment/reports/region/pdf/',       `regions_all_${date()}.pdf`),
  regionExcelById:  (id, name)     => download(`/equipment/reports/region/excel/${id}/`, `region_${(name||'report').replace(/ /g,'_').toLowerCase()}_${date()}.xlsx`),
  regionPdfById:    (id, name)     => download(`/equipment/reports/region/pdf/${id}/`,   `region_${(name||'report').replace(/ /g,'_').toLowerCase()}_${date()}.pdf`),

  // DPU-based exports
  dpuExcelAll:   ()             => download('/equipment/reports/dpu/excel/',     `dpus_all_${date()}.xlsx`),
  dpuPdfAll:     ()             => download('/equipment/reports/dpu/pdf/',       `dpus_all_${date()}.pdf`),
  dpuExcelById:  (id, name)     => download(`/equipment/reports/dpu/excel/${id}/`, `dpu_${(name||'report').replace(/ /g,'_').toLowerCase()}_${date()}.xlsx`),
  dpuPdfById:    (id, name)     => download(`/equipment/reports/dpu/pdf/${id}/`,   `dpu_${(name||'report').replace(/ /g,'_').toLowerCase()}_${date()}.pdf`),


  // Aggregated counts — single call for entire Reports page
  counts: () => get('/equipment/reports/counts/'),






};
