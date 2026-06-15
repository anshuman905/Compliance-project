import streamlit as st
import pandas as pd
import re

# ---------------------------
# PAGE SETUP
# ---------------------------
st.set_page_config(page_title="Compliance System", layout="wide")
st.title("📊 Compliance Monitoring System")

# ---------------------------
# SMART FIELD MATCHING (NEW ✅)
# ---------------------------
def match_column(field, columns):
    field = field.lower()
    for col in columns:
        if field in col.lower():
            return col
    return None

# ---------------------------
# ENHANCED RULE GENERATOR ✅
# ---------------------------
def generate_rules_from_text(policy_text, columns):
    rules = []
    text = policy_text.lower()

    patterns = [
        (r'(\w+)\s+(above|greater than|at least|min|minimum)\s+(\d+)', "min"),
        (r'(\w+)\s+(below|less than|at most|max|maximum)\s+(\d+)', "max"),
        (r'(\w+)\s+between\s+(\d+)\s+and\s+(\d+)', "range"),
        (r'(\w+)\s+(equals|equal to)\s+(\d+)', "equal"),
        (r'(\w+)\s+(must not be empty|mandatory|required)', "not_null")
    ]

    for pattern, operator in patterns:
        matches = re.findall(pattern, text)

        for m in matches:
            field = m[0]
            col = match_column(field, columns)

            if not col:
                continue

            if operator == "range":
                rules.append({
                    "field": col,
                    "operator": "range",
                    "value": (int(m[1]), int(m[2])),
                    "severity": "Medium"
                })

            elif operator == "not_null":
                rules.append({
                    "field": col,
                    "operator": "not_null",
                    "value": None,
                    "severity": "High"
                })

            else:
                rules.append({
                    "field": col,
                    "operator": operator,
                    "value": int(m[-1]),
                    "severity": "High"
                })

    return rules

# ---------------------------
# RULE ENGINE (same)
# ---------------------------
def evaluate_rules(row, rules):
    issues = []

    for rule in rules:
        field = rule["field"]
        operator = rule["operator"]
        value = rule["value"]

        if field not in row:
            continue

        if operator == "min" and row[field] < value:
            issues.append(f"{field} < {value}")

        elif operator == "max" and row[field] > value:
            issues.append(f"{field} > {value}")

        elif operator == "range":
            if not (value[0] <= row[field] <= value[1]):
                issues.append(f"{field} not in {value}")

        elif operator == "equal" and row[field] != value:
            issues.append(f"{field} != {value}")

        elif operator == "not_null" and pd.isna(row[field]):
            issues.append(f"{field} is null")

    return "✅ Compliant" if not issues else "❌ " + ", ".join(issues)

# ---------------------------
# FILE READERS ✅
# ---------------------------
def read_rules_file(file, columns):
    if file.name.endswith(".txt"):
        text = file.read().decode("utf-8")
        return generate_rules_from_text(text, columns)

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

data_file = st.sidebar.file_uploader("Upload Data", type=["csv","xlsx"])
rules_file = st.sidebar.file_uploader("Upload Rules", type=["csv","txt","docx"])

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

    # ✅ RULE LOADING (IMPROVED)
    if rules_file:
        rules = read_rules_file(rules_file, data.columns)

    elif generate and policy_text:
        rules = generate_rules_from_text(policy_text, data.columns)
        st.session_state["rules"] = rules

    elif "rules" in st.session_state:
        rules = st.session_state["rules"]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Data")
        st.dataframe(data)

    with col2:
        st.subheader("Rules")
        st.write(rules if rules else "No rules")

    # SEARCH
    search = st.text_input("Search")

    if search:
        data = data[data.astype(str).apply(lambda r: r.str.contains(search, case=False, na=False)).any(axis=1)]

    if st.button("Run Compliance Check"):

        if not rules:
            st.error("No rules found")
        else:
            data["Result"] = data.apply(lambda x: evaluate_rules(x, rules), axis=1)

            total = len(data)
            compliant = data[data["Result"].str.contains("✅")].shape[0]
            violations = total - compliant

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background-color:#e3a389;padding:25px;border-radius:8px;text-align:center;">
                <h3>Results Dashboard</h3>
                <p>Total Records: {total}</p>
                <p>Compliant: {compliant} ✅</p>
                <p>Non-Compliant: {violations} ❌</p>
            </div>
            """, unsafe_allow_html=True)

            st.dataframe(data)

else:
    st.info("Upload data to start")
