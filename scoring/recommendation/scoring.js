import {
    ACCESSORY_PRICE_RATIO,
} from "./recommendRule.js";

/**
 * =====================
 * SCORE WEIGHT CONFIG
 * =====================
 */
const SCORE_WEIGHT = {
    price_fit: 0.4,
    price_rank: 0.3,      // 👈 thêm rule phân khúc
    ecosystem_fit: 0.15,
    quality: 0.1,
    compatibility: 0.05,
};

const FINAL_WEIGHT = {
    local: 0.7,
    external: 0.3,
};

/**
 * =====================
 * HELPERS
 * =====================
 */

function safeScoreFallback(item, reason) {
    return {
        ...(item || {}),
        score_total: 0,
        score_detail: {},
        score_error: reason,
    };
}

function clamp01(val) {
    return Math.max(0, Math.min(1, val));
}

function priceFit(phonePrice, accPrice, category) {
    if (!phonePrice || phonePrice <= 0) return 0;
    if (!accPrice || accPrice <= 0) return 0;

    const rule = ACCESSORY_PRICE_RATIO[category];
    if (!rule) return 0;

    const ratio = accPrice / phonePrice;
    if (ratio < rule.min || ratio > rule.max) return 0;

    const mid = (rule.min + rule.max) / 2;
    return clamp01(1 - Math.abs(ratio - mid) / mid);
}

function priceRankSimilarity(phoneRank, accRank) {
    if (phoneRank == null || accRank == null) return 0;

    const diff = Math.abs(phoneRank - accRank);
    return clamp01(1 - diff);
}

/**
 * =====================
 * MAIN SCORING
 * =====================
 */
export async function scoreItem(phone, item, category) {
    // ---- HARD NULL CHECK ----
    if (!phone) {
        console.error("[scoreItem] ❌ phone missing");
        return safeScoreFallback(item, "PHONE_MISSING");
    }

    if (!item) {
        console.error(
            `[scoreItem] ❌ item missing | phone_id=${phone.source_product_id}`
        );
        return safeScoreFallback(null, "ITEM_MISSING");
    }

    if (!category) {
        console.error(
            `[scoreItem] ❌ category missing | phone_id=${phone.source_product_id}`
        );
        return safeScoreFallback(item, "CATEGORY_MISSING");
    }

    // ---- PRICE ----
    const phonePrice = phone.price ?? phone.product_price ?? 0;
    const accPrice = item.price ?? 0;

    // ---- PRICE RANK (đã crawl sẵn) ----
    const phonePriceRank = phone.price_rank;
    const accPriceRank = item.price_rank;

    if (phonePriceRank == null) {
        console.warn(
            `[scoreItem] ⚠ phone price_rank missing | phone_id=${phone.source_product_id}`
        );
    }

    if (accPriceRank == null) {
        console.warn(
            `[scoreItem] ⚠ accessory price_rank missing | item_id=${item.id || item._id}`
        );
    }

    // ---- SCORE RULES ----
    const price_fit = priceFit(phonePrice, accPrice, category);
    const price_rank = priceRankSimilarity(phonePriceRank, accPriceRank);

    const ecosystem_fit = 0;
    const quality = 0;
    const compatibility = 0;

    // ---- LOCAL SCORE ----
    const local_score =
        price_fit * SCORE_WEIGHT.price_fit +
        price_rank * SCORE_WEIGHT.price_rank +
        ecosystem_fit * SCORE_WEIGHT.ecosystem_fit +
        quality * SCORE_WEIGHT.quality +
        compatibility * SCORE_WEIGHT.compatibility;

    // ---- FINAL SCORE ----
    const score_total = local_score * FINAL_WEIGHT.local;

    return {
        ...item,
        score_total,
        score_detail: {
            accPrice,
            phonePrice,
            price_fit,
            price_rank,
            ecosystem_fit,
            quality,
            compatibility,
            local_score,
        },
    };
}
