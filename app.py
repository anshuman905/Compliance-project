import streamlit as st
import pandas as pd
import re
import requests

# ---------------------------
# PAGE SETUP
# ---------------------------
st.set_page_config(page_title="Compliance System", layout="wide")
st.title("📊 AI Compliance Monitoring System")

# ---------------------------
# HF CONFIG (SAFE)
# ---------------------------
HF_TOKEN = st.secrets.get("HF_TOKEN", None)
API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-base"

headers = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}

# ---------------------------
# SAFE HF CALL ✅
# ---------------------------
def query_hf(prompt):
    if not HF_TOKEN:
        return ""

    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json={"inputs": prompt},
            timeout=20
        )

        if response.status_code != 200:
            return ""

        result = response.json()

        if isinstance(result, list) and "generated_text" in result[0]:
            return result[0]["generated_text"]

        return ""

    except:
        return ""

# ---------------------------
# LLM RULE GENERATOR
# ---------------------------
def generate_rules_llm(policy_text, columns):
    prompt = f"""
    Convert policy into rules.

    Format: field, operator, value
    Operators: min, max, range, equal, not_null

    Policy: {policy_text}
    Columns: {list(columns)}
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
# REGEX FALLBACK ✅
# ---------------------------
def generate_rules_from_text(policy_text, columns):
    rules = []
    text = policy_text.lower()

    for field, _, value in re.findall(r'(\w+)\s+(above|greater than|at least|min|minimum)\s+(\d+)', text):
        rules.append({"field": field.capitalize(), "operator": "min", "value": int(value)})

    for field, _, value in re.findall(r'(\w+)\s+(below|less than|at most|max|maximum)\s+(\d+)', text):
        rules.append({"field": field.capitalize(), "operator": "max", "value": int(value)})

    for field, v1, v2 in re.findall(r'(\w+)\s+between\s+(\d+)\s+and\s+(\d+)', text):
        rules.append({"field": field.capitalize(), "operator": "range", "value": (int(v1), int(v2))})

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
# READ POLICY FILE ✅
# ---------------------------
def read_policy_file(file):
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

data_file = st.sidebar.file_uploader("Upload Data", type=["csv", "xlsx"])
policy_file = st.sidebar.file_uploader("Upload Rules", type=["txt", "csv", "docx", "pdf"])

policy_text = st.sidebar.text_area("Or paste policy")

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
        st.error("❌ Error reading dataset")
        st.stop()

    # GET POLICY TEXT
    if policy_file:
        policy_text = read_policy_file(policy_file)

    # ✅ AUTO RULE GENERATION (AI + FALLBACK)
    if policy_text:
        rules = generate_rules_llm(policy_text, data.columns)

        if not rules:
            st.warning("⚠️ AI unavailable → using fallback rules")
            rules = generate_rules_from_text(policy_text, data.columns)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Data")
        st.dataframe(data)

    with col2:
        st.subheader("Rules")
        st.write(rules if rules else "No rules generated")

    # SEARCH
    search = st.text_input("Search")

    if search:
        data = data[data.astype(str).apply(
            lambda r: r.str.contains(search, case=False, na=False)
        ).any(axis=1)]

    # RUN
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
    st.info("Upload dataset to start")
