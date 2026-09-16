import * as pdfjsLib from '/static/vendor/pdfjs/pdf.mjs';
import { TextLayer } from '/static/vendor/pdfjs/pdf.mjs';
pdfjsLib.GlobalWorkerOptions.workerSrc = '/static/vendor/pdfjs/pdf.worker.mjs';

const shell = document.querySelector('.pdf-reader-shell');
if (!shell) throw new Error('PDF reader root missing');
const $ = (selector) => document.querySelector(selector);
const pdfUrl = shell.dataset.pdfUrl;
const progressUrl = shell.dataset.progressUrl;
const bookmarkUrl = shell.dataset.bookmarkUrl;
const annotationUrl = shell.dataset.annotationUrl;
const stage = $('#pdf-stage');
const pagesEl = $('#pdf-pages');
const pageLabel = $('#page-label');
const zoomLabel = $('#zoom-label');
const statusEl = $('#pdf-status');
const menu = $('#selection-menu');
let pdf = null;
let scale = 1;
let currentPage = 1;
let twoPage = localStorage.getItem('dana.pdf.twoPage') === '1';
let pageHeights = [];
let textCache = [];
let annotations = [];
let bookmarks = [];
let readingSeconds = Number(shell.dataset.readingSeconds || 0);
let saving = false;

try { annotations = JSON.parse(shell.dataset.annotations || '[]'); } catch { annotations = []; }
try { bookmarks = JSON.parse(shell.dataset.bookmarks || '[]').map(Number).filter(Number.isFinite); } catch { bookmarks = []; }

const csrf = () => decodeURIComponent((document.cookie.match(/(?:^|; )csrftoken=([^;]+)/) || [])[1] || '');
const clamp = (n, a, b) => Math.max(a, Math.min(b, n));
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const status = (text) => { statusEl.textContent = text; };
const post = async (url, data) => {
  const body = new URLSearchParams(data);
  const response = await fetch(url, {method: 'POST', headers: {'X-CSRFToken': csrf(), 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'}, body});
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
};

async function load() {
  status('در حال بارگذاری PDF…');
  pdf = await pdfjsLib.getDocument(pdfUrl).promise;
  pageLabel.textContent = `1 / ${pdf.numPages}`;
  pagesEl.innerHTML = '';
  pageHeights = [];
  textCache = [];
  for (let page = 1; page <= pdf.numPages; page += 1) await renderPage(page);
  applyLayout();
  await buildOutline();
  renderAnnotations();
  renderBookmarks();
  restorePosition();
  status('آماده مطالعه');
}

async function renderPage(num) {
  const page = await pdf.getPage(num);
  const viewport = page.getViewport({scale});
  pageHeights[num] = viewport.height;
  const wrap = document.createElement('section');
  wrap.className = 'pdf-page';
  wrap.dataset.page = num;
  wrap.id = `pdf-page-${num}`;
  wrap.style.width = `${viewport.width}px`;
  wrap.style.height = `${viewport.height}px`;
  const canvas = document.createElement('canvas');
  canvas.width = Math.ceil(viewport.width);
  canvas.height = Math.ceil(viewport.height);
  canvas.className = 'pdf-canvas';
  const textLayer = document.createElement('div');
  textLayer.className = 'textLayer';
  wrap.append(canvas, textLayer);
  pagesEl.appendChild(wrap);
  await page.render({canvasContext: canvas.getContext('2d'), viewport}).promise;
  const content = await page.getTextContent();
  textCache[num] = content.items.map(item => item.str).join(' ');
  try {
    const layer = new TextLayer({textContentSource: content, container: textLayer, viewport});
    await layer.render();
  } catch (error) { console.warn('Text layer unavailable', error); }
  wrap.addEventListener('click', () => setCurrentPage(num, false));
}

function applyLayout() {
  pagesEl.classList.toggle('two-page', twoPage);
  $('#toggle-two-page').classList.toggle('active', twoPage);
  localStorage.setItem('dana.pdf.twoPage', twoPage ? '1' : '0');
}

function setCurrentPage(page, scroll = true) {
  currentPage = clamp(Number(page) || 1, 1, pdf?.numPages || 1);
  pageLabel.textContent = `${currentPage} / ${pdf.numPages}`;
  $('#bookmark-page').classList.toggle('active', bookmarks.includes(currentPage));
  if (scroll) $('#pdf-page-' + currentPage)?.scrollIntoView({behavior: 'smooth', block: 'start'});
}

async function gotoPage(page) { setCurrentPage(page, true); }

function detectPage() {
  const pages = [...document.querySelectorAll('.pdf-page')];
  if (!pages.length) return;
  let best = currentPage;
  let distance = Infinity;
  const target = stage.scrollTop + stage.clientHeight * 0.35;
  for (const page of pages) {
    const d = Math.abs(page.offsetTop - target);
    if (d < distance) { distance = d; best = Number(page.dataset.page); }
  }
  if (best !== currentPage) setCurrentPage(best, false);
}

function renderAnnotations() {
  document.querySelectorAll('.pdf-annotation-mark').forEach(node => node.remove());
  for (const annotation of annotations) {
    for (const rect of annotation.rects || []) {
      const page = document.querySelector(`#pdf-page-${rect.page}`);
      if (!page) continue;
      const mark = document.createElement('button');
      mark.type = 'button';
      mark.className = `pdf-annotation-mark ${annotation.color || 'amber'}`;
      mark.style.left = `${rect.x * 100}%`;
      mark.style.top = `${rect.y * 100}%`;
      mark.style.width = `${rect.w * 100}%`;
      mark.style.height = `${rect.h * 100}%`;
      mark.title = annotation.note || annotation.selected_text || 'Annotation';
      mark.addEventListener('click', event => { event.stopPropagation(); showAnnotation(annotation); });
      page.appendChild(mark);
    }
  }
  renderAnnotationPanel();
}

function renderAnnotationPanel() {
  const box = $('#annotation-panel-list');
  if (!annotations.length) { box.innerHTML = '<p class="muted">هنوز یادداشتی ثبت نشده است.</p>'; return; }
  box.innerHTML = annotations.map(annotation => `
    <article class="pdf-note-card" data-id="${annotation.id}">
      <div class="pdf-note-meta"><span class="badge ${esc(annotation.color || 'amber')}">${annotation.kind === 'note' ? 'یادداشت' : 'هایلایت'}</span><button data-action="jump">صفحه ${annotation.page || 1}</button></div>
      <blockquote>${esc((annotation.selected_text || '').slice(0, 400))}</blockquote>
      <textarea data-field="note" placeholder="یادداشت پژوهشی…">${esc(annotation.note || '')}</textarea>
      <div class="pdf-note-actions"><button data-action="save">ذخیره</button><button data-action="delete" class="danger">حذف</button></div>
    </article>`).join('');
  box.querySelectorAll('.pdf-note-card').forEach(card => {
    const id = Number(card.dataset.id);
    const annotation = annotations.find(item => item.id === id);
    card.querySelector('[data-action="jump"]').onclick = () => showAnnotation(annotation);
    card.querySelector('[data-action="save"]').onclick = () => updateAnnotation(annotation, card.querySelector('[data-field="note"]').value);
    card.querySelector('[data-action="delete"]').onclick = () => deleteAnnotation(annotation);
  });
}

function renderBookmarks() {
  const box = $('#bookmark-panel-list');
  if (!bookmarks.length) { box.innerHTML = '<p class="muted">نشانکی ثبت نشده است.</p>'; return; }
  box.innerHTML = bookmarks.map(page => `<button class="pdf-bookmark-item" data-page="${page}">🔖 صفحه ${page}</button>`).join('');
  box.querySelectorAll('[data-page]').forEach(button => button.onclick = () => gotoPage(Number(button.dataset.page)));
}

function showAnnotation(annotation) { if (!annotation) return; setCurrentPage(annotation.page || 1, true); openTab('annotations'); }

async function updateAnnotation(annotation, note) {
  try {
    const data = await post(`/articles/annotation/${annotation.id}/update/`, {note});
    Object.assign(annotation, data);
    renderAnnotations();
    status('یادداشت ذخیره شد');
  } catch { status('ذخیره یادداشت ناموفق بود'); }
}

async function deleteAnnotation(annotation) {
  if (!confirm('این یادداشت حذف شود؟')) return;
  try {
    await post(`/articles/annotation/${annotation.id}/delete/`, {});
    annotations = annotations.filter(item => item.id !== annotation.id);
    renderAnnotations();
    status('یادداشت حذف شد');
  } catch { status('حذف ناموفق بود'); }
}

async function toggleBookmark() {
  try {
    const data = await post(bookmarkUrl, {page: currentPage});
    bookmarks = data.bookmarks || [];
    renderBookmarks();
    setCurrentPage(currentPage, false);
    status(data.active ? 'نشانک اضافه شد' : 'نشانک حذف شد');
  } catch { status('ذخیره نشانک ناموفق بود'); }
}

async function saveAnnotation(color = 'amber', note = '') {
  const selection = window.getSelection();
  const selectedText = selection?.toString().trim();
  if (!selectedText || !selection.rangeCount) return hideSelectionMenu();
  const range = selection.getRangeAt(0);
  const pageEl = range.commonAncestorContainer.nodeType === 1 ? range.commonAncestorContainer.closest?.('.pdf-page') : range.commonAncestorContainer.parentElement?.closest('.pdf-page');
  if (!pageEl) return hideSelectionMenu();
  const page = Number(pageEl.dataset.page);
  const pageText = textCache[page] || '';
  const index = pageText.indexOf(selectedText.slice(0, 120));
  const prefix = index > 0 ? pageText.slice(Math.max(0, index - 300), index) : '';
  const suffix = index >= 0 ? pageText.slice(index + selectedText.length, index + selectedText.length + 300) : '';
  const pageRect = pageEl.getBoundingClientRect();
  const rects = [];
  for (const rect of range.getClientRects()) {
    if (rect.width <= 0 || rect.height <= 0) continue;
    rects.push({page, x: clamp((rect.left - pageRect.left) / pageRect.width, 0, 1), y: clamp((rect.top - pageRect.top) / pageRect.height, 0, 1), w: clamp(rect.width / pageRect.width, 0, 1), h: clamp(rect.height / pageRect.height, 0, 1)});
  }
  try {
    const data = await post(annotationUrl, {selected_text: selectedText, kind: note ? 'note' : 'highlight', note, color, page, rects: JSON.stringify(rects), prefix, suffix});
    annotations.unshift({...data, color, page, rects, note, selected_text: selectedText});
    renderAnnotations();
    openTab('annotations');
    status(note ? 'یادداشت ذخیره شد' : 'هایلایت ذخیره شد');
  } catch { status('ثبت Annotation ناموفق بود'); }
  hideSelectionMenu();
  selection.removeAllRanges();
}

function showSelectionMenu(event) {
  const selected = window.getSelection()?.toString().trim();
  if (!selected) return hideSelectionMenu();
  menu.hidden = false;
  menu.style.left = `${Math.min(event.clientX, window.innerWidth - menu.offsetWidth - 12)}px`;
  menu.style.top = `${Math.max(8, event.clientY - 48)}px`;
}
function hideSelectionMenu() { menu.hidden = true; }

async function searchPdf() {
  const query = $('#pdf-search-input').value.trim().toLowerCase();
  if (!query) return;
  const page = textCache.findIndex((text, index) => index > 0 && text.toLowerCase().includes(query));
  if (page > 0) { await gotoPage(page); status(`نتیجه در صفحه ${page}`); } else status('نتیجه‌ای پیدا نشد');
}

async function buildOutline() {
  const box = $('#pdf-outline');
  box.innerHTML = '';
  const outline = await pdf.getOutline();
  if (!outline?.length) { box.innerHTML = '<p class="muted">فهرست داخلی PDF وجود ندارد.</p>'; return; }
  const render = (items, parent) => items.forEach(item => {
    const button = document.createElement('button');
    button.className = 'pdf-outline-item'; button.textContent = item.title;
    button.onclick = async () => { if (item.dest) { const target = await pdf.getDestination(item.dest); const ref = target?.[0]; if (ref) { const page = await pdf.getPageIndex(ref); gotoPage(page + 1); } } };
    parent.appendChild(button);
    if (item.items?.length) render(item.items, parent);
  });
  render(outline, box);
}

function restorePosition() {
  const position = Number(shell.dataset.lastPosition || 0);
  if (position > 0) stage.scrollTop = position;
}

async function saveProgress() {
  if (!pdf || saving) return;
  saving = true;
  readingSeconds += 15;
  const progress = Math.round((currentPage / pdf.numPages) * 100);
  try { await post(progressUrl, {progress, position: Math.round(stage.scrollTop), seconds: readingSeconds}); } catch { /* reader remains usable offline */ }
  saving = false;
}

function openTab(name) {
  document.querySelectorAll('.pdf-sidebar-tabs button').forEach(button => button.classList.toggle('active', button.dataset.tab === name));
  document.querySelectorAll('.pdf-sidebar-panel').forEach(panel => panel.classList.toggle('active', panel.id === `tab-${name}`));
}

function zoom(delta) {
  const old = scale;
  scale = clamp(Math.round((scale + delta) * 20) / 20, 0.5, 2.5);
  if (scale === old) return;
  const position = stage.scrollTop;
  status('در حال تغییر اندازه…');
  load().then(() => { stage.scrollTop = position; status('آماده مطالعه'); });
  zoomLabel.textContent = `${Math.round(scale * 100)}%`;
}

function fitPage() {
  const first = $('#pdf-page-1');
  if (!first) return;
  const width = stage.clientWidth - 48;
  const base = first.getBoundingClientRect().width / scale;
  if (base > 0) { scale = clamp(width / base, 0.5, 2.5); zoomLabel.textContent = `${Math.round(scale * 100)}%`; load().then(() => status('آماده مطالعه')); }
}

$('#prev-page').onclick = () => gotoPage(currentPage - 1);
$('#next-page').onclick = () => gotoPage(currentPage + 1);
$('#zoom-out').onclick = () => zoom(-0.1);
$('#zoom-in').onclick = () => zoom(0.1);
$('#fit-page').onclick = fitPage;
$('#toggle-two-page').onclick = () => { twoPage = !twoPage; applyLayout(); };
$('#bookmark-page').onclick = toggleBookmark;
$('#open-search').onclick = () => { const box = $('#pdf-search'); box.classList.toggle('open'); if (box.classList.contains('open')) $('#pdf-search-input').focus(); };
$('#pdf-search-btn').onclick = searchPdf;
$('#pdf-search-input').addEventListener('keydown', event => { if (event.key === 'Enter') searchPdf(); });
$('#btn-fullscreen').onclick = () => document.documentElement.requestFullscreen?.();

document.querySelectorAll('.pdf-sidebar-tabs button').forEach(button => button.onclick = () => openTab(button.dataset.tab));
menu.querySelectorAll('[data-color]').forEach(button => button.onclick = () => saveAnnotation(button.dataset.color));
$('#selection-note').onclick = () => { const note = prompt('یادداشت پژوهشی را وارد کنید:'); if (note !== null) saveAnnotation('amber', note); };
document.addEventListener('mouseup', event => setTimeout(() => showSelectionMenu(event), 0));
document.addEventListener('mousedown', event => { if (!menu.contains(event.target)) hideSelectionMenu(); });
stage.addEventListener('scroll', detectPage, {passive: true});
window.addEventListener('beforeunload', saveProgress);
setInterval(saveProgress, 15000);
document.addEventListener('keydown', event => {
  if (['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)) return;
  if (event.key === 'ArrowRight') gotoPage(currentPage - 1);
  if (event.key === 'ArrowLeft') gotoPage(currentPage + 1);
  if (event.key === '+') zoom(0.1);
  if (event.key === '-') zoom(-0.1);
  if (event.key.toLowerCase() === 'b') toggleBookmark();
  if (event.key === 'f') document.documentElement.requestFullscreen?.();
});

applyLayout();
load().catch(error => { console.error(error); status('بارگذاری PDF ناموفق بود'); });
