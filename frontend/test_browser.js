const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage();
  let gotRootInfo = false;
  page.on('console', msg => {
    console.log('PAGE LOG:', msg.text());
    if (msg.text().includes('ROOT HTML:')) gotRootInfo = true;
  });
  page.on('pageerror', error => console.error('PAGE ERROR:', error.message));
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle2' });
  await page.evaluate(() => {
     console.log('ROOT HTML:', document.getElementById('root').innerHTML.length);
  });
  await browser.close();
})();
