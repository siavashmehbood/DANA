const topButton=document.getElementById('top');
if(topButton){window.addEventListener('scroll',()=>{topButton.style.opacity=window.scrollY>350?'1':'0'});topButton.onclick=()=>window.scrollTo({top:0,behavior:'smooth'});topButton.style.opacity='0';topButton.style.transition='opacity .2s'}
function showPhoneLogin(){document.getElementById('passwordLogin').hidden=true;document.getElementById('recoveryPanel').hidden=true;document.getElementById('phoneLogin').hidden=false}
function showPasswordLogin(){document.getElementById('phoneLogin').hidden=true;document.getElementById('recoveryPanel').hidden=true;document.getElementById('passwordLogin').hidden=false}
function showRecovery(){document.getElementById('passwordLogin').hidden=true;document.getElementById('phoneLogin').hidden=true;document.getElementById('recoveryPanel').hidden=false}
function csrfToken(){return document.querySelector('[name=csrfmiddlewaretoken]')?.value||''}
function setupArticleTools(){
 const reader=document.querySelector('.selectable-reader'),tools=document.getElementById('selectionTools');
 if(!reader||!tools)return;
 let selected='';
 const preview=document.getElementById('selectionPreview'),result=document.getElementById('selectionResult');
 const current=()=>window.getSelection()?.toString().trim()||'';
 reader.addEventListener('mouseup',()=>{const text=current();if(!text)return;selected=text.slice(0,180);preview.textContent=`انتخاب: ${selected}`;tools.hidden=false;result.textContent=''})
 document.getElementById('saveSelectedWord').onclick=async()=>{
  if(!selected)return;
  const url=document.getElementById('article-reader').dataset.saveWordUrl;
  const body=new URLSearchParams({word:selected});
  const r=await fetch(url,{method:'POST',headers:{'X-CSRFToken':csrfToken(),'Content-Type':'application/x-www-form-urlencoded'},body});
  const d=await r.json();result.textContent=d.ok?(d.created?'در لغات من ذخیره شد.':'این مورد قبلاً ذخیره شده است.'):(d.error||'ذخیره انجام نشد.');
 };
 document.getElementById('translateSelectedWord').onclick=async()=>{
  if(!selected)return;
  const url=document.getElementById('article-reader').dataset.translateUrl;result.textContent='در حال بررسی ترجمه...';
  const r=await fetch(url,{method:'POST',headers:{'X-CSRFToken':csrfToken(),'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({text:selected})});
  const d=await r.json();result.textContent=d.ok?d.translation:(d.error||'ترجمه در دسترس نیست.');
 };
}
document.addEventListener('DOMContentLoaded',setupArticleTools);

// Button click ripple for a clear, lightweight interaction effect.
document.addEventListener('click',(event)=>{
 const button=event.target.closest('.btn,.buy-mini,.header-search button,.home-search-top button,.selection-helper');
 if(!button)return;
 const ripple=document.createElement('span');
 const size=Math.max(button.clientWidth,button.clientHeight);
 const rect=button.getBoundingClientRect();
 ripple.className='ripple'; ripple.style.width=`${size}px`; ripple.style.height=`${size}px`;
 ripple.style.left=`${event.clientX-rect.left-size/2}px`; ripple.style.top=`${event.clientY-rect.top-size/2}px`;
 button.appendChild(ripple); ripple.addEventListener('animationend',()=>ripple.remove());
});


// DANA interaction layer v4
(function(){
 const qs=(s,c=document)=>c.querySelector(s),qsa=(s,c=document)=>[...c.querySelectorAll(s)];
 const csrf=()=>qs('[name=csrfmiddlewaretoken]')?.value||'';
 function toast(message,type='info'){
  let stack=qs('.toast-stack'); if(!stack){stack=document.createElement('div');stack.className='toast-stack';document.body.appendChild(stack)}
  const item=document.createElement('div');item.className=`dana-toast ${type}`;item.setAttribute('role','status');item.innerHTML=`<span>${message}</span><button type="button" aria-label="بستن">×</button>`;stack.appendChild(item);
  const close=()=>{item.style.opacity='0';item.style.transform='translateX(-12px)';setTimeout(()=>item.remove(),180)};item.querySelector('button').onclick=close;setTimeout(close,4200);
 }
 window.DANA={toast,csrf};
 function loading(button,on){if(!button)return;button.classList.toggle('is-loading',on);button.disabled=on}
 qsa('button[type="submit"],.btn[type="submit"]').forEach(btn=>{const form=btn.closest('form');if(!form)return;form.addEventListener('submit',()=>{if(form.checkValidity())loading(btn,true)})});
 qsa('[data-animate]').forEach(el=>{if(!('IntersectionObserver' in window)){el.classList.add('is-visible');return}const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('is-visible');io.unobserve(e.target)}}),{threshold:.08});io.observe(el)});
 document.addEventListener('click',e=>{const b=e.target.closest('[data-copy]');if(!b)return;const text=b.dataset.copy;if(!text)return;navigator.clipboard?.writeText(text).then(()=>{const old=b.textContent;b.textContent='کپی شد ✓';toast('کد دعوت با موفقیت کپی شد.','success');setTimeout(()=>b.textContent=old,1600)}).catch(()=>toast('کپی خودکار در دسترس نیست.','error'))});
 qsa('.book-card,.pro-book,.article-home-card,.category-pro-grid a').forEach(c=>c.setAttribute('data-animate',''));
})();
