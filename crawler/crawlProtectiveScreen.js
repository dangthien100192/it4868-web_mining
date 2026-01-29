const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const sleep = ms => new Promise(r => setTimeout(r, ms));

const INPUT_FILE = path.join(__dirname, 'output/phu-kien/cuong-luc.json');
const OUTPUT_FILE = path.join(__dirname, 'product-screen-protector.json');

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
    if (t.includes('tab')) return 'tablet';
    if (t.includes('honor') || t.includes('oppo') || t.includes('vivo') || t.includes('redmi'))
        return 'android';
    return 'other';
}

function extractModels(text) {
    const t = normalize(text);
    const models = new Set();
    let m;

    // iPhone
    const iphoneRegex =
        /iphone\s\d+(?:\spro\smax|\spro|\splus|\smini|\sair|\se)?/g;
    while ((m = iphoneRegex.exec(t)) !== null) {
        models.add(m[0]);
    }

    // Samsung
    const samsungRegex =
        /(samsung|galaxy)\s[a-z0-9\s]+?(?=full|$)/g;
    while ((m = samsungRegex.exec(t)) !== null) {
        models.add(m[0].trim());
    }

    // iPad
    const ipadRegex =
        /ipad\s(?:pro|air|mini)?\s?[a-z0-9\s]*(?:inch)?/g;
    while ((m = ipadRegex.exec(t)) !== null) {
        models.add(m[0].trim());
    }

    // Android khác
    const androidRegex =
        /(oppo|vivo|honor|redmi)\s[a-z0-9\s]+/g;
    while ((m = androidRegex.exec(t)) !== null) {
        models.add(m[0].trim());
    }

    return [...models];
}

function detectGlassType(text) {
    const t = text.toLowerCase();
    const types = [];

    if (t.includes('chống nhìn trộm')) types.push('privacy');
    if (t.includes('full')) types.push('full');
    if (t.includes('không viền')) types.push('no-edge');
    if (t.includes('camera')) types.push('camera-glass');
    if (t.includes('cường lực') || t.includes('kcl')) types.push('tempered-glass');

    return types;
}

function detectBrand(text) {
    const brands = ['zagg', 'likglass', 'ifinger', 'devia'];
    const t = text.toLowerCase();
    return brands.find(b => t.includes(b)) || null;
}

(async () => {
    if (!fs.existsSync(INPUT_FILE)) {
        console.error('❌ Không tìm thấy file input');
        return;
    }

    const input = JSON.parse(fs.readFileSync(INPUT_FILE, 'utf-8'));
    const urls = input.links || [];

    console.log(`🔗 TOTAL URL: ${urls.length}`);

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

            const combined = `${url} ${data.name}`;

            const item = {
                id,
                name: data.name,
                brand: detectBrand(combined),
                device_type: detectDeviceType(combined),
                models: extractModels(combined),
                glass_type: detectGlassType(combined),
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
    console.log(`📦 TOTAL ITEMS: ${results.length}`);

    // await browser.close();
})();
