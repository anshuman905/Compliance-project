import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Compliance System", layout="wide")
st.title("📊 Compliance Monitoring System")

# ---------------------------
# SMART COLUMN MATCHING
# ---------------------------
def match_column(field, columns):
    field = field.lower()
    scores = {}
    for col in columns:
        if field == col.lower():
            return col
        if field in col.lower():
            scores[col] = len(field)
    return max(scores, key=scores.get) if scores else None

# ---------------------------
# ADVANCED RULE GENERATOR
# ---------------------------
def generate_rules_from_text(policy_text, columns):
    rules = []
    text = policy_text.lower()

    patterns = [
        (r'(\w+)\s+(above|greater than|at least|min|minimum)\s+(\d+)', "min"),
        (r'(\w+)\s+(below|less than|at most|max|maximum)\s+(\d+)', "max"),
        (r'(\w+)\s+between\s+(\d+)\s+and\s+(\d+)', "range"),
        (r'(\w+)\s+(equals|equal to)\s+(\d+)', "equal"),
        (r'(\w+)\s+(must not be empty|required|mandatory)', "not_null"),
        (r'(\w+)\s*>\s*(\w+)', "greater_field"),
        (r'(\w+)\s*<\s*(\w+)', "less_field"),
    ]

    for pattern, rule_type in patterns:
        matches = re.findall(pattern, text)
        for m in matches:

            if rule_type in ["greater_field", "less_field"]:
                f1 = match_column(m[0], columns)
                f2 = match_column(m[1], columns)
                if f1 and f2:
                    rules.append({
                        "field": f1,
                        "operator": rule_type,
                        "value": f2
                    })
                continue

            field = m[0]
            col = match_column(field, columns)

            if not col:
                continue

            if rule_type == "range":
                rules.append({
                    "field": col,
                    "operator": "range",
                    "value": (int(m[1]), int(m[2]))
                })

            elif rule_type == "not_null":
                rules.append({
                    "field": col,
                    "operator": "not_null",
                    "value": None
                })

            else:
                rules.append({
                    "field": col,
                    "operator": rule_type,
                    "value": int(m[-1])
                })

    return rules

# ---------------------------
# RULE ENGINE
# ---------------------------
def evaluate_rules(row, rules):
    issues = []

    for r in rules:
        f = r["field"]
        op = r["operator"]
        val = r["value"]

        if f not in row:
            continue

        if op == "min" and row[f] < val:
            issues.append(f"{f} < {val}")

        elif op == "max" and row[f] > val:
            issues.append(f"{f} > {val}")

        elif op == "range":
            if not (val[0] <= row[f] <= val[1]):
                issues.append(f"{f} not in {val}")

        elif op == "equal" and row[f] != val:
            issues.append(f"{f} != {val}")

        elif op == "not_null" and pd.isna(row[f]):
            issues.append(f"{f} is null")

        elif op == "greater_field":
            if row[f] <= row[val]:
                issues.append(f"{f} <= {val}")

        elif op == "less_field":
            if row[f] >= row[val]:
                issues.append(f"{f} >= {val}")

    return "✅ Compliant" if not issues else "❌ " + ", ".join(issues)

# ---------------------------
# FILE READERS
# ---------------------------
def read_rules_file(file, columns):
    if file.name.endswith(".txt"):
        return generate_rules_from_text(file.read().decode("utf-8"), columns)

    elif file.name.endswith(".csv"):
        df = pd.read_csv(file)
        return df.to_dict(orient="records")

    elif file.name.endswith(".docx"):
        from docx import Document
        doc = Document(file)
        text = " ".join([p.text for p in doc.paragraphs])
        return generate_rules_from_text(text, columns)

    return []

# ---------------------------
# SIDEBAR
# ---------------------------
st.sidebar.header("Inputs")

data_file = st.sidebar.file_uploader("Upload Data", type=["csv", "xlsx"])
rules_file = st.sidebar.file_uploader("Upload Rules", type=["csv", "txt", "docx"])

policy_text = st.sidebar.text_area("Policy Text")
generate = st.sidebar.button("Generate Rules")

rules = []

# ---------------------------
# MAIN
# ---------------------------
if data_file:

    if data_file.name.endswith(".csv"):
        data = pd.read_csv(data_file)
    else:
        data = pd.read_excel(data_file, engine="openpyxl")

    # RULE LOAD
    if rules_file:
        rules = read_rules_file(rules_file, data.columns)

    elif generate and policy_text:
        rules = generate_rules_from_text(policy_text, data.columns)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Data")
        st.dataframe(data)

    with col2:
        st.subheader("Rules")
        st.write(rules if rules else "No rules")

    # ADVANCED SEARCH
    search = st.text_input("Search (any field)")

    if search:
        data = data[data.astype(str).apply(
            lambda r: r.str.contains(search, case=False, na=False)
        ).any(axis=1)]

    if st.button("Run Compliance Check"):

        if not rules:
            st.error("No rules found")
        else:
            data["Result"] = data.apply(lambda x: evaluate_rules(x, rules), axis=1)

            total = len(data)
            compliant = data[data["Result"].str.contains("✅")].shape[0]
            violations = total - compliant

            st.markdown(f"""
            <div style="background-color:#e3a389;padding:20px;border-radius:8px;text-align:center;">
                <h3>Results Dashboard</h3>
                <p>Total: {total}</p>
                <p>Compliant: {compliant} ✅</p>
                <p>Non-Compliant: {violations} ❌</p>
            </div>
            """, unsafe_allow_html=True)

            st.dataframe(data)

else:
    st.info("Upload data to start")
