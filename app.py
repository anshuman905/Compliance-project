import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Compliance System", layout="wide")
st.title("📊 Smart Compliance Monitoring System")

def match_column(field, columns):
    field = field.lower()
    for col in columns:
        if field in col.lower() or col.lower() in field:
            return col
    return None

def generate_rules(policy_text, columns):
    rules = []
    text = policy_text.lower()
    sentences = re.split(r"[.\n]", text)

    for sentence in sentences:
        for col in columns:
            if col.lower() in sentence:

                m = re.search(r'(above|greater than|at least|min|minimum)\s+(\d+)', sentence)
                if m:
                    rules.append({"field": col, "operator": "min", "value": int(m.group(2))})
                    continue

                m = re.search(r'(below|less than|at most|max|maximum)\s+(\d+)', sentence)
                if m:
                    rules.append({"field": col, "operator": "max", "value": int(m.group(2))})
                    continue

                m = re.search(r'between\s+(\d+)\s+and\s+(\d+)', sentence)
                if m:
                    rules.append({"field": col, "operator": "range", "value": (int(m.group(1)), int(m.group(2)))})

                m = re.search(r'(equals|equal to|is)\s+(\d+)', sentence)
                if m:
                    rules.append({"field": col, "operator": "equal", "value": int(m.group(2))})

                if any(x in sentence for x in ["must not be empty", "required", "mandatory"]):
                    rules.append({"field": col, "operator": "not_null", "value": None})

    return rules

def evaluate_rules(row, rules):
    issues = []

    for r in rules:
        if r["field"] not in row:
            continue

        try:
            if r["operator"] == "min" and row[r["field"]] < r["value"]:
                issues.append(f'{r["field"]} < {r["value"]}')

            elif r["operator"] == "max" and row[r["field"]] > r["value"]:
                issues.append(f'{r["field"]} > {r["value"]}')

            elif r["operator"] == "range":
                if not (r["value"][0] <= row[r["field"]] <= r["value"][1]):
                    issues.append(f'{r["field"]} not in {r["value"]}')

            elif r["operator"] == "equal" and row[r["field"]] != r["value"]:
                issues.append(f'{r["field"]} != {r["value"]}')

            elif r["operator"] == "not_null" and pd.isna(row[r["field"]]):
                issues.append(f'{r["field"]} is null')

        except:
            continue

    return "✅ Compliant" if not issues else "❌ " + ", ".join(issues)

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

st.sidebar.header("Inputs")

data_file = st.sidebar.file_uploader("Upload Data", ["csv", "xlsx"])
policy_file = st.sidebar.file_uploader("Upload Rules", ["txt", "csv", "docx", "pdf"])
policy_text = st.sidebar.text_area("Or paste policy")

rules = []

if data_file:
    try:
        if data_file.name.endswith(".csv"):
            data = pd.read_csv(data_file)
        else:
            data = pd.read_excel(data_file, engine="openpyxl")
    except:
        st.error("Error reading dataset")
        st.stop()

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
