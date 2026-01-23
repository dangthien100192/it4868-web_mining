# frontend.py - Streamlit UI (Load More)
import streamlit as st
import requests
import os
from dotenv import load_dotenv
from urllib.parse import urlencode

load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:3001/api")

st.set_page_config(
    page_title="Hệ thống Gợi ý Sản phẩm",
    page_icon="🛍️",
    layout="wide"
)

# =========================
# CSS
# =========================
st.markdown("""
<style>
.product-card {
  background: white;
  padding: 16px;
  border-radius: 10px;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.product-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.14); }

.recommendation-badge {
  background: #2563eb;
  color: white;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: bold;
}

a.product-link { text-decoration: none; color: #111827; }
a.product-link:hover { text-decoration: underline; }

.small-muted { color: #6b7280; font-size: 12px; }

.props {
  margin-top: 6px;
  color: #374151;
  font-size: 13px;
  line-height: 1.5;
}
.props b { color: #111827; }

/* fixed load-more bar */
.fixed-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9999;
  padding: 10px 14px;
  background: rgba(15, 23, 42, 0.92);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(255,255,255,0.10);
}
.fixed-bar .wrap {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
}
.fixed-bar .info {
  color: #e5e7eb;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.content-bottom-pad { height: 92px; }
</style>
""", unsafe_allow_html=True)

# =========================
# Session state
# =========================
if "keyword" not in st.session_state:
    st.session_state.keyword = ""
if "page_size" not in st.session_state:
    st.session_state.page_size = 20

# load-more state
if "products" not in st.session_state:
    st.session_state.products = []
if "page" not in st.session_state:
    st.session_state.page = 0  # 0 = chưa load trang nào
if "total" not in st.session_state:
    st.session_state.total = 0
if "has_more" not in st.session_state:
    st.session_state.has_more = False
if "strategy" not in st.session_state:
    st.session_state.strategy = ""

# Cache recommendations per product_id
if "recs_cache" not in st.session_state:
    st.session_state.recs_cache = {}
if "recs_open" not in st.session_state:
    st.session_state.recs_open = set()

# =========================
# Helpers
# =========================
def safe_str(x):
    return "" if x is None else str(x)

def render_properties(product: dict, max_items: int = 6) -> str:
    props = product.get("product_properties") or []
    if not isinstance(props, list) or not props:
        return ""

    lines = []
    for prop in props:
        if not isinstance(prop, dict):
            continue

        key = safe_str(prop.get("product_property", "")).strip()
        vals = prop.get("property_values") or []
        if not key or not isinstance(vals, list) or not vals:
            continue

        vlist = []
        for v in vals[:3]:
            if isinstance(v, dict):
                vv = safe_str(v.get("property_value", "")).strip()
            else:
                vv = safe_str(v).strip()
            if vv:
                vlist.append(vv)

        if vlist:
            lines.append(f"<div><b>{key}:</b> {', '.join(vlist)}</div>")

        if len(lines) >= max_items:
            break

    return f"<div class='props'>{''.join(lines)}</div>" if lines else ""

# =========================
# API calls
# =========================
def api_get_products(search: str, page: int, limit: int):
    params = {"limit": limit, "page": page}
    if search:
        params["search"] = search
    url = f"{API_URL}/products?{urlencode(params)}"
    res = requests.get(url, timeout=30)
    res.raise_for_status()
    return res.json()

def api_get_recommendations(product_id: str):
    res = requests.get(f"{API_URL}/recommendations/{product_id}", timeout=30)
    res.raise_for_status()
    return res.json()

# =========================
# Load logic
# =========================
def reset_search():
    st.session_state.products = []
    st.session_state.page = 0
    st.session_state.total = 0
    st.session_state.has_more = False
    st.session_state.strategy = ""
    st.session_state.recs_open = set()

def load_more():
    next_page = st.session_state.page + 1

    with st.spinner("Đang tải dữ liệu..."):
        data = api_get_products(st.session_state.keyword, next_page, st.session_state.page_size)

    if not data.get("success"):
        st.error("❌ API trả về lỗi.")
        return

    new_items = data.get("data", []) or []
    total = int(data.get("total", 0))
    pages = int(data.get("pages", 1))
    page = int(data.get("page", next_page))
    strategy = safe_str(data.get("strategy", ""))

    # append (tránh trùng product_id)
    seen = set([p.get("product_id") for p in st.session_state.products if p.get("product_id")])
    for it in new_items:
        pid = it.get("product_id")
        if pid and pid in seen:
            continue
        st.session_state.products.append(it)
        if pid:
            seen.add(pid)

    st.session_state.page = page
    st.session_state.total = total
    st.session_state.strategy = strategy
    st.session_state.has_more = (page < pages) and (len(new_items) > 0)

def load_first_page():
    reset_search()
    load_more()

# =========================
# UI
# =========================
st.title("🛍️ Hệ thống Gợi ý Sản phẩm")
st.markdown("### Tìm kiếm và xem gợi ý mua kèm")

with st.form("search_form", clear_on_submit=False):
    c1, c2, c3 = st.columns([7, 2, 2])  # FIX: bỏ vertical_alignment

    with c1:
        st.session_state.keyword = st.text_input(
            "search",
            value=st.session_state.keyword,
            placeholder="Ví dụ: tai nghe, cap sac, iphone, MQKJ3ZA, vivumax...",
            label_visibility="collapsed"
        )

    with c2:
        new_page_size = st.selectbox(
            "page_size",
            options=[10, 20, 50, 100],
            index=[10, 20, 50, 100].index(st.session_state.page_size),
            label_visibility="collapsed"
        )

    with c3:
        submitted = st.form_submit_button("🔍 Tìm", use_container_width=True)

# change page size => reload
if new_page_size != st.session_state.page_size:
    st.session_state.page_size = new_page_size
    if st.session_state.keyword.strip():
        load_first_page()
    else:
        reset_search()

# submit search
if submitted:
    if st.session_state.keyword.strip():
        load_first_page()
    else:
        reset_search()

st.markdown("## 📦 Danh sách sản phẩm")

products = st.session_state.products
total = st.session_state.total
loaded = len(products)

if not products:
    st.info("Nhập từ khóa và bấm 🔍 Tìm (hoặc nhấn Enter) để tải danh sách sản phẩm.")
else:
    extra = f" — strategy: {st.session_state.strategy}" if st.session_state.strategy else ""
    st.success(f"✅ Đang hiển thị {loaded} / {total} sản phẩm{extra}")

    for p in products:
        pid = safe_str(p.get("product_id", ""))
        pname = safe_str(p.get("product_name", ""))
        purl = safe_str(p.get("url", "#"))

        st.markdown(
            f"""
            <div class="product-card">
              <h3>
                <a class="product-link" href="{purl}" target="_blank" rel="noopener noreferrer">{pname}</a>
              </h3>
              {render_properties(p, max_items=6)}
            """,
            unsafe_allow_html=True
        )

        a1, a2, _ = st.columns([2, 2, 6])
        with a1:
            btn_label = "👁️‍🗨️ Ẩn gợi ý" if pid in st.session_state.recs_open else "💡 Gợi ý mua kèm"
            if st.button(btn_label, key=f"toggle_{pid}", use_container_width=True):
                if pid in st.session_state.recs_open:
                    st.session_state.recs_open.remove(pid)
                else:
                    st.session_state.recs_open.add(pid)

                    if pid not in st.session_state.recs_cache:
                        with st.spinner("Đang tải gợi ý..."):
                            try:
                                rec_data = api_get_recommendations(pid)
                                st.session_state.recs_cache[pid] = rec_data.get("data", []) if rec_data.get("success") else []
                            except Exception as e:
                                st.error(f"❌ Lỗi gọi API recommendations: {e}")
                                st.session_state.recs_cache[pid] = []

        with a2:
            st.markdown(f"<div class='small-muted'>ID: <b>{pid}</b></div>", unsafe_allow_html=True)

        if pid in st.session_state.recs_open:
            recs = st.session_state.recs_cache.get(pid, [])
            if not recs:
                st.warning("⚠️ Không có sản phẩm gợi ý.")
            else:
                st.info(f"📊 Có {len(recs)} sản phẩm được gợi ý")
                for r in recs:
                    rname = safe_str(r.get("product_name", ""))
                    rurl = safe_str(r.get("url", "#"))
                    score = float(r.get("similarity_score", r.get("score", 0)))

                    st.markdown(
                        f"""
                        <div class="product-card" style="margin-left:18px;">
                          <h4>
                            <a class="product-link" href="{rurl}" target="_blank" rel="noopener noreferrer">{rname}</a>
                          </h4>
                          {render_properties(r, max_items=5)}
                          <div style="margin-top:8px;">
                            <span class="recommendation-badge">Độ tương đồng: {score*100:.1f}%</span>
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    st.progress(min(max(score, 0.0), 1.0))

        st.markdown("</div>", unsafe_allow_html=True)

# padding so fixed bar doesn't cover content
st.markdown("<div class='content-bottom-pad'></div>", unsafe_allow_html=True)

# =========================
# Fixed bottom bar: Load more
# NOTE: Không dùng st.columns vertical_alignment
# =========================
st.markdown('<div class="fixed-bar"><div class="wrap">', unsafe_allow_html=True)

bar_left, bar_right = st.columns([3, 9])
with bar_left:
    can_load = bool(st.session_state.has_more) and loaded > 0
    if st.button("⬇️ Tải thêm", disabled=not can_load, use_container_width=True, key="btn_load_more"):
        load_more()
        st.rerun()

with bar_right:
    info_q = st.session_state.keyword.strip() or "—"
    st.markdown(
        f"""
        <div class="info">
          Từ khóa: <b>{info_q}</b> | Đang hiển thị <b>{loaded}</b>/<b>{total}</b>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("</div></div>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("<div style='text-align:center;color:white'>IT4868 - Web mining</div>", unsafe_allow_html=True)
