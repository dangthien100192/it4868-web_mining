import puppeteer from 'puppeteer';
import fs from 'fs';
import path from 'path';
import OpenAI from 'openai';

const sleep = ms => new Promise(r => setTimeout(r, ms));

const client = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY
});

const INPUT_FILE = path.join(
    process.cwd(),
    'output/phu-kien/sac-du-phong.json'
);

const OUTPUT_FILE = path.join(
    process.cwd(),
    'product-back-up-charger.json'
);

// ================== UTIL ==================
function extractIdFromUrl(url) {
    const match = url.match(/-(pid\d+)\.html/i);
    return match ? match[1] : null;
}

function extractPrice(text) {
    if (!text) return null;
    return Number(text.replace(/[^\d]/g, ''));
}

// ================== AI EXTRACTION ==================
async function extractByAI(text) {
    const prompt = `
Bạn đang đọc nội dung trang web bán PIN DỰ PHÒNG.

Hãy trích xuất thông tin theo quy tắc:
- power: công suất sạc (W), ví dụ 20W, 22.5W
- price: giá bán (VNĐ)
- capacity: dung lượng pin (mAh), ví dụ 10000, 20000

QUY TẮC:
- Có thể trích xuất từ tên sản phẩm, không bắt buộc phải từ mô tả hay thông số kỹ thuật
- Nếu KHÔNG tìm thấy thì KHÔNG ghi key đó
- Nếu không tìm thấy giá hoặc giá không phải số, hãy gán price = 0
- Chỉ trả về JSON thuần
- Không giải thích
- Không markdown

Ví dụ output hợp lệ:
{ "power": 22.5, "capacity": 20000, "price": 850000 }
hoặc
{ "capacity": 10000, "price": 0 }
`;

    const response = await client.responses.create({
        model: 'gpt-4.1-mini',
        input: [
            { role: 'user', content: text.slice(0, 12000) },
            { role: 'user', content: prompt }
        ]
    });

    try {
        return JSON.parse(response.output_text);
    } catch {
        return {};
    }
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

        // 1️⃣ Lấy text toàn trang
        const pageText = await page.evaluate(() =>
            document.body.innerText
        );

        // 2️⃣ AI extract power + capacity
        const aiData = await extractByAI(pageText);

        // 3️⃣ Lấy giá
        const priceText = await page.evaluate(() => {
            const el = document.querySelector('span.new-price');
            return el ? el.innerText : null;
        });

        const price = extractPrice(priceText);

        const item = {
            id,
            url
        };

        if (aiData.power !== undefined) item.power = aiData.power;
        if (aiData.capacity !== undefined) item.capacity = aiData.capacity;
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
