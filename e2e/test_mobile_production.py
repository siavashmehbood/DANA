import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE_URL=os.getenv("DANA_E2E_BASE_URL","https://dana-staging-web.onrender.com").rstrip("/")
OUT=Path(os.getenv("DANA_E2E_ARTIFACT_DIR","artifacts/mobile"))
OUT.mkdir(parents=True,exist_ok=True)
VIEWPORTS=[("320x568",320,568),("360x800",360,800),("375x667",375,667),("390x844",390,844),("412x915",412,915),("430x932",430,932),("desktop-1366x768",1366,768)]

def assert_visible_geometry(page, selector):
    loc=page.locator(selector)
    expect(loc).to_be_visible()
    box=loc.bounding_box()
    assert box and box["width"]>0 and box["height"]>0, (selector,box)
    style=loc.evaluate("""el=>{const s=getComputedStyle(el);return {display:s.display,visibility:s.visibility,opacity:Number(s.opacity)}}""")
    assert style["display"]!="none" and style["visibility"]!="hidden" and style["opacity"]>0,(selector,style)
    bad=loc.evaluate("""el=>{let n=el;const bad=[];while(n){const s=getComputedStyle(n),r=n.getBoundingClientRect();if(s.display==='none'||s.visibility==='hidden'||Number(s.opacity)===0||r.width===0||r.height===0)bad.push({tag:n.tagName,id:n.id,cls:n.className,display:s.display,visibility:s.visibility,opacity:s.opacity,w:r.width,h:r.height});n=n.parentElement}return bad}""")
    assert not bad,(selector,bad)
    return box

def audit_home(page,name):
    page.goto(BASE_URL+"/",wait_until="networkidle",timeout=90000)
    assert page.locator("#latest-articles").count()==1
    assert_visible_geometry(page,"#latest-articles")
    assert_visible_geometry(page,"#latest-articles h2")
    assert page.locator("#latest-articles h2").inner_text().strip()=="مقالات"
    cta=page.locator("#latest-articles .shelf-more")
    assert_visible_geometry(page,"#latest-articles .shelf-more")
    assert cta.is_enabled()
    cards=page.locator("#latest-articles .article-home-card")
    empty=page.locator("#latest-articles .empty")
    if cards.count():
        assert_visible_geometry(page,"#latest-articles .article-home-card:first-of-type")
    else:
        assert empty.count()==1
        assert_visible_geometry(page,"#latest-articles .empty")
    overflow=page.evaluate("()=>({sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth})")
    assert overflow["sw"]<=overflow["cw"]+2,overflow
    section=page.locator("#latest-articles").bounding_box()
    doc_h=page.evaluate("()=>document.documentElement.scrollHeight")
    assert section and section["y"]>=0 and section["y"]<doc_h
    page.locator("#latest-articles").scroll_into_view_if_needed()
    expect(page.locator("#latest-articles h2")).to_be_in_viewport()
    page.screenshot(path=str(OUT/f"home-{name}.png"),full_page=True)

def main():
    with sync_playwright() as p:
        browser=p.chromium.launch()
        for name,w,h in VIEWPORTS:
            page=browser.new_page(viewport={"width":w,"height":h},locale="fa-IR")
            audit_home(page,name)
            page.close()
        # IntersectionObserver must never be required for core content visibility.
        page=browser.new_page(viewport={"width":390,"height":844},locale="fa-IR")
        page.add_init_script("Object.defineProperty(window,'IntersectionObserver',{value:undefined,writable:false});")
        audit_home(page,"390x844-no-intersection-observer")
        page.close()
        # Core homepage content must also remain visible when JavaScript is unavailable.
        ctx=browser.new_context(viewport={"width":390,"height":844},java_script_enabled=False,locale="fa-IR")
        page=ctx.new_page()
        page.goto(BASE_URL+"/",wait_until="domcontentloaded",timeout=90000)
        assert_visible_geometry(page,"#latest-articles")
        assert_visible_geometry(page,"#latest-articles h2")
        page.screenshot(path=str(OUT/"home-390x844-no-js.png"),full_page=True)
        ctx.close()
        browser.close()

if __name__=="__main__":
    main()
