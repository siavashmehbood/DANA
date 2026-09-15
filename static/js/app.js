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
