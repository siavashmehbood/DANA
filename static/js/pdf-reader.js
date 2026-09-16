import * as pdfjsLib from '/static/vendor/pdfjs/pdf.mjs';
import { TextLayer } from '/static/vendor/pdfjs/pdf.mjs';
pdfjsLib.GlobalWorkerOptions.workerSrc = '/static/vendor/pdfjs/pdf.worker.mjs';
const shell=document.querySelector('.pdf-reader-shell');
if(!shell) throw new Error('PDF reader root missing');
const pdfUrl=shell.dataset.pdfUrl, progressUrl=shell.dataset.progressUrl;
window.__DANA_LAST_POSITION=Number(shell.dataset.lastPosition||0);
let readingSeconds=Number(shell.dataset.readingSeconds||0);
const pagesEl=document.querySelector('#pdf-pages'), stage=document.querySelector('#pdf-stage');
const pageLabel=document.querySelector('#page-label'), zoomLabel=document.querySelector('#zoom-label');
const statusEl=document.querySelector('#pdf-status'), menu=document.querySelector('#selection-menu');
let pdf=null, scale=1, currentPage=1, pageHeights=[], textCache=[], annotations=[];
try{annotations=JSON.parse(shell.dataset.annotations||'[]')}catch{annotations=[]}
const csrf=()=>decodeURIComponent((document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)||[])[1]||'');
function status(t){statusEl.textContent=t}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function clamp(n,a,b){return Math.max(a,Math.min(b,n))}
async function load(){
  status('در حال بارگذاری PDF...'); pdf=await pdfjsLib.getDocument(pdfUrl).promise;
  pageLabel.textContent=`1 / ${pdf.numPages}`; pagesEl.innerHTML='';
  for(let n=1;n<=pdf.numPages;n++) await renderPage(n);
  await buildOutline(); renderAnnotations(); restorePosition(); status('آماده');
}
async function renderPage(num){
  const page=await pdf.getPage(num), viewport=page.getViewport({scale});
  pageHeights[num]=viewport.height;
  const wrap=document.createElement('section'); wrap.className='pdf-page'; wrap.dataset.page=num; wrap.id=`pdf-page-${num}`;
  wrap.style.width=`${viewport.width}px`; wrap.style.height=`${viewport.height}px`;
  const canvas=document.createElement('canvas'); canvas.width=Math.ceil(viewport.width); canvas.height=Math.ceil(viewport.height); canvas.className='pdf-canvas';
  wrap.appendChild(canvas); const textLayer=document.createElement('div'); textLayer.className='textLayer'; wrap.appendChild(textLayer); pagesEl.appendChild(wrap);
  const ctx=canvas.getContext('2d'); await page.render({canvasContext:ctx,viewport}).promise;
  const content=await page.getTextContent(); textCache[num]=content.items.map(x=>x.str).join(' ');
  try{const layer=new TextLayer({textContentSource:content,container:textLayer,viewport}); await layer.render()}catch(e){console.warn('text layer',e)}
  wrap.addEventListener('click',()=>{currentPage=num;pageLabel.textContent=`${num} / ${pdf.numPages}`});
}
async function rebuild(){const keep=stage.scrollTop; pagesEl.innerHTML=''; pageHeights=[]; await load(); stage.scrollTop=keep}
async function gotoPage(n){n=clamp(Number(n)||1,1,pdf.numPages); const el=document.querySelector(`#pdf-page-${n}`); if(el){stage.scrollTo({top:el.offsetTop-24,behavior:'smooth'});currentPage=n;pageLabel.textContent=`${n} / ${pdf.numPages}`}}
function renderAnnotations(){
  document.querySelectorAll('.pdf-annotation-mark').forEach(x=>x.remove());
  annotations.forEach(a=>{(a.rects||[]).forEach(r=>{const page=document.querySelector(`#pdf-page-${r.page}`);if(!page)return;const m=document.createElement('span');m.className=`pdf-annotation-mark ${a.color||'amber'}`;m.style.left=`${r.x*100}%`;m.style.top=`${r.y*100}%`;m.style.width=`${r.w*100}%`;m.style.height=`${r.h*100}%`;m.title=a.note||a.selected_text;m.dataset.id=a.id;m.onclick=e=>{e.stopPropagation();showAnnotation(a)};page.appendChild(m)})}); renderAnnotationPanel()}
function renderAnnotationPanel(){const box=document.querySelector('#annotation-panel-list');if(!annotations.length){box.innerHTML='<p class="muted">هنوز Annotationای ثبت نشده است.</p>';return}box.innerHTML=annotations.map(a=>`<article class="pdf-note-card"><div><span class="badge ${a.color||'amber'}">${a.kind==='note'?'یادداشت':'هایلایت'}</span><span class="muted">صفحه ${a.page||1}</span></div><blockquote>${esc((a.selected_text||'').slice(0,280))}</blockquote>${a.note?`<p>${esc(a.note)}</p>`:''}<button data-jump="${a.page||1}">رفتن به متن</button><button class="danger" data-delete="${a.id}">حذف</button></article>`).join('');box.querySelectorAll('[data-jump]').forEach(b=>b.onclick=()=>gotoPage(b.dataset.jump));box.querySelectorAll('[data-delete]').forEach(b=>b.onclick=()=>deleteAnnotation(b.dataset.delete))}
function showAnnotation(a){document.querySelector('[data-panel="annotations"]').click();gotoPage(a.page||1)}
async function deleteAnnotation(id){if(!confirm('این Annotation حذف شود؟'))return;const r=await fetch(`/articles/annotation/${id}/delete/`,{method:'POST',headers:{'X-CSRFToken':csrf()}});if(r.ok){annotations=annotations.filter(a=>String(a.id)!==String(id));renderAnnotations()}}
async function saveSelection(kind,color){const sel=window.getSelection();const text=sel?.toString().trim();if(!text)return;const rects=[];for(const rr of sel.getRangeAt(0).getClientRects()){const el=document.elementFromPoint(rr.left+1,rr.top+1)?.closest('.pdf-page');if(!el)continue;const pr=el.getBoundingClientRect();rects.push({page:Number(el.dataset.page),x:(rr.left-pr.left)/pr.width,y:(rr.top-pr.top)/pr.height,w:rr.width/pr.width,h:rr.height/pr.height})}if(!rects.length)return;let note='';if(kind==='note')note=prompt('یادداشت این بخش را وارد کنید:','')||'';const first=rects[0];const body=new URLSearchParams({selected_text:text,kind,color:color||'amber',note,page:first.page,rects:JSON.stringify(rects)});const r=await fetch(window.location.pathname.replace(/pdf\/$/,'annotate/'),{method:'POST',headers:{'X-CSRFToken':csrf()},body});const d=await r.json();if(d.ok){annotations.unshift({...d,page:first.page,color:color||'amber',rects,note});renderAnnotations();sel.removeAllRanges();menu.classList.remove('open');status('Annotation ذخیره شد')}}
async function buildOutline(){const outline=await pdf.getOutline();const box=document.querySelector('#pdf-outline');if(!outline?.length){box.innerHTML='<p class="muted">این PDF فهرست داخلی ندارد.</p>';return}box.innerHTML='';const walk=(items,depth=0)=>{items.forEach(i=>{const b=document.createElement('button');b.className='outline-item';b.style.paddingInlineStart=`${12+depth*14}px`;b.textContent=i.title;b.onclick=async()=>{if(i.dest){const dest=typeof i.dest==='string'?await pdf.getDestination(i.dest):i.dest;const ref=dest?.[0];if(ref){const p=await pdf.getPageIndex(ref);gotoPage(p+1)}}};box.appendChild(b);if(i.items)walk(i.items,depth+1)})};walk(outline)}
async function searchPdf(){const q=document.querySelector('#pdf-search').value.trim().toLowerCase();const box=document.querySelector('#search-results');if(!q){box.innerHTML='';return}const hits=[];for(let i=1;i<=pdf.numPages;i++){if((textCache[i]||'').toLowerCase().includes(q))hits.push(i)}box.innerHTML=hits.length?`<p>${hits.length} صفحه پیدا شد</p>`+hits.map(p=>`<button class="search-hit" data-page="${p}">صفحه ${p}</button>`).join(''):'<p class="muted">نتیجه‌ای پیدا نشد.</p>';box.querySelectorAll('[data-page]').forEach(b=>b.onclick=()=>gotoPage(b.dataset.page))}
function saveProgress(){if(!pdf)return;const max=Math.max(1,stage.scrollHeight-stage.clientHeight);const progress=Math.round(stage.scrollTop/max*100);readingSeconds+=15; const body=new URLSearchParams({progress:String(clamp(progress,0,100)),position:String(Math.round(stage.scrollTop)),seconds:String(readingSeconds)});fetch(progressUrl,{method:'POST',headers:{'X-CSRFToken':csrf(),'Content-Type':'application/x-www-form-urlencoded'},body,keepalive:true}).catch(()=>{})}
function restorePosition(){const saved=Number(window.__DANA_LAST_POSITION||0);if(saved>0)stage.scrollTop=saved}
function setup(){
  document.querySelectorAll('[data-action]').forEach(b=>b.onclick=async()=>{const a=b.dataset.action;if(a==='prev')gotoPage(currentPage-1);if(a==='next')gotoPage(currentPage+1);if(a==='zoom-in'){scale=clamp(scale+.15,.5,2.5);await rebuild();zoomLabel.textContent=`${Math.round(scale*100)}%`};if(a==='zoom-out'){scale=clamp(scale-.15,.5,2.5);await rebuild();zoomLabel.textContent=`${Math.round(scale*100)}%`};if(a==='fit'){const first=await pdf.getPage(1);scale=(stage.clientWidth-60)/first.getViewport({scale:1}).width;await rebuild();zoomLabel.textContent=`${Math.round(scale*100)}%`};if(a==='search'){document.querySelector('#pdf-search').focus()};if(a==='fullscreen'){document.querySelector('.pdf-reader-shell').requestFullscreen?.()}});
  document.querySelectorAll('.pdf-sidebar-tabs button').forEach(b=>b.onclick=()=>{document.querySelectorAll('.pdf-sidebar-tabs button,.pdf-panel').forEach(x=>x.classList.remove('active'));b.classList.add('active');document.querySelector(`#panel-${b.dataset.panel}`).classList.add('active')});
  document.querySelector('#pdf-search-btn').onclick=searchPdf;document.querySelector('#pdf-search').onkeydown=e=>{if(e.key==='Enter')searchPdf()};
  stage.addEventListener('scroll',()=>{let best=1,dist=Infinity;document.querySelectorAll('.pdf-page').forEach(p=>{const d=Math.abs(p.offsetTop-stage.scrollTop-30);if(d<dist){dist=d;best=Number(p.dataset.page)}});currentPage=best;pageLabel.textContent=`${best} / ${pdf.numPages}`});
  setInterval(saveProgress,15000);window.addEventListener('beforeunload',saveProgress);
  document.addEventListener('mouseup',e=>{const text=window.getSelection()?.toString().trim();if(!text||!document.querySelector('.textLayer'))return;menu.style.left=`${e.pageX}px`;menu.style.top=`${e.pageY}px`;menu.classList.add('open')});
  menu.querySelectorAll('button').forEach(b=>b.onclick=()=>saveSelection(b.dataset.kind,b.dataset.color));document.addEventListener('mousedown',e=>{if(!menu.contains(e.target))menu.classList.remove('open')});
}
setup();load().catch(e=>{console.error(e);pagesEl.innerHTML='<div class="pdf-error">بارگذاری PDF انجام نشد. فایل یا دسترسی آن را بررسی کنید.</div>';status('خطا در PDF')});
