const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright');
const fs=require('fs');
(async()=>{
  const browser=await chromium.launch({headless:true,...(process.env.BROWSER_PATH?{executablePath:process.env.BROWSER_PATH}:{})});
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const password=process.env.DEMO_PASSWORD;if(!password)throw Error('Set DEMO_PASSWORD');
  async function login(name){await page.goto('http://127.0.0.1:8000');await page.getByLabel('用户名',{exact:true}).fill(name);await page.getByLabel('密码',{exact:true}).fill(password);await page.getByRole('button',{name:'进入课堂'}).click();await page.locator('#session-select').waitFor();}
  await login('student');await page.locator('[data-emoji="surprise"]').click();await page.getByText('已记录，谢谢你的反馈',{exact:true}).waitFor();
  fs.mkdirSync('artifacts',{recursive:true});await page.screenshot({path:'artifacts/student.png',fullPage:true});
  await page.locator('#logout').click();await login('teacher');await page.locator('#charts .metric').first().waitFor();
  await page.screenshot({path:'artifacts/teacher-dashboard.png',fullPage:true});
  await page.locator('[data-page="statistics"]').click();await page.locator('#results .metric').first().waitFor();
  await page.locator('#logout').click();await login('admin');await page.locator('[data-page="history"]').click();await page.locator('#results table').waitFor();
  const download=page.waitForEvent('download');await page.locator('#export').click();const file=await download;await file.saveAs('artifacts/export.csv');
  if(!fs.readFileSync('artifacts/export.csv','utf8').includes('surprise'))throw Error('Missing submitted emotion in CSV');
  await page.locator('[data-page="manage"]').click();await page.locator('#course-form').waitFor();
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:'artifacts/mobile.png',fullPage:true});
  if(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth))throw Error('Mobile horizontal overflow');
  await page.locator('[data-page="account"]').click();await page.locator('#account-logout').click();
  if(errors.length)throw Error(errors.join('\n'));
  await page.screenshot({path:'artifacts/login-mobile.png',fullPage:true});
  await browser.close();console.log('PASS: student submission, teacher dashboard, statistics, admin CSV export, management, mobile layout, logout; no page errors.');
})().catch(e=>{console.error(e);process.exit(1)});
