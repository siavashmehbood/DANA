/* DANA Reader v30 — real paginated columns */
(function(){
  'use strict';
  function init(){
    const root=document.querySelector('[data-paged-reader]');
    if(!root||root.dataset.readerReady==='30') return;
    root.dataset.readerReady='30';
    const columns=[...root.querySelectorAll('.reader-column')];
    const prev=document.querySelector('[data-reader-prev]');
    const next=document.querySelector('[data-reader-next]');
    const label=document.querySelector('[data-reader-page]');
    const shell=root.closest('.reader-shell');
    const key='dana-reader:'+location.pathname;
    let groups=[],total=1,current=0;
    function unwrapLegacy(){
      root.querySelectorAll('.reader-flow').forEach(w=>{const p=w.parentNode;while(w.firstChild)p.insertBefore(w.firstChild,w);w.remove()});
    }
    function measure(){
      groups=columns.map((column,i)=>{const text=column.querySelector('.article-text');
        if(!text) return {column,text:null,pages:1};
        text.scrollLeft=0;
        const pages=Math.max(1,Math.ceil((text.scrollWidth+2)/Math.max(1,text.clientWidth)));
        return {column,text,pages};
      });
      total=Math.max(1,groups.reduce((n,g)=>n+g.pages,0));
      const saved=Math.max(0,Math.min(total-1,parseInt(localStorage.getItem(key)||'0',10)||0));
      current=saved;
      render(false);
    }
    function locate(index){
      let n=index;
      for(let i=0;i<groups.length;i++){if(n<groups[i].pages)return {group:i,page:n};n-=groups[i].pages}
      return {group:groups.length-1,page:Math.max(0,groups.at(-1).pages-1)};
    }
    function render(smooth=true){
      const pos=locate(current); const g=groups[pos.group];
      groups.forEach((x,i)=>{if(x.text&&i!==pos.group)x.text.scrollLeft=0});
      if(g&&g.text){const x=pos.page*g.text.clientWidth;g.text.scrollTo({left:x,behavior:smooth?'smooth':'auto'})}
      if(g){root.scrollTo({left:Math.max(0,g.column.offsetLeft-root.clientWidth/2+g.column.clientWidth/2),behavior:smooth?'smooth':'auto'})}
      if(label)label.textContent='صفحه '+(current+1)+' از '+total;
      if(prev)prev.disabled=current<=0;
      if(next)next.disabled=current>=total-1;
      if(shell)shell.style.setProperty('--reader-progress',((current+1)/total*100)+'%');
      localStorage.setItem(key,String(current));
    }
    function go(delta){current=Math.max(0,Math.min(total-1,current+delta));render(true)}
    prev&&prev.addEventListener('click',()=>go(-1));
    next&&next.addEventListener('click',()=>go(1));
    root.addEventListener('click',e=>{if(e.target.closest('a,button,input,textarea,select'))return;const r=root.getBoundingClientRect();if(e.clientX<r.left+r.width*.3)go(-1);else if(e.clientX>r.left+r.width*.7)go(1)});
    window.addEventListener('keydown',e=>{if(['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName))return;if(['ArrowLeft','PageDown',' '].includes(e.key)){e.preventDefault();go(1)}else if(['ArrowRight','PageUp'].includes(e.key)){e.preventDefault();go(-1)}else if(e.key==='Home'){e.preventDefault();current=0;render(false)}else if(e.key==='End'){e.preventDefault();current=total-1;render(false)}});
    window.addEventListener('resize',()=>{const old=current;measure();current=Math.min(old,total-1);render(false)});
    if(document.fonts&&document.fonts.ready)document.fonts.ready.then(()=>measure());
    unwrapLegacy();
    requestAnimationFrame(measure);
    if(new URLSearchParams(location.search).get('focus')==='1')requestAnimationFrame(()=>document.getElementById('article-reader')?.scrollIntoView({block:'start'}));
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
