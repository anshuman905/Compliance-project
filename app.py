import streamlit as st
import pandas as pd
import re

# ---------------------------
# PAGE SETUP
# ---------------------------
st.set_page_config(page_title="Compliance System", layout="wide")
st.title("📊 Compliance Monitoring System")

# ---------------------------
# COLUMN MATCH
# ---------------------------
def match_column(text, columns):
    text = text.lower()
    for col in columns:
        if col.lower() in text:
            return col
    return None

# ---------------------------
# RULE GENERATOR (SAFE + FLEXIBLE)
# ---------------------------
def generate_rules(policy_text, columns):
    rules = []
    text = policy_text.lower()

    sentences = re.split(r"[.\n]", text)

    for sentence in sentences:
        for col in columns:

            if col.lower() not in sentence:
                continue

            numbers = re.findall(r"\d+", sentence)

            # RANGE
            if "between" in sentence and len(numbers) >= 2:
                rules.append({
                    "field": col,
                    "operator": "range",
                    "value": (int(numbers[0]), int(numbers[1]))
                })
                continue

            if not numbers:
                continue

            value = int(numbers[0])

            # MIN
            if any(x in sentence for x in ["above", "greater", "minimum", "at least"]):
                rules.append({"field": col, "operator": "min", "value": value})

            # MAX
            elif any(x in sentence for x in ["below", "less", "maximum", "at most"]):
                rules.append({"field": col, "operator": "max", "value": value})

            # EQUAL
            elif any(x in sentence for x in ["equal", "equals", "is"]):
                rules.append({"field": col, "operator": "equal", "value": value})

            # NOT NULL
            elif any(x in sentence for x in ["mandatory", "required", "not empty"]):
                rules.append({"field": col, "operator": "not_null", "value": None})

    return rules

# ---------------------------
# RULE ENGINE
# ---------------------------
def evaluate_rules(row, rules):
    issues = []

    for r in rules:
        field = r["field"]
        op = r["operator"]
        val = r["value"]

        if field not in row:
            continue

        try:
            if op == "min" and row[field] < val:
                issues.append(f"{field} < {val}")

            elif op == "max" and row[field] > val:
                issues.append(f"{field} > {val}")

            elif op == "range":
                if not (val[0] <= row[field] <= val[1]):
                    issues.append(f"{field} not in {val}")

            elif op == "equal" and row[field] != val:
                issues.append(f"{field} != {val}")

            elif op == "not_null" and pd.isna(row[field]):
                issues.append(f"{field} is null")

        except:
            continue

    return "✅ Compliant" if not issues else "❌ " + ", ".join(issues)

# ---------------------------
# FILE READER
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
# SIDEBAR
# ---------------------------
st.sidebar.header("Inputs")

data_file = st.sidebar.file_uploader("Upload Dataset", ["csv", "xlsx"])
policy_file = st.sidebar.file_uploader("Upload Policy", ["txt", "csv", "docx", "pdf"])
policy_text = st.sidebar.text_area("Or paste policy")

rules = []

# ---------------------------
# MAIN
# ---------------------------
if data_file:

    try:
        if data_file.name.endswith(".csv"):
            data = pd.read_csv(data_file)
        else:
            data = pd.read_excel(data_file, engine="openpyxl")
    except:
        st.error("❌ Error reading dataset")
        st.stop()

    if policy_file:
        policy_text = read_policy(policy_file)

    if policy_text:
        rules = generate_rules(policy_text, data.columns)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Dataset")
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
            compliant = (data["Result"] == "✅ Compliant").sum()
            violations = total - compliant

            st.markdown(f"""
            <div style="background:#e3a389;padding:20px;border-radius:8px;text-align:center;">
                <h3>Results Dashboard</h3>
                <p>Total Records: {total}</p>
                <p>Compliant: {compliant} ✅</p>
                <p>Non-Compliant: {violations} ❌</p>
            </div>
            """, unsafe_allow_html=True)

            st.dataframe(data)

else:
    st.info("Upload dataset to start")
