// ─── STATE ───────────────────────────────────
let files = [];
let lastResult = null;
const API_URL = 'http://127.0.0.1:8000';
const REQUEST_TIMEOUT_MS = 180000;

// ─── TAB SWITCHING ───────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  event.target.classList.add('active');
}

// ─── FILE HANDLING ───────────────────────────
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const fileList = document.getElementById('fileList');

dropzone.addEventListener('dragover', e => {
  e.preventDefault();
  dropzone.classList.add('drag-over');
});

dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));

dropzone.addEventListener('drop', e => {
  e.preventDefault();
  dropzone.classList.remove('drag-over');
  addFiles(Array.from(e.dataTransfer.files));
});

fileInput.addEventListener('change', () => {
  addFiles(Array.from(fileInput.files));
  fileInput.value = '';
});

function addFiles(newFiles) {
  const allowed = ['pdf','xls','xlsx','xlsm','csv','jpg','jpeg','png','webp'];
  newFiles.forEach(f => {
    const ext = f.name.split('.').pop().toLowerCase();
    if (!allowed.includes(ext)) {
      alert(`Formato no soportado: .${ext}`);
      return;
    }
    if (f.size > 50 * 1024 * 1024) {
      alert(`Archivo muy grande: ${f.name}`);
      return;
    }
    if (!files.find(x => x.name === f.name && x.size === f.size)) {
      files.push(f);
    }
  });
  renderFileList();
  updateButtons();
}

function getIcon(name) {
  const ext = name.split('.').pop().toLowerCase();
  const map = { pdf:'📄', xls:'📊', xlsx:'📊', xlsm:'📊', csv:'📋',
    jpg:'🖼️', jpeg:'🖼️', png:'🖼️', webp:'🖼️' };
  return map[ext] || '📁';
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + 'B';
  if (bytes < 1024*1024) return (bytes/1024).toFixed(1) + 'KB';
  return (bytes/1024/1024).toFixed(1) + 'MB';
}

function renderFileList() {
  fileList.innerHTML = files.map((f, i) => `
    <div class="file-item">
      <span class="file-icon">${getIcon(f.name)}</span>
      <span class="file-name">${f.name}</span>
      <span class="file-size">${formatSize(f.size)}</span>
      <button class="remove-btn" onclick="removeFile(${i})">×</button>
    </div>
  `).join('');
}

function removeFile(i) {
  files.splice(i, 1);
  renderFileList();
  updateButtons();
}

function updateButtons() {
  const has = files.length > 0;
  document.getElementById('btnExtract').disabled = !has;
}

function clearAll() {
  files = [];
  lastResult = null;
  renderFileList();
  updateButtons();
  document.getElementById('progressSection').classList.remove('visible');
  document.getElementById('progressLog').innerHTML = '';
  document.getElementById('btnDownload').disabled = true;
  resetAgentChips();
  document.getElementById('resultsSection').classList.remove('visible');
  document.getElementById('resultsEmpty').style.display = 'block';
}

// ─── AGENT CHIPS ─────────────────────────────
function setAgent(id, state) {
  const chip = document.getElementById('chip-' + id);
  chip.className = 'agent-chip ' + state;
}

function resetAgentChips() {
  ['orchestrator','extractor','transformer','verifier'].forEach(id => setAgent(id, ''));
}

// ─── PROGRESS ────────────────────────────────
function setProgress(pct, label) {
  document.getElementById('progressBarFill').style.width = pct + '%';
  document.getElementById('progressStatus').textContent = label;
}

// ─── PROGRESS LOG ────────────────────────────
function addLog(step, status, detail) {
  const log = document.getElementById('progressLog');
  const time = new Date().toLocaleTimeString('es-AR', {hour12:false});
  const div = document.createElement('div');
  div.className = `log-entry ${status}`;
  div.innerHTML = `
    <span class="log-time">${time}</span>
    <span class="log-step">[${step.toUpperCase()}]</span>
    <span class="log-msg">${detail} ${status === 'running' ? '<span class="spinner"></span>' : status === 'done' ? '✓' : '✗'}</span>
  `;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

// ─── EXTRACTION ──────────────────────────────
async function startExtraction() {
  if (files.length === 0) return;

  const cuit = document.getElementById('supplierCuit').value.trim();
  const btn = document.getElementById('btnExtract');

  btn.disabled = true;
  btn.textContent = '⏳ Procesando...';
  document.getElementById('progressSection').classList.add('visible');
  document.getElementById('progressLog').innerHTML = '';

  resetAgentChips();
  setAgent('orchestrator', 'active');
  setProgress(5, 'Iniciando extracción...');
  addLog('orquestador', 'running', `Iniciando con ${files.length} archivo(s)...`);

  let allRows = [];
  let lastReport = null;

  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    addLog('extractor', 'running', `Extrayendo: ${file.name}`);
    setAgent('extractor', 'active');
    setProgress(10 + (i / files.length * 20), `Extrayendo ${file.name}...`);

    const formData = new FormData();
    formData.append('file', file);
    if (cuit) formData.append('supplier_cuit', cuit);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
      const resp = await fetch(`${API_URL}/extract`, {
        method: 'POST',
        body: formData,
        signal: controller.signal
      }).finally(() => clearTimeout(timeoutId));

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({detail: resp.statusText}));
        throw new Error(err.detail || resp.statusText);
      }

      const data = await resp.json();
      setAgent('extractor', 'done');
      
      // Determine extraction method from file type
      const ext = file.name.split('.').pop().toLowerCase();
      let method = 'IA completa';
      if (['csv','xlsx','xls','xlsm'].includes(ext)) method = 'Directo + IA';
      else if (['jpg','jpeg','png','webp'].includes(ext)) method = 'Vision AI';
      
      addLog('extractor', 'done', `${data.metadata?.pages || 1} página(s) — método: ${method}`);
      setProgress(40 + (i / files.length * 20), 'Transformando datos...');

      setAgent('transformer', 'active');
      addLog('transformador', 'running', `Mapeando ${data.rows?.length || 0} productos...`);
      setAgent('transformer', 'done');
      addLog('transformador', 'done', `${data.rows?.length || 0} filas extraídas`);
      setProgress(70 + (i / files.length * 15), 'Verificando calidad...');

      setAgent('verifier', 'active');
      addLog('verificador', 'running', 'Validando datos...');
      setAgent('verifier', 'done');
      addLog('verificador', 'done',
        `Calidad: ${data.report?.quality_score}% — ${data.report?.valid_rows}/${data.report?.total_rows} válidas`);
      setProgress(90, 'Finalizando...');

      allRows = allRows.concat(data.rows || []);
      lastReport = data.report;
      lastResult = data;

    } catch (err) {
      setAgent('extractor', 'error');
      const msg = err?.name === 'AbortError'
        ? `Timeout de ${Math.round(REQUEST_TIMEOUT_MS / 1000)}s en ${file.name}`
        : `Error en ${file.name}: ${err.message}`;
      addLog('error', 'error', msg);
    }
  }

  setAgent('orchestrator', 'done');
  setProgress(100, `✓ Completado — ${allRows.length} productos extraídos`);
  addLog('orquestador', 'done', `Completado. Total: ${allRows.length} productos.`);

  if (allRows.length > 0) {
    lastResult = { ...lastResult, rows: allRows };
    renderResults(allRows, lastReport);
    renderMapping(lastResult.column_mapping || {});
    document.getElementById('btnDownload').disabled = false;
    // Switch to results tab
    document.querySelectorAll('.tab').forEach((t,i) => {
      t.classList.toggle('active', i === 1);
    });
    document.querySelectorAll('.tab-panel').forEach((p,i) => {
      p.classList.toggle('active', i === 1);
    });
  }

  btn.disabled = false;
  btn.textContent = '🤖 Extraer con IA';
}

// ─── RENDER RESULTS ──────────────────────────
function renderResults(rows, report) {
  document.getElementById('resultsEmpty').style.display = 'none';
  document.getElementById('resultsSection').classList.add('visible');

  // Stats
  document.getElementById('statRows').textContent = rows.length;
  document.getElementById('statQuality').textContent = (report?.quality_score || 0) + '%';
  document.getElementById('statValid').textContent = report?.valid_rows || rows.length;
  document.getElementById('statIssues').textContent = report?.rows_with_issues || 0;
  document.getElementById('qualityFill').style.width = (report?.quality_score || 100) + '%';

  // Extraction method
  if (files.length > 0) {
    const ext = files[0].name.split('.').pop().toLowerCase();
    let methodLabel = 'IA completa';
    if (['csv','xlsx','xls','xlsm'].includes(ext)) methodLabel = 'Directo + IA';
    else if (['jpg','jpeg','png','webp'].includes(ext)) methodLabel = 'Vision AI';
    document.getElementById('statMethod').textContent = methodLabel;
  }

  // Table
  const tbody = document.getElementById('resultsBody');
  tbody.innerHTML = rows.slice(0, 200).map((r, i) => `
    <tr>
      <td style="color:var(--muted)">${i + 1}</td>
      <td class="code-cell">${esc(r['Cód. Artículo'])}</td>
      <td title="${esc(r['Descripción artículo'])}">${esc(r['Descripción artículo']).slice(0,40)}</td>
      <td title="${esc(r['Descripción adicional artículo'])}">${esc(r['Descripción adicional artículo']).slice(0,30)}</td>
      <td class="currency-cell">${esc(r['Moneda'])}</td>
      <td>${esc(r['Unidad'])}</td>
      <td class="price-cell">${esc(r['Precio'])}</td>
      <td>${esc(r['Bonif.'])}</td>
      <td>${esc(r['Cód. Lista'])}</td>
      <td>${esc(r['Fecha vigencia desde'])}</td>
      <td>${esc(r['Fecha vigencia hasta'])}</td>
    </tr>
  `).join('');

  if (rows.length > 200) {
    tbody.innerHTML += `<tr><td colspan="11" style="text-align:center;color:var(--muted);padding:12px">
      ... y ${rows.length - 200} filas más (descargá el XLSX para verlas todas)
    </td></tr>`;
  }

  // Issues
  const issues = report?.issues || [];
  if (issues.length > 0) {
    document.getElementById('issuesPanel').classList.add('visible');
    document.getElementById('issuesList').innerHTML = issues.slice(0, 10).map(iss =>
      `<div class="issue-row">Fila ${iss.row}: <span>${iss.issues.join(', ')}</span></div>`
    ).join('');
  } else {
    document.getElementById('issuesPanel').classList.remove('visible');
  }
}

function esc(v) {
  if (v === null || v === undefined) return '';
  return String(v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ─── DOWNLOAD ────────────────────────────────
async function downloadFile(format) {
  if (!files.length) return;
  const cuit = document.getElementById('supplierCuit').value.trim();
  const file = files[0];

  const formData = new FormData();
  formData.append('file', file);
  if (cuit) formData.append('supplier_cuit', cuit);
  formData.append('format', format);

  try {
    const resp = await fetch(`${API_URL}/extract/download?format=${format}`, {
      method: 'POST',
      body: formData
    });

    if (!resp.ok) throw new Error(await resp.text());

    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const cd = resp.headers.get('content-disposition') || '';
    const match = cd.match(/filename=(.+)/);
    a.download = match ? match[1] : `precios_extraidos.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert('Error al descargar: ' + err.message);
  }
}

// ─── COPY JSON ───────────────────────────────
function copyJson() {
  if (!lastResult) return;
  navigator.clipboard.writeText(JSON.stringify(lastResult.rows, null, 2))
    .then(() => alert('JSON copiado al portapapeles'))
    .catch(() => alert('No se pudo copiar'));
}

// ─── COLUMN MAPPING ──────────────────────────
function renderMapping(mapping) {
  const panel = document.getElementById('mappingPanel');
  const grid = document.getElementById('mappingGrid');
  if (!mapping || Object.keys(mapping).length === 0) {
    panel.classList.remove('visible');
    return;
  }
  panel.classList.add('visible');
  grid.innerHTML = Object.entries(mapping).map(([src, dest]) => `
    <div class="mapping-row">
      <span class="mapping-src">${esc(src)}</span>
      <span class="mapping-arrow">→</span>
      <span class="mapping-dest">${esc(dest)}</span>
    </div>
  `).join('');
}
