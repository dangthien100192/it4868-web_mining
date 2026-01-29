const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const sleep = ms => new Promise(r => setTimeout(r, ms));

const INPUT_FILE = path.join(__dirname, 'output/phu-kien/tai-nghe.json');
const OUTPUT_FILE = path.join(__dirname, 'product-headphone.json');

function extractIdFromUrl(url) {
    const match = url.match(/pid\d+/i);
    return match ? match[0] : null;
}

function normalizePrice(text) {
    if (!text) return null;
    return Number(text.replace(/[^\d]/g, ''));
}

/**
 * Phân tích text để tìm:
 * - connections (nghe)
 * - charging_port (sạc)
 */
function extractPorts(text) {
    const t = text.toLowerCase();
    const connections = new Set();
    let chargingPort = null;

    // 🎧 CONNECTIONS
    if (t.includes('bluetooth') || /\bbt\b/.test(t)) {
        connections.add('bluetooth');
    }

    if (t.includes('3.5') || t.includes('3,5') || t.includes('jack')) {
        connections.add('3.5mm');
    }

    // USB nghe trực tiếp (ít gặp nhưng có)
    if (t.includes('usb audio')) {
        connections.add('usb');
    }

    // 🔌 CHARGING PORT
    if (t.includes('type-c') || t.includes('usb-c')) {
        chargingPort = 'type-c';
    } else if (t.includes('micro usb')) {
        chargingPort = 'micro-usb';
    } else if (t.includes('cổng lightning')) {
        chargingPort = 'lightning';
    }

    return {
        connections: [...connections],
        charging_port: chargingPort
    };
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
        console.log(`\n==============================`);
        console.log(`📄 (${index}/${urls.length}) ${url}`);

        try {
            await page.goto(url, { waitUntil: 'networkidle2' });
            await sleep(1000);

            const data = await page.evaluate(() => {
                const name =
                    document.querySelector('h1')?.innerText?.trim() || '';

                const priceText =
                    document.querySelector('span.new-price')?.innerText || '';

                const specText = [
                    ...document.querySelectorAll('#panel-cau-hinh, .panel-cau-hinh')
                ]
                    .map(el => el.innerText)
                    .join(' ');

                return { name, priceText, specText };
            });

            const id = extractIdFromUrl(url);
            const price = normalizePrice(data.priceText);

            // 🔍 parse từ cấu hình
            let ports = extractPorts(data.specText);

            // 🔁 fallback parse từ tên
            if (ports.connections.length === 0 && !ports.charging_port) {
                ports = extractPorts(data.name);
            }

            const item = {
                id,
                name: data.name,
                price,
                connections: ports.connections
            };

            if (ports.charging_port) {
                item.charging_port = ports.charging_port;
            }

            console.log('✅ Parsed:', item);
            results.push(item);
        } catch (err) {
            console.log('❌ Lỗi:', err.message);
        }

        index++;
        await sleep(1000); // interval 1s
    }

    fs.writeFileSync(
        OUTPUT_FILE,
        JSON.stringify(results, null, 2),
        'utf-8'
    );

    console.log(`\n💾 Saved → ${OUTPUT_FILE}`);
    console.log(`🎧 Total products: ${results.length}`);

    // await browser.close();
})();
