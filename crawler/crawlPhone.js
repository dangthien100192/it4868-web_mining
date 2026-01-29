const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const sleep = ms => new Promise(r => setTimeout(r, ms));

// ================= CONFIG =================
const INPUT_FILE = path.join(__dirname, 'output', 'dien-thoai.json');
const OUTPUT_FILE = path.join(__dirname, 'product_phone_web.json');
const INTERVAL_MS = 1000;

// ================= NORMALIZE =================
function splitToArray(value) {
    if (!value) return [];
    return value
        .replace(/\s+và\s+/gi, ',')
        .replace(/\s*&\s*/g, ',')
        .replace(/\s*\|\s*/g, ',')
        .replace(/\s*;\s*/g, ',')
        .split(',')
        .map(v => v.trim())
        .filter(Boolean);
}

function parseDimensions(value) {
    // Ví dụ hợp lệ:
    // "159,9 x 76,7 x 8,25 mm"
    // "159.9 x 76.7 x 8.25"
    // "160 x 75 x 8 mm"

    return value
        .toLowerCase()
        .replace(/mm/g, '')
        .replace('Ngang', '')
        .replace('Cao', '')
        .replace('Dày', '')
        .replace('Rộng', '')
        .replace('Dài', '')
        .replace('ngang', '')
        .replace('cao', '')
        .replace('dày', '')
        .replace('rộng', '')
        .replace('dài', '')
        .replace('-', 'x')
        .split('x')
        .map(v => {
            // đổi dấu phẩy thành dấu chấm
            const normalized = v.trim().replace(',', '.');
            const num = parseFloat(normalized);
            return isNaN(num) ? null : num;
        })
        .filter(v => v !== null);
}

function extractKeyFromUrl(url) {
    const slug = url
        .split('/')
        .pop()
        .replace('.html', '')
        .toLowerCase();

    const parts = slug.split('-');

    let storage = null;
    const nameParts = [];

    for (const part of parts) {
        // bỏ pid
        if (part.startsWith('pid')) continue;

        // RAM (vd: 8gb, 12gb)
        if (/^\d+gb$/.test(part)) continue;

        // Storage (vd: 128gb, 256gb, 1tb)
        if (/^\d+(gb|tb)$/.test(part)) {
            storage = part;
            continue;
        }

        nameParts.push(part);
    }

    if (!storage) storage = 'unknown';

    return `${nameParts.join('_')}_${storage}`;
}


function normalizeSpecs(rawSpecs) {
    const normalized = {};

    for (const [key, value] of Object.entries(rawSpecs)) {
        if (!value) continue;

        const lowerKey = key.toLowerCase();

        // ===== KÍCH THƯỚC =====
        if (lowerKey.includes('kích thước')) {
            const dims = parseDimensions(value);
            if (dims.length > 3) {
                normalized.dimensions_mm = dims;
            } else {
                normalized.dimensions_raw = value; // fallback debug
            }
            continue;
        }

        // ===== RAM =====
        if (lowerKey.includes('ram')) {
            normalized.ram_gb = parseInt(value.replace(/gb/gi, '').trim());
            continue;
        }

        // ===== BỘ NHỚ TRONG =====
        if (lowerKey.includes('bộ nhớ trong')) {
            normalized.storage_gb = parseInt(value.replace(/gb/gi, '').trim());
            continue;
        }

        // ===== HỆ ĐIỀU HÀNH =====
        if (lowerKey.includes('hệ điều hành')) {
            const parts = value.split(' ');
            normalized.os = {
                name: parts[0],
                version: parts.slice(1).join(' ')
            };
            continue;
        }

        // ===== TÁCH MẢNG (KHÔNG ÁP DỤNG CHO KÍCH THƯỚC) =====
        if (
            (/[,&|]/.test(value) || value.toLowerCase().includes(' và '))
        ) {
            normalized[key] = splitToArray(value);
            continue;
        }

        // ===== DEFAULT =====
        normalized[key] = value;
    }

    return normalized;
}

// ================= MAIN =================
(async () => {
    console.log('🚀 START PHONE CRAWLER (DEBUG MODE)');

    if (!fs.existsSync(INPUT_FILE)) {
        console.error('❌ Không tìm thấy file:', INPUT_FILE);
        process.exit(1);
    }

    const inputData = JSON.parse(fs.readFileSync(INPUT_FILE, 'utf-8'));
    const urls = inputData.links || [];

    console.log(`🔗 TOTAL URLS: ${urls.length}`);
    if (urls.length === 0) process.exit(1);

    const browser = await puppeteer.launch({
        headless: false,
        slowMo: 50,
        defaultViewport: null
    });

    const page = await browser.newPage();
    const results = [];

    for (let i = 0; i < urls.length; i++) {
        const url = urls[i];

        console.log('\n====================================');
        console.log(`📱 [${i + 1}/${urls.length}]`);
        console.log(url);

        try {
            await page.goto(url, { waitUntil: 'networkidle2' });

            console.log(`⏳ WAIT ${INTERVAL_MS}ms`);
            await sleep(INTERVAL_MS);

            const configBtn = await page.$('#navcau-hinh');
            if (!configBtn) {
                console.log('⚠️ Không có nút cấu hình');
                continue;
            }

            console.log('✅ FOUND #navcau-hinh');

            await page.evaluate(() => {
                const btn = document.querySelector('#navcau-hinh');
                btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                btn.click();
            });

            await page.waitForSelector('#panel-cau-hinh', { timeout: 8000 });
            console.log('📦 panel-cau-hinh loaded');

            const rawSpecs = await page.$$eval(
                '#panel-cau-hinh tr.row_item',
                rows => {
                    const data = {};
                    rows.forEach(row => {
                        const key = row.querySelector('td.left_row_item')?.innerText.trim();
                        const value = row.querySelector('td.right_row_item')?.innerText.trim();
                        if (key && value) data[key] = value;
                    });
                    return data;
                }
            );

            console.log(`🧾 RAW SPECS: ${Object.keys(rawSpecs).length}`);
            Object.entries(rawSpecs).forEach(([k, v]) =>
                console.log(`   - ${k}: ${v}`)
            );

            const normalizedSpecs = normalizeSpecs(rawSpecs);

            console.log('🔧 NORMALIZED SPECS');
            console.log(normalizedSpecs);

            const product_key = extractKeyFromUrl(url);

            results.push({
                product_key,
                url,
                raw_specs: rawSpecs,
                specs: normalizedSpecs
            });

            await sleep(INTERVAL_MS);

        } catch (err) {
            console.log('❌ ERROR:', err.message);
        }
    }

    fs.writeFileSync(
        OUTPUT_FILE,
        JSON.stringify(
            {
                crawled_at: new Date().toISOString(),
                total: results.length,
                data: results
            },
            null,
            2
        )
    );

    console.log('\n💾 SAVED:', OUTPUT_FILE);
    console.log('🏁 DONE ALL');

    // await browser.close();
})();
