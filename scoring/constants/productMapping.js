/**
 * CATEGORY → RECOMMEND CATEGORY MAPPING
 * Dùng cho filter ứng viên ban đầu
 */
export const CATEGORY_RECOMMEND_MAPPING = {
    phone: [
        "case",
        "screen_protector",
        "backup_charger",
        "headphone",
    ],
};

/**
 * CATEGORY COMPATIBILITY RULE
 * Dùng cho rule compatibility (must-have)
 */
export const COMPATIBILITY_RULE = {
    case: {
        requireModelCode: true
    },

    screen_protector: {
        requireModelCode: true
    },

    headphone: {
        requirePort: true
    },
};

/**
 * ACCESSORY PRICE RATIO
 * Rule phân khúc chi tiêu (spending tier)
 */
export const ACCESSORY_PRICE_RATIO = {
    case: {
        min: 0.005,
        max: 0.02
    },
    screen_protector: {
        min: 0.003,
        max: 0.01
    },
    backup_charger: {
        min: 0.01,
        max: 0.03
    },
    headphone: {
        min: 0.03,
        max: 0.1
    }
};

/**
 * PRODUCT SPENDING TIER
 * Dùng cho anchor product
 */
export const SPENDING_TIER = {
    entry: {
        min: 0,
        max: 10_000_000
    },
    mid: {
        min: 10_000_000,
        max: 25_000_000
    },
    high: {
        min: 25_000_000,
        max: 45_000_000
    },
    ultra: {
        min: 45_000_000,
        max: Infinity
    }
};

/**
 * ECOSYSTEM FIT SCORE
 * Dùng cho scoring rule hệ sinh thái
 */
export const ECOSYSTEM_FIT_SCORE = {
    apple: {
        apple: 1.0,
        mfi: 0.9,
        generic: 0.6
    },
    samsung: {
        samsung: 1.0,
        generic: 0.7
    }
};

/**
 * QUALITY TIER → FEATURE SCORE (fallback)
 */
export const QUALITY_TIER_SCORE = {
    low: 0.4,
    mid: 0.7,
    high: 0.9,
    premium: 1.0
};
