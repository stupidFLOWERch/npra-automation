const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ acceptDownloads: true });
  const page = await context.newPage();

  const url = 'https://npra.gov.my/easyarticles/images/users/1153/DCA/New%20Product%20Approved/2025/Senarai-produk-yang-diluluskan-dalam-PBKD404-16-Jan-2025-website.pdf';

  const outputDir = './downloads';
  fs.mkdirSync(outputDir, { recursive: true });

  const outputPath = path.join(outputDir, 'DCA404.pdf');

  console.log('Downloading DCA404...');
  console.log('URL:', url);

  try {
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 60000 }),
      page.goto(url).catch(() => {}),
    ]);

    console.log('Suggested filename:', download.suggestedFilename());
    await download.saveAs(outputPath);
    console.log('Saved to:', outputPath);

    const buffer = fs.readFileSync(outputPath);
    console.log('Size:', buffer.length, 'bytes');
    console.log('Header:', buffer.slice(0, 4).toString());
  } catch (err) {
    console.error('Download failed:', err.message);
  }

  await browser.close();
})();