import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Compliance System", layout="wide")
st.title("📊 Smart Compliance Monitoring System")

# ---------------------------
# COLUMN MATCH
# ---------------------------
def match_column(text, columns):
    for col in columns:
        if col.lower() in text or text in col.lower():
            return col
    return None

# ---------------------------
# NLP-LIKE RULE EXTRACTION ✅
# ---------------------------
def generate_rules(policy_text, columns):
    rules = []
    text = policy_text.lower()

    sentences = re.split(r'[.\n]', text)

    for sentence in sentences:

        # Clean sentence
        sentence = sentence.strip()
        if not sentence:
            continue

        for col in columns:
            col_lower = col.lower()

            # If keyword exists anywhere in sentence
            if col_lower in sentence:

                # -------- MIN --------
                m = re.search(r'(above|greater than|at least|not less than|min|minimum)\s*(of)?\s*(\d+)', sentence)
                if m:
                    rules.append({"field": col, "operator": "min", "value": int(m.group(3))})
                    continue

                # -------- MAX --------
                m = re.search(r'(below|less than|at most|not more than|max|maximum)\s*(of)?\s*(\d+)', sentence)
                if m:
                    rules.append({"field": col, "operator": "max", "value": int(m.group(3))})
                    continue

                # -------- RANGE --------
                m = re.search(r'between\s*(\d+)\s*and\s*(\d+)', sentence)
                if m:
                    rules.append({"field": col, "operator": "range", "value": (int(m.group(1)), int(m.group(2)))})
                    continue

                # -------- EQUAL --------
                m = re.search(r'(equals|equal to|is)\s*(\d+)', sentence)
                if m:
                    rules.append({"field": col, "operator": "equal", "value": int(m.group(2))})
                    continue

                # -------- NOT NULL --------
                if any(keyword in sentence for keyword in [
                    "must not be empty", 
                    "cannot be empty",
                    "should not be empty",
                    "mandatory",
                    "required"
                ]):
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
        value = r["value"]

        if field not in row:
            continue

        try:
            if op == "min" and row[field] < value:
                issues.append(f"{field} < {value}")

            elif op == "max" and row[field] > value:
                issues.append(f"{field} > {value}")

            elif op == "range":
                if not (value[0] <= row[field] <= value[1]):
                    issues.append(f"{field} not in {value}")

            elif op == "equal" and row[field] != value:
                issues.append(f"{field} != {value}")

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
# UI
# ---------------------------
st.sidebar.header("Inputs")

data_file = st.sidebar.file_uploader("Upload Dataset", ["csv", "xlsx"])
policy_file = st.sidebar.file_uploader("Upload Policy Document", ["txt", "csv", "docx", "pdf"])
policy_text = st.sidebar.text_area("Or paste policy text")

rules = []

# ---------------------------
# MAIN
# ---------------------------
if data_file:

    # Load data
    try:
        if data_file.name.endswith(".csv"):
            data = pd.read_csv(data_file)
        else:
            data = pd.read_excel(data_file, engine="openpyxl")
    except:
        st.error("Error reading dataset")
        st.stop()

    # Read policy
    if policy_file:
        policy_text = read_policy(policy_file)

    # Generate rules
    if policy_text:
        rules = generate_rules(policy_text, data.columns)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Data")
        st.dataframe(data)

    with col2:
        st.subheader("Generated Rules")
        st.write(rules if rules else "No rules generated")

    # Run compliance
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
                <p>Total: {total}</p>
                <p>Compliant: {compliant} ✅</p>
                <p>Non-Compliant: {violations} ❌</p>
            </div>
            """, unsafe_allow_html=True)

            st.dataframe(data)

else:
    st.info("Upload dataset to start")
