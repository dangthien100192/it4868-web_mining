import { MongoClient } from 'mongodb';

// ================= DB CONFIG =================
const uri = "mongodb://admin:admin@203.113.132.140:8000/?authSource=admin";
const DB_NAME = "mydb";

// ================= COLLECTIONS =================
const COLLECTIONS = [
    { name: "product_backup_charger", category: "backup_charger" },
    // { name: "product_headphone", category: "headphone" },
    // { name: "product_case", category: "case" },
    // { name: "product_screen_protector", category: "screen_protector" }
];

// ================= MAIN =================
(async () => {
    const client = new MongoClient(uri);
    await client.connect();
    console.log('✅ Connected MongoDB');

    const db = client.db(DB_NAME);

    for (const colInfo of COLLECTIONS) {
        console.log(`\n==============================`);
        console.log(`📂 COLLECTION: ${colInfo.name}`);
        console.log(`==============================`);

        const col = db.collection(colInfo.name);

        // 1️⃣ Lấy sản phẩm có price
        const products = await col.find({
            price: { $type: "number", $gt: 0 }
        }).toArray();

        console.log(`📦 Found ${products.length} products with price`);

        if (products.length === 0) {
            console.log('⚠ Không có sản phẩm hợp lệ');
            continue;
        }

        // 2️⃣ Tính min / max
        const prices = products.map(p => p.price);
        const minPrice = Math.min(...prices);
        const maxPrice = Math.max(...prices);

        console.log(`💰 PRICE RANGE: ${minPrice} → ${maxPrice}`);

        // 3️⃣ Update từng product
        let updated = 0;

        for (const p of products) {
            const priceRank =
                maxPrice !== minPrice
                    ? (p.price - minPrice) / (maxPrice - minPrice)
                    : 1;

            await col.updateOne(
                { _id: p._id },
                {
                    $set: {
                        price_rank: Number(priceRank.toFixed(4)),
                        category: colInfo.category
                    }
                }
            );

            updated++;
        }

        console.log(`✅ Updated ${updated} documents`);
    }

    await client.close();
    console.log('\n🎉 ALL DONE');
})();
