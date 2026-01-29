const { MongoClient } = require("mongodb");

const uri = "mongodb://admin:admin@203.113.132.140:8000/?authSource=admin";
const client = new MongoClient(uri);

function enrichPhoneDetail(name = "") {
    const n = name.toLowerCase();

    let result = {
        phone_brand: null,
        operating_system: null,
        phone_generation: null,
        phone_variant: "base",
        phone_series: null,
        supported_connection: []
    };

    // ================= iPhone =================
    if (n.includes("iphone")) {
        result.phone_brand = "iPhone";
        result.operating_system = "iOS";
        result.phone_series = "iPhone";

        // generation
        const genMatch = n.match(/iphone\s?(x|xr|xs|\d{1,2})/);
        if (genMatch) {
            const g = genMatch[1];
            result.phone_generation =
                g === "x" || g === "xr" || g === "xs" ? 10 : parseInt(g);
        }

        // variant
        if (n.includes("pro max")) result.phone_variant = "promax";
        else if (n.includes("pro")) result.phone_variant = "pro";
        else if (n.includes("plus")) result.phone_variant = "plus";
        else if (n.includes("mini")) result.phone_variant = "mini";

        result.supported_connection = [
            "wifi",
            "bluetooth",
            "cellular",
            result.phone_generation >= 15 ? "type_C" : "lightning"
        ];

        return result;
    }

    // ================= Samsung =================
    if (n.includes("samsung") || n.includes("galaxy")) {
        result.phone_brand = "Samsung";
        result.operating_system = "Android";

        if (n.includes("galaxy s")) result.phone_series = "Galaxy S";
        else if (n.includes("galaxy a")) result.phone_series = "Galaxy A";
        else if (n.includes("galaxy z")) result.phone_series = "Galaxy Z";
        else if (n.includes("note")) result.phone_series = "Galaxy Note";

        // generation (S23, A15, Z Fold 5...)
        const genMatch = n.match(/(s|a|fold|flip|note)\s?(\d{1,2})/);
        if (genMatch) {
            result.phone_generation = parseInt(genMatch[2]);
        }

        // variant
        if (n.includes("ultra")) result.phone_variant = "ultra";
        else if (n.includes("fe")) result.phone_variant = "fe";
        else if (n.includes("plus")) result.phone_variant = "plus";

        result.supported_connection = [
            "wifi",
            "bluetooth",
            "cellular",
            "type_C"
        ];

        return result;
    }

    // ================= Xiaomi =================
    if (n.includes("xiaomi") || n.includes("redmi")) {
        result.phone_brand = "Xiaomi";
        result.operating_system = "Android";

        if (n.includes("redmi note")) result.phone_series = "Redmi Note";
        else if (n.includes("redmi")) result.phone_series = "Redmi";
        else result.phone_series = "Xiaomi";

        const genMatch = n.match(/note\s?(\d{1,2})|xiaomi\s?(\d{1,2})/);
        if (genMatch) {
            result.phone_generation = parseInt(genMatch[1] || genMatch[2]);
        }

        if (n.includes("pro plus")) result.phone_variant = "pro+";
        else if (n.includes("pro")) result.phone_variant = "pro";

        result.supported_connection = [
            "wifi",
            "bluetooth",
            "cellular",
            "type_C"
        ];

        return result;
    }

    return null;
}

async function run() {
    try {
        await client.connect();
        console.log("✅ Mongo connected");

        const db = client.db("mydb"); // đổi nếu DB khác
        const products = db.collection("products");
        const productPhone = db.collection("product_phone");

        const allProducts = await products.find({}).toArray();
        console.log(`ℹ️ Tìm thấy ${allProducts.length} sản phẩm trong products`);

        const phones = [];

        for (const p of allProducts) {
            console.log(`🔍 Xử lý sản phẩm: ${p.product_name}`);
            const extra = enrichPhoneDetail(p.product_name);
            if (!extra) continue;

            phones.push({
                ...p,
                ...extra,
                source_product_id: p._id,   // trace lại data gốc
                created_at: new Date()
            });
        }

        if (phones.length === 0) {
            console.log("⚠️ Không có sản phẩm điện thoại");
            return;
        }

        // clear cũ nếu muốn (optional)
        // await productPhone.deleteMany({});

        await productPhone.insertMany(phones);

        console.log(`🎉 Đã insert ${phones.length} sản phẩm vào product_phone`);

    } catch (err) {
        console.error("❌ Lỗi:", err);
    } finally {
        await client.close();
    }
}

run();
