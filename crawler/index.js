const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const sleep = ms => new Promise(r => setTimeout(r, ms));

const CATEGORIES = [
    {
        name: 'cu-day-sac',
        url: 'https://viettelstore.vn/phu-kien/cap-sac-pkid010005014.html'
    },
    {
        name: 'op',
        url: 'https://viettelstore.vn/phu-kien/bao-da-op-lung-pkid010005012.html'
    },
    {
        name: 'tai-nghe',
        url: 'https://viettelstore.vn/phu-kien/tai-nghe-pkid010005005.html'
    },
    {
        name: 'sac-du-phong',
        url: 'https://viettelstore.vn/phu-kien/pin-du-phong-pkid010005004.html'
    },
    {
        name: 'cuong-luc',
        url: 'https://viettelstore.vn/phu-kien/tam-dan-pkid010005013.html'
    }
];

const OUTPUT_DIR = path.join(__dirname, 'output');
if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR);
}

function loadExistingUrls(filePath) {
    if (!fs.existsSync(filePath)) return new Set();
    try {
        const raw = fs.readFileSync(filePath, 'utf-8');
        const json = JSON.parse(raw);
        return new Set(json.links || []);
    } catch {
        return new Set();
    }
}

(async () => {
    const browser = await puppeteer.launch({
        headless: false,
        slowMo: 50,
        defaultViewport: null
    });

    const page = await browser.newPage();

    for (const category of CATEGORIES) {
        console.log(`\n==============================`);
        console.log(`📂 CATEGORY: ${category.name}`);
        console.log(`==============================`);

        const outputPath = path.join(OUTPUT_DIR, `${category.name}.json`);
        const existingUrls = loadExistingUrls(outputPath);

        const allUrls = new Set(existingUrls);

        await page.goto(category.url, { waitUntil: 'networkidle2' });
        await sleep(2000);

        let round = 1;

        while (true) {
            console.log(`\n📄 ROUND ${round}`);

            const prevTotal = allUrls.size;

            // 1️⃣ Crawl link
            const links = await page.$$eval(
                'div.product-info a',
                as => as.map(a => a.href).filter(Boolean)
            );

            links.forEach(url => allUrls.add(url));

            console.log(`🔎 Links page: ${links.length}`);
            console.log(`📦 Total unique: ${allUrls.size}`);

            // 2️⃣ Nếu không tăng nữa → dừng
            if (allUrls.size === prevTotal) {
                console.log('🛑 Không có link mới → DỪNG category');
                break;
            }

            // 3️⃣ Kiểm tra nút xem thêm
            const hasLoadMore = await page.evaluate(() =>
                [...document.querySelectorAll('a')]
                    .some(a => a.textContent.includes('Xem thêm sản phẩm'))
            );

            if (!hasLoadMore) {
                console.log('🛑 Không còn nút "Xem thêm sản phẩm"');
                break;
            }

            // 4️⃣ Click xem thêm
            console.log('👉 Click "Xem thêm sản phẩm"');
            await page.evaluate(() => {
                const btn = [...document.querySelectorAll('a')]
                    .find(a => a.textContent.includes('Xem thêm sản phẩm'));
                btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                btn.click();
            });

            await sleep(1000); // interval 1s
            round++;
        }

        const finalLinks = [...allUrls];

        fs.writeFileSync(
            outputPath,
            JSON.stringify({
                category: category.name,
                url: category.url,
                total: finalLinks.length,
                new_added: finalLinks.length - existingUrls.size,
                links: finalLinks
            }, null, 2),
            'utf-8'
        );

        console.log(`\n💾 Saved: ${outputPath}`);
        console.log(`🆕 Thêm mới: ${finalLinks.length - existingUrls.size}`);
        console.log(`📦 Tổng URL: ${finalLinks.length}`);
    }

    console.log('\n✅ DONE ALL CATEGORIES');
    // await browser.close();
})();
