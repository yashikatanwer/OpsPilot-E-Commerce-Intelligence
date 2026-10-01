import re
from difflib import SequenceMatcher
import numpy as np
import pandas as pd

# OpsPilot supports a deliberately scoped set of common e-commerce order/sales schemas.

FIELD_KEYWORDS = {
    "order": ["order id", "order number", "order no", "transaction id", "transaction number", "invoice id", "invoice no", "invoice number", "invoice"],
    "customer": ["customer id", "customer name", "buyer id", "buyer name", "client id", "client", "user id", "user name", "customer"],
    "product": ["product name", "item name", "product", "item", "description"],
    "product_id": ["product id", "product code", "sku", "product sku", "stock keeping unit", "stock code", "item id", "item code"],
    "category": ["product category", "category", "product type", "department", "segment"],
    "revenue": ["total revenue", "total sales", "sales revenue", "sales amount", "total amount", "total price", "order value", "order amount", "transaction amount", "order total", "grand total", "line total", "line amount", "extended price", "subtotal", "net sales", "gross sales", "revenue", "sales", "amount", "gmv", "merchandise value"],
    "quantity": ["quantity", "qty", "units sold", "item quantity", "number of units", "units"],
    "price": ["unit selling price", "selling price", "unit price", "item price", "sale price", "price"],
    "list_price": ["mrp", "maximum retail price", "list price", "retail price", "marked price"],
    "profit": ["net profit", "gross profit", "profit amount", "profit"],
    "cost": ["unit cost", "product cost", "cost amount", "cost of goods sold", "cogs", "cost"],
    "discount": ["discount amount", "discount value", "discount rate", "discount percent", "discount"],
    "status": ["order status", "delivery status", "fulfillment status", "transaction status", "order state", "status"],
    "payment": ["payment method", "payment type", "transaction method", "mode of payment", "payment"],
    "date": ["order date", "purchase date", "transaction date", "sales date", "sale date", "invoice date", "created date", "created at", "transaction datetime", "datetime", "timestamp", "date"],
    "channel": ["sales channel", "sales platform", "marketplace", "channel", "platform", "store"],
    "referral": ["referral source", "acquisition source", "traffic source", "utm source", "marketing source", "referral", "source"],
    "city": ["city"],
    "state": ["state", "province"],
    "country": ["country", "nation"],
    "region": ["region", "territory", "sales region"],
}

FIELD_EXCLUSIONS = {
    "order": ["reorder point", "order point", "order level"],
    "customer": ["customer rating", "customer score", "customer satisfaction", "customer feedback", "average customer rating", "review score"],
    "revenue": ["unit price", "selling price", "unit selling price", "item price", "sale price", "price", "mrp", "retail price", "discount", "profit", "cost", "monthly recurring revenue", "mrr"],
    "price": ["total price", "total amount", "total revenue", "order value", "mrp", "retail price", "discount"],
    "list_price": ["unit price", "selling price", "sale price"],
    "discount": ["coupon code", "coupon", "promo code", "promotion code"],
    "channel": ["referral source", "traffic source", "acquisition source", "utm source"],
    "status": ["stock status", "inventory status"],
    "product": ["items in cart", "customer rating", "product id", "sku", "stock code"],
}

NON_ECOM_MARKERS = [
    "subscription plan", "billing cycle", "monthly recurring revenue", "mrr", "churn flag", "churn reason",
    "menu item", "restaurant location", "order type", "customer rating",
    "supplier name", "opening stock", "closing stock", "reorder point", "stock status",
]


def normalize_name(name):
    text = str(name).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([A-Za-z])([0-9])", r"\1 \2", text)
    text = re.sub(r"([0-9])([A-Za-z])", r"\1 \2", text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def numeric_series(df, column):
    if not column or column not in df.columns:
        return pd.Series(index=df.index, dtype=float)
    s = df[column]
    if pd.api.types.is_numeric_dtype(s):
        return pd.to_numeric(s, errors="coerce")
    s = (s.astype(str).str.replace(",", "", regex=False)
           .str.replace("₹", "", regex=False).str.replace("$", "", regex=False)
           .str.replace("€", "", regex=False).str.replace("£", "", regex=False)
           .str.replace("%", "", regex=False).str.strip())
    return pd.to_numeric(s, errors="coerce")


def _similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


def _allowed(name, field):
    for ex in FIELD_EXCLUSIONS.get(field, []):
        if name == normalize_name(ex):
            return False
    return True


def find_column(df, keywords, used=None, field=None):
    used = set(used or [])
    normalized = {c: normalize_name(c) for c in df.columns}
    kws = [normalize_name(k) for k in keywords]

    # Strong exact match always wins.
    for kw in kws:
        for col, name in normalized.items():
            if col not in used and name == kw and _allowed(name, field):
                return col

    # Multi-word phrases can match a longer column name; single generic words cannot.
    candidates = []
    for kw in kws:
        kt = kw.split()
        if len(kt) < 2:
            continue
        for col, name in normalized.items():
            if col in used or not _allowed(name, field):
                continue
            nt = name.split()
            if kt == nt:
                candidates.append((100 + len(kt), col))
            elif name.startswith(kw + " ") or name.endswith(" " + kw):
                candidates.append((85 + len(kt), col))
    if candidates:
        return max(candidates, key=lambda x: x[0])[1]

    # Conservative fuzzy matching for obvious typos only.
    fuzzy = []
    for kw in kws:
        if len(kw) < 4:
            continue
        for col, name in normalized.items():
            if col in used or not _allowed(name, field):
                continue
            ratio = _similarity(kw, name)
            if ratio >= 0.93:
                fuzzy.append((ratio, col))
    return max(fuzzy, key=lambda x: x[0])[1] if fuzzy else None


def detect_fields(df):
    fields = {}
    used = set()
    # Product name before product ID prevents StockCode from becoming the displayed product.
    priority = ["order", "customer", "product", "product_id", "category", "date", "quantity", "revenue", "price", "list_price", "profit", "cost", "discount", "status", "payment", "referral", "channel", "city", "state", "country", "region"]
    for field in priority:
        col = find_column(df, FIELD_KEYWORDS[field], used, field)
        fields[field] = col
        if col:
            used.add(col)
    return fields


def classify_ecommerce_dataset(df, fields):
    names = [normalize_name(c) for c in df.columns]
    joined = " | ".join(names)

    # Reject clearly unrelated business schemas.
    non_ecom = [
        "subscription plan", "billing cycle", "monthly recurring revenue",
        "mrr", "churn flag", "churn reason", "menu item",
        "restaurant location", "customer rating"
    ]
    markers = [m for m in non_ecom if normalize_name(m) in joined]
    if markers:
        return {
            "is_ecommerce": False,
            "confidence": "High",
            "reason": "The dataset contains fields associated with a non-e-commerce dataset.",
            "markers": markers,
        }

    has_order = bool(fields.get("order"))
    has_product = bool(fields.get("product") or fields.get("product_id"))
    has_money = bool(fields.get("revenue") or (fields.get("quantity") and (fields.get("price") or fields.get("list_price"))))
    has_customer = bool(fields.get("customer"))
    has_date = bool(fields.get("date"))
    inventory_shape = bool(fields.get("product") and fields.get("quantity") and fields.get("list_price"))

    supported = (
        (has_order and has_product and has_money)
        or (has_order and has_money and fields.get("quantity"))
        or (has_product and has_money and has_date)
        or inventory_shape
        or (has_product and has_money and has_customer)
    )

    if supported:
        kind = "Retail / Inventory Sales" if inventory_shape and not has_order else "E-Commerce"
        return {
            "is_ecommerce": True,
            "confidence": "High",
            "reason": "The dataset contains a recognizable e-commerce or retail sales structure.",
            "markers": [],
            "subtype": kind,
        }

    return {
        "is_ecommerce": False,
        "confidence": "Low",
        "reason": "Required e-commerce order/product and sales fields were not detected.",
        "markers": [],
    }


def _revenue_series(df, fields):
    col = fields.get("revenue")
    if col:
        return numeric_series(df, col), "column"
    qty = fields.get("quantity")
    price = fields.get("price") or fields.get("list_price")
    if qty and price:
        return numeric_series(df, qty) * numeric_series(df, price), "derived"
    return pd.Series(index=df.index, dtype=float), None


def _order_count(df, fields):
    col = fields.get("order")
    if not col:
        return None
    values = df[col].dropna().astype(str).str.strip()
    values = values[values != ""]
    return int(values.nunique()) if not values.empty else 0


def _affected_orders(df, fields):
    mask = pd.Series(False, index=df.index)
    qty = fields.get("quantity")
    status = fields.get("status")
    order = fields.get("order")
    if qty:
        mask |= numeric_series(df, qty).fillna(0) < 0
    if status:
        mask |= df[status].astype(str).str.contains(r"cancel|return|refund", case=False, na=False)
    if order:
        mask |= df[order].astype(str).str.match(r"^C", case=False, na=False)
    return mask


def generate_kpis(df, fields):
    k = {}

    order_count = _order_count(df, fields)
    if order_count is not None:
        k["total_orders"] = order_count
    else:
        k["total_records"] = int(len(df))

    customer = fields.get("customer")
    if customer:
        values = df[customer].dropna().astype(str).str.strip()
        values = values[values != ""]
        if not values.empty:
            k["total_customers"] = int(values.nunique())

    revenue, source = _revenue_series(df, fields)
    valid = revenue.notna()
    if valid.any():
        net = float(revenue[valid].sum())
        gross = float(revenue[valid & (revenue > 0)].sum())
        returns = float(-revenue[valid & (revenue < 0)].sum())
        k.update({
            "total_revenue": round(net, 2),
            "net_revenue": round(net, 2),
            "gross_revenue": round(gross, 2),
            "return_value": round(max(returns, 0), 2),
            "revenue_source": source,
        })
        if order_count is not None and order_count > 0:
            k["average_order_value"] = round(net / order_count, 2)

    qty = fields.get("quantity")
    if qty:
        q = numeric_series(df, qty).dropna()
        if not q.empty:
            k["total_quantity"] = round(float(q.sum()), 2)
            k["returned_units"] = round(float(-q[q < 0].sum()), 2)

    profit = fields.get("profit")
    if profit:
        p = numeric_series(df, profit).dropna()
        if not p.empty:
            k["total_profit"] = round(float(p.sum()), 2)
    elif fields.get("cost") and "total_revenue" in k:
        cost = numeric_series(df, fields["cost"])
        qty_values = numeric_series(df, fields.get("quantity")) if fields.get("quantity") else None
        if cost.notna().any():
            total_cost = cost * qty_values if qty_values is not None else cost
            k["total_profit"] = round(float(k["total_revenue"] - total_cost.sum()), 2)

    affected = _affected_orders(df, fields)
    if affected.any():
        order = fields.get("order")
        if order:
            affected_count = int(df.loc[affected, order].dropna().astype(str).nunique())
            k["cancelled_orders"] = affected_count
            k["cancellation_rate"] = round(affected_count / max(order_count or 1, 1) * 100, 2)

    return k


def _group_dimension(df, dimension_col, fields):
    if not dimension_col or dimension_col not in df.columns:
        return pd.DataFrame(columns=["dimension", "orders", "revenue"])
    valid = df[dimension_col].notna()
    if not valid.any():
        return pd.DataFrame(columns=["dimension", "orders", "revenue"])
    sub = df.loc[valid]
    rev, _ = _revenue_series(sub, fields)
    temp = pd.DataFrame({"dimension": sub[dimension_col].astype(str).values, "revenue": rev.fillna(0).values}, index=sub.index)
    order = fields.get("order")
    if order:
        temp["order_id"] = sub[order].astype(str).values
        out = temp.groupby("dimension").agg(orders=("order_id", "nunique"), revenue=("revenue", "sum")).reset_index()
    else:
        temp["orders"] = 1
        out = temp.groupby("dimension").agg(orders=("orders", "sum"), revenue=("revenue", "sum")).reset_index()
    return out.sort_values(["revenue", "orders"], ascending=False).head(20)


def analyze_products(df, fields):
    out = _group_dimension(df, fields.get("product"), fields)
    return [{"product": str(r.dimension), "orders": int(r.orders), "revenue": round(float(r.revenue), 2)} for r in out.itertuples()]


def analyze_categories(df, fields):
    out = _group_dimension(df, fields.get("category"), fields)
    return [{"category": str(r.dimension), "orders": int(r.orders), "revenue": round(float(r.revenue), 2)} for r in out.itertuples()]


def _distinct_counts(df, col, order_col=None):
    if not col:
        return {}
    cols = [col] + ([order_col] if order_col else [])
    temp = df[cols].dropna(subset=[col]).copy()
    if order_col:
        temp = temp.drop_duplicates(subset=[order_col])
    return temp[col].astype(str).value_counts().to_dict()


def analyze_payments(df, fields):
    col, order = fields.get("payment"), fields.get("order")
    counts = _distinct_counts(df, col, order)
    total = sum(counts.values()) or 1
    return [{"payment_method": str(k), "orders": int(v), "percentage": round(v / total * 100, 2)} for k, v in counts.items()]


def analyze_channels(df, fields):
    col, order = fields.get("channel"), fields.get("order")
    counts = _distinct_counts(df, col, order)
    return [{"channel": str(k), "orders": int(v)} for k, v in counts.items()]


def analyze_referrals(df, fields):
    col = fields.get("referral")
    if not col:
        return []
    valid = df[col].notna()
    sub = df.loc[valid]
    rev, _ = _revenue_series(sub, fields)
    temp = pd.DataFrame({"referral": sub[col].astype(str).values, "revenue": rev.fillna(0).values}, index=sub.index)
    order = fields.get("order")
    if order:
        temp["order_id"] = sub[order].astype(str).values
        out = temp.groupby("referral").agg(orders=("order_id", "nunique"), revenue=("revenue", "sum")).reset_index()
    else:
        temp["orders"] = 1
        out = temp.groupby("referral").agg(orders=("orders", "sum"), revenue=("revenue", "sum")).reset_index()
    out = out.sort_values("revenue", ascending=False).head(20)
    return [{"referral": str(r.referral), "orders": int(r.orders), "revenue": round(float(r.revenue), 2)} for r in out.itertuples()]


def analyze_trends(df, fields):
    col = fields.get("date")
    if not col:
        return []
    dates = pd.to_datetime(df[col], errors="coerce")
    valid = dates.notna()
    if not valid.any():
        return []
    sub = df.loc[valid]
    rev, _ = _revenue_series(sub, fields)
    temp = pd.DataFrame({"month": dates.loc[valid].dt.to_period("M").astype(str).values, "revenue": rev.fillna(0).values}, index=sub.index)
    order = fields.get("order")
    if order:
        temp["order_id"] = sub[order].astype(str).values
        out = temp.groupby("month").agg(orders=("order_id", "nunique"), revenue=("revenue", "sum")).reset_index()
    else:
        temp["orders"] = 1
        out = temp.groupby("month").agg(orders=("orders", "sum"), revenue=("revenue", "sum")).reset_index()
    return [{"month": str(r.month), "orders": int(r.orders), "revenue": round(float(r.revenue), 2)} for r in out.itertuples()]


def analyze_status(df, fields):
    col, order = fields.get("status"), fields.get("order")
    if not col:
        return []
    temp = df[[col] + ([order] if order else [])].dropna(subset=[col]).copy()
    if order:
        temp = temp.drop_duplicates(subset=[order])
    counts = temp[col].astype(str).value_counts()
    total = len(temp) or 1
    return [{"status": str(k), "count": int(v), "percentage": round(v / total * 100, 2)} for k, v in counts.items()]


def analyze_data_quality(df):
    missing_by_col = df.isna().sum()
    missing_total = int(missing_by_col.sum())
    duplicates = int(df.duplicated().sum()) if len(df) <= 300000 else None
    return {
        "rows": int(len(df)), "columns": int(len(df.columns)), "missing_values": missing_total,
        "missing_columns": {str(c): int(v) for c, v in missing_by_col.items() if v > 0},
        "duplicate_rows": duplicates, "duplicate_check": "exact" if duplicates is not None else "not calculated for large dataset",
        "completeness": round(100 - missing_total / max(len(df) * len(df.columns), 1) * 100, 2),
    }


def generate_insights(df, fields, kpis, products, statuses):
    insights = []
    if "total_revenue" in kpis:
        source = "the detected revenue field" if kpis.get("revenue_source") == "column" else "quantity × unit price"
        insights.append({"title": "Revenue", "text": f"Net revenue is ₹{kpis['total_revenue']:,.2f}, calculated from {source}."})
    if products:
        insights.append({"title": "Top product", "text": f"{products[0]['product']} generated the highest available revenue."})
    if kpis.get("total_customers") is not None and kpis.get("total_orders"):
        insights.append({"title": "Customer base", "text": f"{kpis['total_customers']:,} unique customers are associated with {kpis['total_orders']:,} detected orders."})
    if kpis.get("cancellation_rate") is not None:
        insights.append({"title": "Returns / cancellations", "text": f"{kpis['cancelled_orders']:,} affected orders were detected ({kpis['cancellation_rate']:.2f}% of orders)."})
    if statuses:
        top = statuses[0]
        insights.append({"title": "Order status", "text": f"{top['status']} is the most common detected order status ({top['percentage']:.2f}%)."})
    return insights


def analyze_dataset(df):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("The uploaded dataset is empty.")
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all").copy()
    if df.empty:
        raise ValueError("The uploaded dataset contains no usable rows or columns.")

    fields = detect_fields(df)
    classification = classify_ecommerce_dataset(df, fields)
    if not classification["is_ecommerce"]:
        raise ValueError("Unsupported dataset: OpsPilot accepts common e-commerce order/sales datasets only.")

    kpis = generate_kpis(df, fields)
    products = analyze_products(df, fields)
    categories = analyze_categories(df, fields)
    payments = analyze_payments(df, fields)
    channels = analyze_channels(df, fields)
    referrals = analyze_referrals(df, fields)
    trends = analyze_trends(df, fields)
    statuses = analyze_status(df, fields)
    quality = analyze_data_quality(df)
    insights = generate_insights(df, fields, kpis, products, statuses)

    product_count = int(df[fields["product"]].dropna().nunique()) if fields.get("product") else 0
    payment_count = int(df[fields["payment"]].dropna().nunique()) if fields.get("payment") else 0
    top_product = products[0]["product"] if products else None
    top_payment = payments[0]["payment_method"] if payments else None

    numeric_cols = [str(c) for c in df.select_dtypes(include=np.number).columns]
    text_cols = [str(c) for c in df.select_dtypes(include=["object", "string"]).columns]
    date_cols = [str(c) for c in df.columns if any(x in normalize_name(c) for x in ["date", "time", "timestamp"])]

    return {
        "dataset_type": classification.get("subtype", "E-Commerce"),
        "dataset_classification": classification,
        "rows": len(df), "columns": len(df.columns), "total_rows": len(df), "total_columns": len(df.columns),
        "filename": df.attrs.get("filename"), "source_sheets": df.attrs.get("source_sheets", []),
        "missing": quality["missing_values"], "missing_values": quality["missing_values"],
        "duplicates": quality["duplicate_rows"] if quality["duplicate_rows"] is not None else "Not calculated",
        "duplicate_rows": quality["duplicate_rows"], "completeness": quality["completeness"],
        "missing_columns": quality["missing_columns"], "duplicate_check": quality["duplicate_check"],
        "numeric_columns": numeric_cols, "text_columns": text_cols, "date_columns": date_cols,
        "column_names": [str(c) for c in df.columns],
        "data_types": {str(c): str(df[c].dtype) for c in df.columns},
        "unique_values": {str(c): int(df[c].nunique(dropna=True)) for c in df.columns if len(df) <= 300000},
        "detected_fields": fields,
        "kpis": kpis, "metrics": kpis,
        "products": products, "categories": categories, "payments": payments, "channels": channels, "referrals": referrals, "trends": trends, "statuses": statuses,
        "insights": insights,
        "revenue_over_time": {x["month"]: x["revenue"] for x in trends},
        "revenue_by_product": {x["product"]: x["revenue"] for x in products},
        "orders_by_product": {x["product"]: x["orders"] for x in products},
        "orders_by_status": {x["status"]: x["count"] for x in statuses},
        "orders_by_payment": {x["payment_method"]: x["orders"] for x in payments},
        "revenue_by_referral": {x["referral"]: x["revenue"] for x in referrals},
        "product_count": product_count, "payment_count": payment_count, "top_product": top_product, "top_product_revenue": products[0]["revenue"] if products else None,
        "top_payment_method": top_payment,
        "total_orders": kpis.get("total_orders"),
        "total_records": kpis.get("total_records", len(df)), "total_revenue": kpis.get("total_revenue"), "net_revenue": kpis.get("net_revenue"),
        "gross_revenue": kpis.get("gross_revenue"), "return_value": kpis.get("return_value"), "returned_units": kpis.get("returned_units", 0),
        "total_customers": kpis.get("total_customers"), "average_order_value": kpis.get("average_order_value"),
        "cancelled_orders": kpis.get("cancelled_orders"), "cancellation_rate": kpis.get("cancellation_rate"),
        "executive_summary": f"OpsPilot analyzed {len(df):,} rows across {len(df.columns)} columns from the uploaded e-commerce dataset.",
    }
