import streamlit as st
import pandas as pd
import re
import requests

# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(page_title="Compliance System", layout="wide")
st.title("📊 AI Compliance Monitoring System")

HF_TOKEN = st.secrets["HF_TOKEN"]
API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-large"

headers = {"Authorization": f"Bearer {HF_TOKEN}"}

# ---------------------------
# CALL HUGGING FACE
# ---------------------------
def query_hf(prompt):
    payload = {"inputs": prompt}
    response = requests.post(API_URL, headers=headers, json=payload)

    if response.status_code != 200:
        return ""

    try:
        return response.json()[0]["generated_text"]
    except:
        return ""

# ---------------------------
# LLM RULE GENERATOR ✅
# ---------------------------
def generate_rules_llm(policy_text, columns):

    prompt = f"""
    Convert the following policy into structured rules.

    Output format:
    field, operator, value

    Operators allowed: min, max, range, equal, not_null

    Policy:
    {policy_text}

    Columns available:
    {list(columns)}

    Return only rules.
    """

    result = query_hf(prompt)

    rules = []

    for line in result.split("\n"):
        parts = line.split(",")
        if len(parts) >= 3:
            try:
                field = parts[0].strip()
                operator = parts[1].strip()
                value = parts[2].strip()

                if operator == "range":
                    v1, v2 = map(int, value.split("-"))
                    value = (v1, v2)
                elif operator != "not_null":
                    value = int(value)

                rules.append({
                    "field": field,
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

    return "✅ Compliant" if not issues else "❌ " + ", ".join(issues)

# ---------------------------
# READ RULE FILES
# ---------------------------
def read_rules_file(file):
    try:
        if file.name.endswith(".txt"):
            return file.read().decode("utf-8")

        elif file.name.endswith(".docx"):
            from docx import Document
            doc = Document(file)
            return " ".join([p.text for p in doc.paragraphs])

        elif file.name.endswith(".pdf"):
            from PyPDF2 import PdfReader
            reader = PdfReader(file)
            return " ".join([p.extract_text() or "" for p in reader.pages])

        elif file.name.endswith(".csv"):
            df = pd.read_csv(file)
            return " ".join(df.astype(str).values.flatten())

    except:
        return ""

    return ""

# ---------------------------
# SIDEBAR
# ---------------------------
st.sidebar.header("Inputs")

data_file = st.sidebar.file_uploader("Upload Data", type=["csv", "xlsx"])
rules_file = st.sidebar.file_uploader("Upload Policy File", type=["csv", "txt", "docx", "pdf"])

policy_text = st.sidebar.text_area("Or paste policy text")
generate = st.sidebar.button("Generate Rules (AI)")

rules = []

# ---------------------------
# MAIN
# ---------------------------
if data_file:

    # READ DATA
    try:
        if data_file.name.endswith(".csv"):
            data = pd.read_csv(data_file)
        else:
            data = pd.read_excel(data_file, engine="openpyxl")
    except:
        st.error("Error reading dataset")
        st.stop()

    # POLICY INPUT
    if rules_file:
        policy_text = read_rules_file(rules_file)

    if generate and policy_text:
        rules = generate_rules_llm(policy_text, data.columns)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Data")
        st.dataframe(data)

    with col2:
        st.subheader("AI Generated Rules")
        st.write(rules if rules else "No rules")

    # SEARCH
    search = st.text_input("Search")

    if search:
        data = data[data.astype(str).apply(
            lambda r: r.str.contains(search, case=False, na=False)
        ).any(axis=1)]

    if st.button("Run Compliance Check"):

        if not rules:
            st.error("No rules generated")
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
    st.info("Upload dataset to start")
``
