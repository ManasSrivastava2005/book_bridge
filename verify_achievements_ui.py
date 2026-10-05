import json,subprocess
from pathlib import Path
from app.services.auth import create_access_token
f=json.loads(Path('v2-integration-fixture.json').read_text());token=create_access_token(f['student'],'student')
program=r"""
await page.setViewportSize({width:1600,height:1100});await page.goto('http://127.0.0.1:5174/login');await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),TOKEN);await page.goto('http://127.0.0.1:5174/achievements');await page.getByRole('heading',{name:'Achievements',exact:true}).waitFor();
for(const name of ['Reading','Streak','Level','Contribution','Quiz','Curriculum','Other'])await page.getByRole('heading',{name:name+' Badges',exact:true}).waitFor();
await page.getByRole('button',{name:'Book Explorer, Locked',exact:true}).click();await page.getByRole('complementary',{name:'Selected badge details'}).getByRole('heading',{name:'Book Explorer',exact:true}).waitFor();
await page.screenshot({path:'achievements-desktop.png',fullPage:true});
await page.setViewportSize({width:390,height:844});if(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth))throw new Error('Mobile horizontal overflow');
await page.getByRole('button',{name:'First Borrow, Earned',exact:true}).click();await page.getByRole('complementary',{name:'Selected badge details'}).getByRole('heading',{name:'First Borrow',exact:true}).waitFor();await page.screenshot({path:'achievements-mobile.png',fullPage:true});await page.setViewportSize({width:1600,height:1100});await page.evaluate(()=>localStorage.removeItem('bookbridge_token'));return {categories:7,selection:true,earned:true,mobileNoOverflow:true,url:page.url()};
""".replace('TOKEN',json.dumps(token))
r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','v2-circulation-checks-r5','browser','run','--stdin','--no-snapshot-diff','--timeout','40','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=50);print(r.stdout);print(r.stderr);assert r.returncode==0
