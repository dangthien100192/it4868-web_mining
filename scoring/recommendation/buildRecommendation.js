import { CATEGORY_RECOMMEND_MAPPING } from "./recommendRule.js";
import { scoreItem } from "./scoring.js";
import { getDb } from "./mongo.js";

export async function buildRecommendation(phone) {
    const result = {};

    // =====================
    // INPUT VALIDATION
    // =====================
    if (!phone) {
        console.error("[buildRecommendation] ❌ phone is null/undefined");
        return result;
    }

    if (!phone.source_product_id) {
        console.error(
            "[buildRecommendation] ❌ phone.source_product_id missing",
            phone
        );
        return result;
    }

    console.log(
        `[buildRecommendation] ▶ Start | phone_id=${phone.source_product_id} | phone_name=${phone.product_name}`
    );

    const { db } = await getDb();

    // =====================
    // LOAD FILTERED MAP
    // =====================
    const filteredPhoneMap = await db
        .collection("phone_accessory_map")
        .findOne({ phone_id: phone.source_product_id });

    if (!filteredPhoneMap) {
        console.error(
            `[buildRecommendation] ❌ No accessory map found | phone_id=${phone.source_product_id}`
        );
        return result;
    }

    console.log(
        `[buildRecommendation] ✔ Accessory map loaded | phone_id=${phone.source_product_id}`
    );

    // =====================
    // SCORING PER CATEGORY
    // =====================
    for (const category of CATEGORY_RECOMMEND_MAPPING.phone) {
        const rawCandidates = filteredPhoneMap[category] || [];

        console.log(
            `[buildRecommendation] ▶ Category=${category} | raw_candidates=${rawCandidates.length}`
        );

        if (rawCandidates.length === 0) {
            console.warn(
                `[buildRecommendation] ⚠ No candidates | category=${category} | phone_id=${phone.source_product_id}`
            );
            result[category] = [];
            continue;
        }

        const validCandidates = rawCandidates.filter(i => {
            if (!i) {
                console.warn(
                    `[buildRecommendation] ⚠ Null item | category=${category}`
                );
                return false;
            }

            if (!i.price || i.price <= 0) {
                console.warn(
                    `[buildRecommendation] ⚠ Invalid price | category=${category} | item_id=${i.id || i._id}`
                );
                return false;
            }

            if (typeof i.name === "string" && i.name.trim() === "") {
                console.warn(
                    `[buildRecommendation] ⚠ Empty name | category=${category} | item_id=${i.id || i._id}`
                );
                return false;
            }

            return true;
        });

        console.log(
            `[buildRecommendation] ✔ Valid candidates | category=${category} | count=${validCandidates.length}`
        );

        const scored = await Promise.all(
            validCandidates.map(i =>
                scoreItem(
                    filteredPhoneMap.phone || phone,
                    i,
                    category
                )
            )
        );

        const ranked = scored
            .filter(s => {
                if (!s) return false;
                if (s.score_total === 0) {
                    console.warn(
                        `[buildRecommendation] ⚠ Zero score | category=${category} | item_id=${s.id || s._id}`
                    );
                }
                return true;
            })
            .sort((a, b) => b.score_total - a.score_total)
            .slice(0, 10);

        console.log(
            `[buildRecommendation] ✔ Top results | category=${category} | top=${ranked.length}`
        );

        result[category] = ranked;
    }

    console.log(
        `[buildRecommendation] ✅ Done | phone_id=${phone.source_product_id}`
    );

    return result;
}
