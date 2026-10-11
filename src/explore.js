const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  const url = 'https://npra.gov.my/index.php/en/informationen/new-products-indication/new-products-approved-quest3.html';
  console.log('Opening:', url);

  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(3000);

  // grab all links ending in .pdf
  const links = await page.$$eval('a', els =>
    els
      .filter(el => el.href && el.href.toLowerCase().endsWith('.pdf'))
      .map(el => ({ text: el.textContent.trim(), href: el.href }))
  );

  // filter DCA404+ and sort ascending
  const target = links.map(link => {
    // m[0] = full match, m[1] = captured digits
    const m = link.text.match(/^DCA(\d+)$/);
    return m ? { dca: parseInt(m[1], 10), text: link.text, href: link.href } : null;
  })
  .filter(item => item !== null)
  .filter(item => item.dca >= 404)
  .sort((a, b) => a.dca - b.dca);

  console.log('To download:', target.length);
  console.log(JSON.stringify(target, null, 2));

  await browser.close();
})();