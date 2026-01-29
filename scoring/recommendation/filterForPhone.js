import { MongoClient } from "mongodb";

/**
 * =====================
 * CONFIG
 * =====================
 */
const uri = "mongodb://admin:admin@203.113.132.140:8000/?authSource=admin";
const DB_NAME = "mydb";

const COLLECTIONS = {
    phone: "product_phone",
    case: "product_case",
    screen_protector: "product_screen_protector",
    backup_charger: "product_backup_charger",
    headphone: "product_headphone"
};

/**
 * =====================
 * HELPERS
 * =====================
 */

// headphone connections: empty => bluetooth
function normalizeHeadphoneConnections(h) {
    if (!h.connections || h.connections.length === 0) {
        return ["bluetooth"];
    }
    return h.connections.map(c => c.toLowerCase());
}

/**
 * =====================
 * MATCH RULES
 * =====================
 */

function matchVariant(models, phoneVariant) {
    const text = models.join(" ").toLowerCase();

    const variant = (phoneVariant || "")
        .toLowerCase()
        .replace(/[-_]/g, " ")
        .replace(/\s+/g, " ")
        .trim();

    const isBase = !variant || ["base", "standard"].includes(variant);
    const isProMax = /pro\s*max/.test(variant);
    const isPro = /\bpro\b/.test(variant) && !isProMax;
    const isMax = /\bmax\b/.test(variant) && !isProMax;

    if (isBase) {
        return !/(pro|max|plus|ultra|lite|mini|fe|\bs\b)/.test(text);
    }

    if (isProMax) {
        return /pro\s*max|promax/.test(text);
    }

    if (isPro) {
        return /\bpro\b/.test(text) && !/pro\s*max|promax/.test(text);
    }

    if (isMax) {
        return /\bmax\b/.test(text) && !/pro\s*max|promax/.test(text);
    }

    return new RegExp(`\\b${variant}\\b`).test(text);
}

// CASE
function matchCase(phone, cases) {
    return cases.filter(c => {
        if (!c.models || !c.price || c.price <= 0) return false;

        const models = c.models.map(m => m.toLowerCase());

        const generationMatch = models.some(m =>
            m.includes(phone.phone_generation?.toString())
        );

        const brandMatch = models.some(m =>
            m.includes(phone.phone_brand?.toLowerCase())
        );

        const variantMatch = matchVariant(models, phone.phone_variant?.toLowerCase());

        return generationMatch && brandMatch && variantMatch;
    });
}

// SCREEN PROTECTOR
function matchScreenProtector(phone, protectors) {
    return protectors.filter(c => {
        if (!c.models || !c.price || c.price <= 0) return false;

        const models = c.models.map(m => m.toLowerCase());

        const generationMatch = models.some(m =>
            m.includes(phone.phone_generation?.toString())
        );

        const brandMatch = models.some(m =>
            m.includes(phone.phone_brand?.toLowerCase())
        );

        const variantMatch = matchVariant(models, phone.phone_variant?.toLowerCase());

        return generationMatch && brandMatch && variantMatch;
    });
}

// BACKUP CHARGER (compatible với mọi phone)
function matchBackupCharger(_phone, chargers) {
    return chargers.filter(c => c.price && c.price > 0);
}

// HEADPHONE
function matchHeadphone(phone, headphones) {
    return headphones.filter(h => {
        const phoneConns = (phone.supported_connection || []).map(c => c.toLowerCase());
        const hpConns = normalizeHeadphoneConnections(h);

        if (!h.price || h.price <= 0) {
            return false;
        }

        // bluetooth luôn match nếu phone có bluetooth
        if (hpConns.includes("bluetooth")) {
            return phoneConns.includes("bluetooth");
        }

        // jack 3.5mm (rule mở rộng)
        if (hpConns.includes("3.5mm")) {
            return phoneConns.includes("3.5mm");
        }

        return false;
    });
}

/**
 * =====================
 * MAIN FILTER
 * =====================
 */
function filterAccessoriesForPhone(phone, data) {
    return {
        phone_id: phone.source_product_id,
        phone_name: phone.product_name,
        phone: phone,
        case: matchCase(phone, data.cases),
        screen_protector: matchScreenProtector(phone, data.screen_protectors),
        backup_charger: matchBackupCharger(phone, data.backup_chargers),
        headphone: matchHeadphone(phone, data.headphones)
    };
}

/**
 * =====================
 * RUN
 * =====================
 */
async function run() {
    const client = new MongoClient(uri);

    try {
        await client.connect();
        console.log("✅ Mongo connected");

        const db = client.db(DB_NAME);

        // READ ONLY
        let phones = await db.collection(COLLECTIONS.phone).find({}).toArray();
        const cases = await db.collection(COLLECTIONS.case).find({}).toArray();
        const screenProtectors = await db
            .collection(COLLECTIONS.screen_protector)
            .find({})
            .toArray();
        const backupChargers = await db
            .collection(COLLECTIONS.backup_charger)
            .find({})
            .toArray();
        const headphones = await db
            .collection(COLLECTIONS.headphone)
            .find({})
            .toArray();

        // phones = phones.slice(0, 1); // TESTING LIMIT

        // FILTER cho từng phone
        const results = phones.map(phone =>
            filterAccessoriesForPhone(phone, {
                cases,
                screen_protectors: screenProtectors,
                backup_chargers: backupChargers,
                headphones
            })
        );

        // 👉 nếu muốn SAVE ra collection mới (OPTIONAL)
        await db.collection("phone_accessory_map").insertMany(
            results.map(r => ({
                ...r,
                created_at: new Date()
            }))
        );

    } catch (err) {
        console.error("❌ Error:", err);
    } finally {
        await client.close();
    }
}

run();
