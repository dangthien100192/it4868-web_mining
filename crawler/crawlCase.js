const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const sleep = ms => new Promise(r => setTimeout(r, ms));

const INPUT_FILE = path.join(__dirname, 'output/phu-kien/op.json');
const OUTPUT_FILE = path.join(__dirname, 'product-case.json');

function extractId(url) {
    const m = url.match(/pid\d+/i);
    return m ? m[0] : null;
}

function normalizePrice(text) {
    if (!text) return null;
    return Number(text.replace(/[^\d]/g, ''));
}

function normalize(text) {
    return text
        .toLowerCase()
        .replace(/[-_/]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

function detectDeviceType(text) {
    const t = text.toLowerCase();
    if (t.includes('iphone')) return 'iphone';
    if (t.includes('samsung') || t.includes('galaxy')) return 'samsung';
    if (t.includes('ipad')) return 'ipad';
    if (t.includes('watch')) return 'watch';
    if (t.includes('tab')) return 'tablet';
    return 'other';
}

function extractModels(text) {
    const t = normalize(text);
    const models = new Set();

    // iPhone
    const iphoneRegex =
        /iphone\s(\d+)(?:\spro\smax|\spro|\splus|\sair)?/g;
    let m;
    while ((m = iphoneRegex.exec(t)) !== null) {
        models.add(`iphone ${m[1]}${m[0].includes('pro max') ? ' pro max'
            : m[0].includes('pro') ? ' pro'
                : m[0].includes('plus') ? ' plus'
                    : m[0].includes('air') ? ' air'
                        : ''}`.trim());
    }

    // Samsung Galaxy
    const galaxyRegex =
        /(galaxy\s(?:s|z|a|tab))\s?([a-z0-9\s]+)/g;
    while ((m = galaxyRegex.exec(t)) !== null) {
        models.add(`${m[1]} ${m[2]}`.trim());
    }

    // iPad
    const ipadRegex =
        /(ipad\s(?:pro|air|mini))\s?([a-z0-9\s]*)/g;
    while ((m = ipadRegex.exec(t)) !== null) {
        models.add(`${m[1]} ${m[2]}`.trim());
    }

    return [...models];
}

(async () => {
    if (!fs.existsSync(INPUT_FILE)) {
        console.error('❌ Không tìm thấy file input');
        return;
    }

    const input = JSON.parse(fs.readFileSync(INPUT_FILE, 'utf-8'));
    const urls = input.links || [];

    console.log(`🔗 Tổng URL: ${urls.length}`);

    const browser = await puppeteer.launch({
        headless: false,
        slowMo: 30,
        defaultViewport: null
    });

    const page = await browser.newPage();
    const results = [];

    let index = 1;

    for (const url of urls) {
        console.log(`\n📄 (${index}/${urls.length}) ${url}`);

        try {
            await page.goto(url, { waitUntil: 'networkidle2' });
            await sleep(1000);

            const data = await page.evaluate(() => {
                const name =
                    document.querySelector('h1')?.innerText?.trim() || '';

                const priceText =
                    document.querySelector('span.new-price')?.innerText || '';

                return { name, priceText };
            });

            const id = extractId(url);
            const price = normalizePrice(data.priceText);

            const combinedText = `${url} ${data.name}`;
            const device_type = detectDeviceType(combinedText);
            const models = extractModels(combinedText);

            const item = {
                id,
                name: data.name,
                device_type,
                models,
                price
            };

            console.log('✅ Parsed:', item);
            results.push(item);
        } catch (e) {
            console.log('❌ Lỗi:', e.message);
        }

        index++;
        await sleep(1000);
    }

    fs.writeFileSync(
        OUTPUT_FILE,
        JSON.stringify(results, null, 2),
        'utf-8'
    );

    console.log(`\n💾 Saved → ${OUTPUT_FILE}`);
    console.log(`📦 Total items: ${results.length}`);

    // await browser.close();
})();
