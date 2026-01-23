# app.py - Flask Backend API (DB=mydb, collection=products)
# Search strategy:
#  - MongoDB $text (optional, keyword-based)
#  - edge n-gram + tri-gram fields for fast prefix/contains search
#  - search_norm (normalized full text) for multi-word phrase search (fix "tai nghe" -> nồi cơm)

from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient, UpdateOne
import os
from datetime import datetime
from dotenv import load_dotenv
import unicodedata
import re

load_dotenv()

app = Flask(__name__)
CORS(app)

# =========================
# MongoDB config
# =========================
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_USERNAME = os.getenv("MONGODB_USERNAME", "")
MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD", "")

DB_NAME = os.getenv("DB_NAME", "mydb")
PRODUCTS_COL = os.getenv("PRODUCTS_COL", "products")
RECOMMEND_COL = os.getenv("RECOMMEND_COL", "recommendation_products")

# =========================
# Mongo connect
# =========================
try:
    if MONGODB_USERNAME and MONGODB_PASSWORD:
        client = MongoClient(
            MONGODB_URI,
            username=MONGODB_USERNAME,
            password=MONGODB_PASSWORD,
            serverSelectionTimeoutMS=5000,
        )
    else:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)

    client.admin.command("ping")

    db = client[DB_NAME]
    products_collection = db[PRODUCTS_COL]
    recommendations_collection = db[RECOMMEND_COL]

    print("✅ Connected to MongoDB successfully")
    print(f"   DB={db.name} products={products_collection.name} recs={recommendations_collection.name}")
except Exception as e:
    print(f"❌ MongoDB connection error: {e}")
    raise

# =========================
# Helpers
# =========================
def serialize_doc(doc):
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

def vn_norm(s: str) -> str:
    """
    Normalize Vietnamese:
      - lower
      - remove diacritics
      - đ -> d
      - keep a-z0-9 and spaces
      - collapse spaces
    """
    if s is None:
        return ""
    s = str(s).lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.replace("đ", "d")
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    s = " ".join(s.split())
    return s

def words(text: str):
    t = vn_norm(text)
    return [w for w in t.split() if w]

def edge_ngrams_token(token: str, min_len=2, max_len=10):
    L = len(token)
    out = []
    for n in range(min_len, min(max_len, L) + 1):
        out.append(token[:n])
    return out

def trigrams_token(token: str):
    L = len(token)
    if L < 3:
        return []
    return [token[i:i+3] for i in range(0, L - 3 + 1)]

def extract_search_texts(p: dict):
    """
    Gather all searchable texts from product doc.
    """
    parts = []
    parts.append(p.get("product_id", ""))
    parts.append(p.get("product_name", ""))

    props = p.get("product_properties") or []
    if isinstance(props, list):
        for prop in props:
            if not isinstance(prop, dict):
                continue
            parts.append(prop.get("product_property", ""))
            vals = prop.get("property_values") or []
            if isinstance(vals, list):
                for v in vals:
                    if isinstance(v, dict):
                        parts.append(v.get("property_value", ""))
                    else:
                        parts.append(v)

    return [x for x in parts if x not in (None, "")]

def build_search_norm(p: dict, max_len: int = 1200) -> str:
    """
    A normalized searchable string used for phrase / multi-word search.
    Keep it capped to avoid huge docs.
    """
    texts = extract_search_texts(p)
    joined = " ".join(str(x) for x in texts if x)
    joined = vn_norm(joined)
    if len(joined) > max_len:
        joined = joined[:max_len]
    return joined

def build_search_edge(p: dict, min_len=2, max_len=10):
    """
    Edge tokens for prefix/autocomplete:
      - product_id (prefix tokens)
      - each word from name/properties -> prefix tokens
    """
    texts = extract_search_texts(p)
    tokens = []

    pid = vn_norm(p.get("product_id", ""))
    if pid:
        tokens.extend(edge_ngrams_token(pid, min_len=min_len, max_len=max_len))

    for t in texts:
        for w in words(t):
            tokens.extend(edge_ngrams_token(w, min_len=min_len, max_len=max_len))

    # unique preserve order
    return list(dict.fromkeys(tokens))

def build_search_trigrams(p: dict, max_tokens=1200):
    """
    Tri-gram tokens for contains-ish search.
    Storage control for 100k docs:
      - cap word length
      - cap total grams per doc
    """
    texts = extract_search_texts(p)
    grams = []

    for t in texts:
        for w in words(t):
            if len(w) > 32:
                w = w[:32]
            grams.extend(trigrams_token(w))
            if len(grams) >= max_tokens:
                break
        if len(grams) >= max_tokens:
            break

    grams = list(dict.fromkeys(grams))
    return grams[:max_tokens]

def sample_query_grams(search_term: str, max_grams=6):
    """
    Query grams should NOT be too many.
    We will use $in, not $all (to avoid false positives & over-strictness).
    """
    grams = []
    for w in words(search_term):
        grams.extend(trigrams_token(w))
    grams = list(dict.fromkeys(grams))
    return grams[:max_grams]

def parse_score(value):
    """
    Normalize similarity score:
      - if None -> 0
      - if > 1 and <= 100: treat as percentage => /100
      - clamp 0..1
    """
    if value is None:
        return 0.0
    try:
        x = float(value)
    except Exception:
        return 0.0

    # common case: stored as 0..100
    if x > 1.0 and x <= 100.0:
        x = x / 100.0
    # if accidentally stored 0..1000 etc just clamp
    if x < 0:
        x = 0.0
    if x > 1:
        x = 1.0
    return float(x)

# =========================
# API Endpoints
# =========================
@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "success": True,
        "message": "Server is running",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route("/api/admin/create-text-index", methods=["POST"])
def create_text_index():
    """
    Create MongoDB text index for keyword search ($text).
    Note: $text is token-based; it won't match partial product_id well.
    """
    try:
        index_name = "idx_products_text_all"
        existing = products_collection.index_information()
        if index_name in existing:
            return jsonify({"success": True, "message": "Index already exists", "index": index_name})

        products_collection.create_index(
            [
                ("product_name", "text"),
                ("product_id", "text"),
                ("product_properties.product_property", "text"),
                ("product_properties.property_values.property_value", "text"),
            ],
            name=index_name,
            default_language="none"
        )

        return jsonify({"success": True, "message": "Created text index", "index": index_name})
    except Exception as e:
        print(f"Error creating text index: {e}")
        return jsonify({"success": False, "error": "Lỗi tạo text index"}), 500

@app.route("/api/admin/build-ngrams", methods=["POST"])
def admin_build_ngrams():
    """
    Build fields:
      - search_norm: normalized full text (phrase search)
      - search_edge: edge n-gram tokens (prefix/autocomplete)
      - search_trg: tri-gram tokens (contains-ish)

    Tuned defaults for ~100k docs, avg text length ~200:
      - batch=1000
      - max_edge=10
      - max_trg_tokens=1200

    Query params:
      - batch (default 1000, max 5000)
      - only_missing=1 (default 1)
      - min_edge=2 (default 2)
      - max_edge=10 (default 10)
      - max_trg_tokens=1200 (default 1200)
    """
    try:
        batch = int(request.args.get("batch") or 1000)
        batch = max(1, min(batch, 5000))

        only_missing = (request.args.get("only_missing") or "1").strip() == "1"

        min_edge = int(request.args.get("min_edge") or 2)
        max_edge = int(request.args.get("max_edge") or 10)
        max_trg_tokens = int(request.args.get("max_trg_tokens") or 1200)

        existing = products_collection.index_information()

        # multikey indexes (for token arrays)
        if "idx_search_edge_1" not in existing:
            products_collection.create_index([("search_edge", 1)], name="idx_search_edge_1")
        if "idx_search_trg_1" not in existing:
            products_collection.create_index([("search_trg", 1)], name="idx_search_trg_1")
        # search_norm index
        if "idx_search_norm_1" not in existing:
            products_collection.create_index([("search_norm", 1)], name="idx_search_norm_1")

        filter_q = {}
        if only_missing:
            filter_q = {
                "$or": [
                    {"search_edge": {"$exists": False}},
                    {"search_trg": {"$exists": False}},
                    {"search_norm": {"$exists": False}},
                    {"search_edge": None},
                    {"search_trg": None},
                    {"search_norm": None},
                    {"search_edge": []},
                    {"search_trg": []},
                    {"search_norm": ""},
                ]
            }

        cursor = products_collection.find(
            filter_q,
            {"_id": 1, "product_id": 1, "product_name": 1, "product_properties": 1}
        ).batch_size(batch)

        ops = []
        updated = 0

        for p in cursor:
            edge = build_search_edge(p, min_len=min_edge, max_len=max_edge)
            trg = build_search_trigrams(p, max_tokens=max_trg_tokens)
            norm = build_search_norm(p)

            ops.append(UpdateOne(
                {"_id": p["_id"]},
                {"$set": {"search_norm": norm, "search_edge": edge, "search_trg": trg}}
            ))

            if len(ops) >= batch:
                res = products_collection.bulk_write(ops, ordered=False)
                updated += res.modified_count
                ops = []

        if ops:
            res = products_collection.bulk_write(ops, ordered=False)
            updated += res.modified_count

        return jsonify({
            "success": True,
            "message": "Built search_norm + search_edge + search_trg",
            "updated": updated,
            "indexes": ["idx_search_norm_1", "idx_search_edge_1", "idx_search_trg_1"],
            "params": {
                "batch": batch,
                "only_missing": only_missing,
                "min_edge": min_edge,
                "max_edge": max_edge,
                "max_trg_tokens": max_trg_tokens
            }
        })

    except Exception as e:
        print(f"Error admin_build_ngrams: {e}")
        return jsonify({"success": False, "error": "Lỗi build n-gram"}), 500

@app.route("/api/products", methods=["GET"])
def get_products():
    """
    Pagination params:
      - page (default 1)
      - limit (default 50, max 200)

    Response:
      success, count, total, page, pages, limit, strategy, data[]
    """
    try:
        search_term = (request.args.get("search") or "").strip()

        limit = int(request.args.get("limit") or 50)
        limit = max(1, min(limit, 200))

        page = int(request.args.get("page") or 1)
        page = max(1, page)
        skip = (page - 1) * limit

        projection = {
            "_id": 1,
            "product_id": 1,
            "product_name": 1,
            "url": 1,
            "product_properties": 1
        }

        # =========================
        # No search: simple paging
        # =========================
        if not search_term:
            total = products_collection.count_documents({})
            cursor = products_collection.find({}, projection).skip(skip).limit(limit)
            products = [serialize_doc(p) for p in cursor]

            pages = max(1, (total + limit - 1) // limit)
            return jsonify({
                "success": True,
                "count": len(products),
                "total": total,
                "page": page,
                "pages": pages,
                "limit": limit,
                "strategy": "all",
                "data": products
            })

        # =========================
        # Search: improved strategy
        # =========================
        norm = vn_norm(search_term)
        wlist = words(search_term)

        strategy = None
        query = None
        sort_spec = None
        projection_used = projection

        # (A) Multi-word: phrase search on search_norm (fix "tai nghe" matching irrelevant docs)
        if len(wlist) >= 2:
            strategy = "phrase"
            phrase = " ".join(wlist)
            # word boundary phrase match
            query = {"search_norm": {"$regex": r"\b" + re.escape(phrase) + r"\b"}}

            total = products_collection.count_documents(query)
            cursor = products_collection.find(query, projection).skip(skip).limit(limit)
            products = [serialize_doc(p) for p in cursor]

            pages = max(1, (total + limit - 1) // limit)
            return jsonify({
                "success": True,
                "count": len(products),
                "total": total,
                "page": page,
                "pages": pages,
                "limit": limit,
                "strategy": strategy,
                "data": products
            })

        # (B) Single-word: try $text quickly (only if it returns something)
        try:
            text_query = {
                "$text": {
                    "$search": search_term,
                    "$caseSensitive": False,
                    "$diacriticSensitive": False
                }
            }
            probe = list(products_collection.find(text_query, {"_id": 1}).limit(1))
            if probe:
                strategy = "text"
                query = text_query
                sort_spec = [("score", {"$meta": "textScore"})]
                projection_text = dict(projection)
                projection_text["score"] = {"$meta": "textScore"}
                projection_used = projection_text
        except Exception:
            strategy = None

        # (C) Edge n-gram (prefix)
        if strategy is None:
            strategy = "edge"
            if norm.isdigit() or len(norm) < 3:
                query = {"search_edge": norm}
            else:
                query = {"search_edge": wlist[0]} if wlist else {"search_edge": norm}

        total = products_collection.count_documents(query)
        cursor = products_collection.find(query, projection_used)
        if sort_spec:
            cursor = cursor.sort(sort_spec)
        cursor = cursor.skip(skip).limit(limit)
        products = [serialize_doc(p) for p in cursor]

        # (D) Fallback trigram: use $in (not $all) and fewer grams
        if total == 0:
            grams = sample_query_grams(search_term, max_grams=6)
            if grams:
                strategy = "trigram"
                query = {"search_trg": {"$in": grams}}
                total = products_collection.count_documents(query)

                cursor = products_collection.find(query, projection).skip(skip).limit(limit)
                products = [serialize_doc(p) for p in cursor]

        pages = max(1, (total + limit - 1) // limit)

        return jsonify({
            "success": True,
            "count": len(products),
            "total": total,
            "page": page,
            "pages": pages,
            "limit": limit,
            "strategy": strategy,
            "data": products
        })

    except Exception as e:
        print(f"Error fetching products: {e}")
        return jsonify({"success": False, "error": "Lỗi khi tìm kiếm sản phẩm"}), 500

@app.route("/api/products/<product_id>", methods=["GET"])
def get_product_detail(product_id):
    try:
        product = products_collection.find_one({"product_id": product_id})
        if not product:
            return jsonify({"success": False, "error": "Không tìm thấy sản phẩm"}), 404
        return jsonify({"success": True, "data": serialize_doc(product)})
    except Exception as e:
        print(f"Error fetching product: {e}")
        return jsonify({"success": False, "error": "Lỗi khi lấy thông tin sản phẩm"}), 500

@app.route("/api/recommendations/<product_id>", methods=["GET"])
def get_recommendations(product_id):
    """
    Returns recommended products enriched with real product info (name/url/properties)
    and normalized similarity_score in range 0..1.
    """
    try:
        recommendation = recommendations_collection.find_one({"product_id": product_id})
        if not recommendation or "recommended_products" not in recommendation:
            return jsonify({"success": True, "count": 0, "data": []})

        rec_list = recommendation.get("recommended_products") or []
        rec_ids = [r.get("product_id") for r in rec_list if r.get("product_id")]

        # fetch real products so UI can show product_properties
        prod_map = {}
        if rec_ids:
            cur = products_collection.find(
                {"product_id": {"$in": rec_ids}},
                {"_id": 0, "product_id": 1, "product_name": 1, "url": 1, "product_properties": 1}
            )
            for p in cur:
                prod_map[p["product_id"]] = p

        enriched = []
        for r in rec_list:
            rid = r.get("product_id")
            if not rid:
                continue

            raw_score = r.get("similarity_score", None)
            if raw_score is None:
                raw_score = r.get("score", 0)

            score = parse_score(raw_score)

            pinfo = prod_map.get(rid, {})
            enriched.append({
                "product_id": rid,
                "product_name": pinfo.get("product_name") or r.get("product_name"),
                "url": pinfo.get("url") or r.get("url"),
                "product_properties": pinfo.get("product_properties", r.get("product_properties", [])),
                "similarity_score": score,
                "reasons": r.get("reasons", [])
            })

        enriched.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)

        return jsonify({
            "success": True,
            "count": len(enriched),
            "data": enriched
        })

    except Exception as e:
        print(f"Error fetching recommendations: {e}")
        return jsonify({"success": False, "error": "Lỗi khi lấy sản phẩm gợi ý"}), 500

@app.route("/api/products/<product_id>/with-recommendations", methods=["GET"])
def get_product_with_recommendations(product_id):
    """
    Convenience endpoint: returns product detail + recommendations (enriched).
    """
    try:
        product = products_collection.find_one({"product_id": product_id})
        if not product:
            return jsonify({"success": False, "error": "Không tìm thấy sản phẩm"}), 404
        product = serialize_doc(product)

        rec_resp = get_recommendations(product_id)
        # get_recommendations already returns a Flask response; extract json if possible
        try:
            rec_json = rec_resp.get_json()
        except Exception:
            rec_json = {"success": True, "count": 0, "data": []}

        return jsonify({
            "success": True,
            "data": {
                "product": product,
                "recommendations": rec_json.get("data", [])
            }
        })

    except Exception as e:
        # noinspection PyPackageRequirements
        print(f"Error fetching product with recommendations: {e}")
        return jsonify({"success": False, "error": "Lỗi khi lấy thông tin"}), 500

# =========================
# Run
# =========================
if __name__ == "__main__":
    PORT = int(os.getenv("PORT", 3001))
    print(f"🚀 Server is running on port {PORT}")
    print(f"📡 API URL: http://localhost:{PORT}/api")
    app.run(host="0.0.0.0", port=PORT, debug=True)
