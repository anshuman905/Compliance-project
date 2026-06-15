import streamlit as st
import pandas as pd
import re
from transformers import pipeline

# ---------------------------
# PAGE SETUP
# ---------------------------
st.set_page_config(page_title="AI Compliance", layout="wide")
st.title("📊 AI Compliance Monitoring System")

# ---------------------------
# LOAD MODEL (LOCAL AI ✅)
# ---------------------------
@st.cache_resource
def load_model():
    return pipeline("text2text-generation", model="google/flan-t5-small")

llm = load_model()

# ---------------------------
# COLUMN MATCH
# ---------------------------
def match_column(field, columns):
    field = field.lower()
    for col in columns:
        if field in col.lower():
            return col
    return None

# ---------------------------
# AI RULE GENERATOR ✅
# ---------------------------
def generate_rules_ai(policy_text, columns):

    prompt = f"""
    Extract structured rules from this policy.
    
    Output format:
    field, operator, value
    
    Operators: min, max, range, equal, not_null
    
    Policy:
    {policy_text}
    """

    try:
        result = llm(prompt, max_length=200)[0]["generated_text"]
    except:
        return []

    rules = []

    for line in result.split("\n"):
        parts = line.split(",")

        if len(parts) >= 3:
            try:
                field = parts[0].strip()
                operator = parts[1].strip()
                value = parts[2].strip()

                col = match_column(field, columns)
                if not col:
                    continue

                if operator == "range":
                    v1, v2 = map(int, value.split("-"))
                    value = (v1, v2)
                elif operator != "not_null":
                    value = int(value)

                rules.append({
                    "field": col,
                    "operator": operator,
                    "value": value
                })
            except:
                continue

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
# READ POLICY
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
# UI INPUT
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
        with st.spinner("AI generating rules..."):
            rules = generate_rules_ai(policy_text, data.columns)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Data")
        st.dataframe(data)

    with col2:
        st.subheader("AI Rules")
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
