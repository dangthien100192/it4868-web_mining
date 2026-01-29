import { getDb } from "./mongo.js";
import { buildRecommendation } from "./buildRecommendation.js";

const SOURCE_COLLECTION = "product_phone";
const TARGET_COLLECTION = "recommendation_phone";

async function run() {
    const { db, client } = await getDb();

    try {
        let phones = await db
            .collection(SOURCE_COLLECTION)
            .find({})
            .toArray();

        // phones = phones.slice(5, 6); // TESTING LIMIT

        const docs = [];

        for (const phone of phones) {
            const recommendation = await buildRecommendation(phone);

            docs.push({
                phone,
                recommendation,
                created_at: new Date(),
            });
        }

        await db.collection(TARGET_COLLECTION).deleteMany({});
        if (docs.length) {
            await db.collection(TARGET_COLLECTION).insertMany(docs);
        }

        console.log(
            `✅ Saved ${docs.length} recommendations into ${TARGET_COLLECTION}`
        );
    } finally {
        await client.close();
    }
}

run();
