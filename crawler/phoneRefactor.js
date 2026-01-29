import puppeteer from 'puppeteer';
import { MongoClient } from 'mongodb';

const sleep = ms => new Promise(r => setTimeout(r, ms));

// ================= DB CONFIG =================
const uri = "mongodb://admin:admin@203.113.132.140:8000/?authSource=admin";
const DB_NAME = "mydb";
const COLLECTION = "product_phone";

// ================= UTILS =================
function normalizePrice(text) {
    if (!text) return null;
    return Number(text.replace(/[^\d]/g, ''));
}

// ================= MAIN =================
(async () => {
    const client = new MongoClient(uri);
    await client.connect();

    console.log('✅ Connected MongoDB');

    const db = client.db(DB_NAME);
    const col = db.collection(COLLECTION);

    // 1️⃣ Lấy toàn bộ phone đã có
    const products = await col.find({
        url: { $exists: true }
    }).toArray();

    console.log(`📦 Found ${products.length} phone products`);

    if (products.length === 0) {
        console.log('⚠ Không có product nào');
        return;
    }

    const browser = await puppeteer.launch({
        headless: false, // bật để debug
        slowMo: 30,
        defaultViewport: null
    });

    const page = await browser.newPage();

    const priceMap = new Map();

    // 2️⃣ Crawl giá
    for (let i = 0; i < products.length; i++) {
        const p = products[i];
        console.log(`\n📄 [${i + 1}/${products.length}] ${p.url}`);

        try {
            await page.goto(p.url, {
                waitUntil: 'networkidle2',
                timeout: 60000
            });

            await sleep(1000);

            const priceText = await page.evaluate(() =>
                document.querySelector('span.new-price')?.innerText || ''
            );

            const price = normalizePrice(priceText);

            if (price) {
                priceMap.set(p._id.toString(), price);
                console.log(`💰 Price: ${price}`);
            } else {
                console.log('⚠ Không tìm thấy giá');
            }

        } catch (err) {
            console.log(`❌ Error: ${err.message}`);
        }

        await sleep(800);
    }

    await browser.close();

    // 3️⃣ Tính rank giá
    const prices = [...priceMap.values()];
    if (prices.length === 0) {
        console.log('❌ Không crawl được giá nào');
        return;
    }

    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);

    console.log(`📊 PRICE RANGE: ${minPrice} → ${maxPrice}`);

    // 4️⃣ Update DB (KHÔNG INSERT)
    for (const p of products) {
        const price = priceMap.get(p._id.toString());
        if (!price) continue;

        const priceRank =
            maxPrice !== minPrice
                ? (price - minPrice) / (maxPrice - minPrice)
                : 1;

        await col.updateOne(
            { _id: p._id },
            {
                $set: {
                    price,
                    price_rank: Number(priceRank.toFixed(4)),
                    category: "phone"
                }
            }
        );

        console.log(`✅ Updated ${p.id || p._id}`);
    }

    await client.close();
    console.log('\n🎉 DONE: price + rank + category updated');
})();
