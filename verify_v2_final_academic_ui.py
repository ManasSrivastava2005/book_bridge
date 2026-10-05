import json,subprocess
from pathlib import Path
from app.services.auth import create_access_token
f=json.loads(Path('v2-integration-fixture.json').read_text());token=create_access_token(f['student'],'student')
program=r"""
await page.goto('http://127.0.0.1:5174/login');await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),TOKEN);
await page.goto('http://127.0.0.1:5174/learning-path');await page.getByRole('heading',{name:'Paging completed',exact:true}).waitFor();
await page.goto('http://127.0.0.1:5174/academic-plan');await page.getByRole('heading',{name:'Operating Systems · 100%',exact:true}).waitFor();
await page.goto('http://127.0.0.1:5174/quizzes');await page.getByRole('button',{name:'Integrated quiz · 100%',exact:true}).click();await page.getByText('Score: 100%',{exact:true}).waitFor();
await page.evaluate(()=>localStorage.removeItem('bookbridge_token'));return {url:page.url(),pathCompleted:true,planProgress100:true,persistedQuizScore100:true};
""".replace('TOKEN',json.dumps(token))
r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','v2-circulation-checks-r5','browser','run','--stdin','--no-snapshot-diff','--timeout','30','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=40);print(r.stdout);print(r.stderr);assert r.returncode==0
