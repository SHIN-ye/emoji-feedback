const{chromium}=require(process.env.PLAYWRIGHT_PATH||'playwright');
(async()=>{const b=await chromium.launch({headless:true,...(process.env.BROWSER_PATH?{executablePath:process.env.BROWSER_PATH}:{})});const p=await b.newPage();await p.goto('http://127.0.0.1:8000');await p.getByLabel('用户名',{exact:true}).fill('teacher');await p.getByLabel('密码',{exact:true}).fill(process.env.DEMO_PASSWORD);await p.getByRole('button',{name:'进入课堂'}).click();await p.locator('#charts .metric').first().waitFor();
let release;const gate=new Promise(r=>release=r);let intercepted;const caught=new Promise(r=>intercepted=r);
await p.route('**/api/emoji/history?',async route=>{const response=await route.fetch();intercepted();await gate;await route.fulfill({response});});
await p.locator('[data-page="history"]').click();await caught;await p.locator('[data-page="statistics"]').click();await p.locator('#results .metric').first().waitFor();release();await p.waitForTimeout(300);
if(await p.locator('#results table').count())throw Error('Stale history overwrote statistics');
await b.close();console.log('PASS: stale response cannot overwrite a different route');})().catch(e=>{console.error(e);process.exit(1)});
