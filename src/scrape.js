const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ acceptDownloads: true });

  // fetch the list page
  const listPage = await context.newPage();
  const listUrl = 'https://npra.gov.my/index.php/en/informationen/new-products-indication/new-products-approved-quest3.html';

  console.log('Fetching list...');
  await listPage.goto(listUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await listPage.waitForTimeout(3000);

  const links = await listPage.$$eval('a', els =>
    els
      .filter(el => el.href && el.href.toLowerCase().endsWith('.pdf'))
      .map(el => ({ text: el.textContent.trim(), href: el.href }))
  );
  await listPage.close();

  // filter DCA404+ and sort ascending
  const target = links
    .map(link => {
      const m = link.text.match(/^DCA(\d+)$/);
      return m ? { dca: parseInt(m[1], 10), text: link.text, href: link.href } : null;
    })
    .filter(item => item !== null)
    .filter(item => item.dca >= 404)
    .sort((a, b) => a.dca - b.dca);

  // detect which PDFs are not yet downloaded
  const newItems = target.filter(item => {
    const outputPath = path.join('./downloads', `${item.text}.pdf`);
    return !fs.existsSync(outputPath);
  });

  console.log(`Total: ${target.length}, Already downloaded: ${target.length - newItems.length}, New: ${newItems.length}`);

  if (newItems.length === 0) {
    console.log('No new documents. Nothing to download.');
    await browser.close();
    return;
  }

  console.log(`Downloading: ${newItems[0].text} → ${newItems[newItems.length - 1].text}`);

  // download the remaining PDFs
  fs.mkdirSync('./downloads', { recursive: true });

  for (const item of newItems) {
    const outputPath = path.join('./downloads', `${item.text}.pdf`);

    console.log(`[download] ${item.text}...`);

    const page = await context.newPage();
    try {
      const [download] = await Promise.all([
        page.waitForEvent('download', { timeout: 60000 }),
        page.goto(item.href).catch(() => {}),
      ]);
      await download.saveAs(outputPath);
      console.log(`  ✓ saved`);
    } catch (err) {
      console.error(`  ✗ failed: ${err.message}`);
    } finally {
      await page.close();
    }
  }

  await browser.close();
  console.log('Done.');
})();