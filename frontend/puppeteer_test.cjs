const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('BROWSER_CONSOLE:', msg.text()));
  page.on('pageerror', error => console.log('BROWSER_ERROR:', error.message));
  
  await page.goto('http://localhost:5173/manager');
  await new Promise(r => setTimeout(r, 2000));
  
  try {
      // Find a button containing "Ask Assistant" or just a button on bottom right
      await page.evaluate(() => {
          const btns = Array.from(document.querySelectorAll('button'));
          const target = btns.find(b => b.innerText.includes('Ask Assistant') || b.textContent.includes('Assistant'));
          if(target) target.click();
          else console.log('Button not found');
      });
      await new Promise(r => setTimeout(r, 2000));
  } catch(e) {
      console.log('Error clicking:', e);
  }
  
  await browser.close();
})();
