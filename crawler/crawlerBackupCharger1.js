const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const sleep = ms => new Promise(r => setTimeout(r, ms));

const INPUT_FILE = path.join(
    __dirname,
    'output/phu-kien/sac-du-phong.json'
);

const OUTPUT_FILE = path.join(
    __dirname,
    'product-back-up-charger.json'
);

// ================== UTIL ==================
function extractIdFromUrl(url) {
    const match = url.match(/-(pid\d+)\.html/i);
    return match ? match[1] : null;
}

function extractPower(text) {
    const match = text.match(/(\d+(?:\.\d+)?)\s*W/i);
    return match ? Number(match[1]) : null;
}

function extractCapacity(text) {
    const match = text.match(/(\d{4,6})\s*mAh/i);
    return match ? Number(match[1]) : null;
}

function extractPrice(text) {
    if (!text) return null;
    return Number(
        text.replace(/[^\d]/g, '')
    );
}

// ================== MAIN ==================
(async () => {
    if (!fs.existsSync(INPUT_FILE)) {
        console.error('❌ Không tìm thấy file URL');
        process.exit(1);
    }

    const urls = JSON.parse(
        fs.readFileSync(INPUT_FILE, 'utf-8')
    ).links || [];

    console.log(`📦 Tổng URL: ${urls.length}`);

    const browser = await puppeteer.launch({
        headless: false,
        slowMo: 50,
        defaultViewport: null
    });

    const page = await browser.newPage();

    const results = [];

    for (let i = 0; i < urls.length; i++) {
        const url = urls[i];
        console.log(`\n🔍 [${i + 1}/${urls.length}] ${url}`);

        const id = extractIdFromUrl(url);
        if (!id) {
            console.log('⚠ Không tìm được ID → bỏ qua');
            continue;
        }

        await page.goto(url, { waitUntil: 'networkidle2' });
        await sleep(1000);

        // 👉 Lấy toàn bộ text trang để parse W + mAh
        const pageText = await page.evaluate(() =>
            document.body.innerText
        );

        const power = extractPower(pageText);
        const capacity = extractCapacity(pageText);

        // 👉 Lấy giá
        const priceText = await page.evaluate(() => {
            const el = document.querySelector('span.new-price');
            return el ? el.innerText : null;
        });

        const price = extractPrice(priceText);

        const item = {
            id,
            url
        };

        if (power !== null) item.power = power;
        if (capacity !== null) item.capacity = capacity;
        if (price !== null) item.price = price;

        results.push(item);

        console.log('✅ Parsed:', item);

        await sleep(1000); // interval 1s
    }

    fs.writeFileSync(
        OUTPUT_FILE,
        JSON.stringify({
            total: results.length,
            items: results
        }, null, 2),
        'utf-8'
    );

    console.log('\n💾 Saved:', OUTPUT_FILE);
    console.log('✅ DONE');

    // await browser.close();
})();
