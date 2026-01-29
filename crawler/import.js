import fs from "fs";
import path from "path";
import { MongoClient } from "mongodb";

const uri = "mongodb://admin:admin@203.113.132.140:8000/?authSource=admin";
const client = new MongoClient(uri);

const DB_NAME = "mydb";

// mapping file → collection
const FILE_COLLECTION_MAP = {
    // "product-mobile-phone.json": "product_phone",
    // "product-case.json": "product_case",
    // "product-headphone.json": "product_headphone"
    // "product-screen-protector.json": "product_screen_protector",
    "product-back-up-charger_1.json": "product_backup_charger",
};

async function run() {
    try {
        await client.connect();
        console.log("✅ Mongo connected");

        const db = client.db(DB_NAME);

        for (const [file, collectionName] of Object.entries(FILE_COLLECTION_MAP)) {
            const filePath = path.join("./", file);

            if (!fs.existsSync(filePath)) {
                console.warn(`⚠️ Skip ${file} (not found)`);
                continue;
            }

            const raw = fs.readFileSync(filePath, "utf-8");
            const data = JSON.parse(raw);

            if (!Array.isArray(data)) {
                console.error(`❌ ${file} không phải JSON array`);
                continue;
            }

            const collection = db.collection(collectionName);

            const docs = data.map(d => ({
                ...d,
                created_at: new Date(),
                data_source: file
            }));

            await collection.insertMany(docs);
            console.log(`🎉 Imported ${docs.length} → ${collectionName}`);
        }

    } catch (e) {
        console.error("❌ Error:", e);
    } finally {
        await client.close();
    }
}

run();
