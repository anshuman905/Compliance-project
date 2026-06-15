import streamlit as st
import pandas as pd
import re

# ---------------------------
# PAGE SETUP
# ---------------------------
st.set_page_config(page_title="Compliance System", layout="wide")
st.title("📊 Smart Compliance Monitoring System")

# ---------------------------
# SMART COLUMN MATCH
# ---------------------------
def match_column(field, columns):
    field = field.lower()

    for col in columns:
        col_lower = col.lower()
        if field in col_lower or col_lower in field:
            return col

    return None

# ---------------------------
# ADVANCED RULE GENERATOR ✅
# ---------------------------
def generate_rules(policy_text, columns):
    rules = []
    text = policy_text.lower()

    # Split sentences intelligently
    sentences = re.split(r"[.\n]", text)

    for sentence in sentences:

        # MIN conditions
        match = re.search(r'(\w+).*?(above|greater than|at least|min|minimum)\s+(\d+)', sentence)
        if match:
            col = match_column(match.group(1), columns)
            if col:
                rules.append({"field": col, "operator": "min", "value": int(match.group(3))})

        # MAX conditions
        match = re.search(r'(\w+).*?(below|less than|at most|max|maximum)\s+(\d+)', sentence)
        if match:
            col = match_column(match.group(1), columns)
            if col:
                rules.append({"field": col, "operator": "max", "value": int(match.group(3))})

        # RANGE
        match = re.search(r'(\w+).*?between\s+(\d+)\s+and\s+(\d+)', sentence)
        if match:
            col = match_column(match.group(1), columns)
            if col:
                rules.append({
                    "field": col,
                    "operator": "range",
                    "value": (int(match.group(2)), int(match.group(3)))
                })

        # EQUAL
        match = re.search(r'(\w+).*?(equals|equal to|is)\s+(\d+)', sentence)
        if match:
            col = match_column(match.group(1), columns)
            if col:
                rules.append({"field": col, "operator": "equal", "value": int(match.group(3))})

        # NOT NULL
        match = re.search(r'(\w+).*?(must not be empty|required|mandatory)', sentence)
        if match:
            col = match_column(match.group(1), columns)
            if col:
                rules.append({"field": col, "operator": "not_null", "value": None})

    return rules

# ---------------------------
# RULE ENGINE
# ---------------------------
def evaluate_rules(row, rules):
    issues = []

    for r in rules:
        f = r["field"]
        op = r["operator"]
        v = r["value"]

        if f not in row:
            continue

        try:
            if op == "min" and row[f] < v:
                issues.append(f"{f} < {v}")

            elif op == "max" and row[f] > v:
                issues.append(f"{f} > {v}")

            elif op == "range":
                if not (v[0] <= row[f] <= v[1]):
                    issues.append(f"{f} not in {v}")

            elif op == "equal" and row[f] != v:
                issues.append(f"{f} != {v}")

            elif op == "not_null" and pd.isna(row[f]):
                issues.append(f"{f} is null")

        except:
            continue

    return "✅" if not issues else "❌ " + ", ".join(issues)

# ---------------------------
# READ POLICY FILE
# ---------------------------
def read_policy(file):
    try:
        if file.name.endswith(".txt"):
            return file.read().decode("utf-8")

        elif file.name.endswith(".csv"):
            df = pd.read_csv(file)
            return " ".join(df.astype(str).values.flatten())

        elif file.name.endswith(".docx"):
            from docx import Document
            doc = Document(file)
            return " ".join([p.text for p in doc.paragraphs])

        elif file.name.endswith(".pdf"):
            from PyPDF2 import PdfReader
            reader = PdfReader(file)
            return " ".join([p.extract_text() or "" for p in reader.pages])

    except:
        return ""

    return ""

# ---------------------------
# UI
# ---------------------------
st.sidebar.header("Inputs")

data_file = st.sidebar.file_uploader("Upload Data", ["csv", "xlsx"])
policy_file = st.sidebar.file_uploader("Upload Rules", ["txt", "csv", "docx", "pdf"])
policy_text = st.sidebar.text_area("Or paste policy")

rules = []

# ---------------------------
# MAIN
# ---------------------------
if data_file:

    if data_file.name.endswith(".csv"):
        data = pd.read_csv(data_file)
    else:
        data = pd.read_excel(data_file, engine="openpyxl")

    if policy_file:
        policy_text = read_policy(policy_file)

    if policy_text:
        rules = generate_rules(policy_text, data.columns)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Data")
        st.dataframe(data)

    with col2:
        st.subheader("Generated Rules")
        st.write(rules if rules else "No rules generated")

    if st.button("Run Compliance Check"):

        if not rules:
            st.error("No rules generated")
        else:
            data["Result"] = data.apply(lambda x: evaluate_rules(x, rules), axis=1)

            total = len(data)
            compliant = (data["Result"] == "✅").sum()
            violations = total - compliant

            st.markdown(f"""
            <div style="background:#e3a389;padding:20px;border-radius:8px;text-align:center;">
                <h3>Results Dashboard</h3>
                <p>Total: {total}</p>
                <p>Compliant: {compliant} ✅</p>
                <p>Non-Compliant: {violations} ❌</p>
            </div>
            """, unsafe_allow_html=True)

            st.dataframe(data)

else:
    st.info("Upload dataset to start")
