export const CATEGORY_RECOMMEND_MAPPING = {
    phone: ["case", "screen_protector", "backup_charger", "headphone"],
};

export const ACCESSORY_PRICE_RATIO = {
    case: { min: 0.005, max: 0.02 },
    screen_protector: { min: 0.003, max: 0.01 },
    backup_charger: { min: 0.01, max: 0.03 },
    headphone: { min: 0.03, max: 0.1 },
};

export const ECOSYSTEM_FIT_SCORE = {
    apple: { apple: 1.0, mfi: 0.9, generic: 0.6 },
    samsung: { samsung: 1.0, generic: 0.7 },
};

export const QUALITY_TIER_SCORE = {
    low: 0.4,
    mid: 0.7,
    high: 0.9,
    premium: 1.0,
};
