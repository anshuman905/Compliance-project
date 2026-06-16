import streamlit as st
import pandas as pd
import re

# ---------------------------
# PAGE SETUP
# ---------------------------
st.set_page_config(page_title="Compliance System", layout="wide")
st.title("📊 AI-like Compliance Monitoring System")

# ---------------------------
# COLUMN MATCH
# ---------------------------
def match_column(sentence, columns):
    for col in columns:
        if col.lower() in sentence:
            return col
    return None

# ---------------------------
# RULE GENERATOR
# ---------------------------
def generate_rules(policy_text, columns):
    rules = []
    text = policy_text.lower()

    sentences = re.split(r"[.\n]", text)

    for sentence in sentences:

        if len(sentence.strip()) < 5:
            continue

        col = match_column(sentence, columns)
        if not col:
            continue

        nums = re.findall(r"\d+", sentence)

        # RANGE
        if "between" in sentence and len(nums) >= 2:
            rules.append({
                "field": col,
                "operator": "range",
                "value": (int(nums[0]), int(nums[1]))
            })
            continue

        # NOT NULL
        if any(w in sentence for w in [
            "mandatory", "required", "must be filled",
            "cannot be empty", "should not be empty"
        ]):
            rules.append({
                "field": col,
                "operator": "not_null",
                "value": None
            })
            continue

        if not nums:
            continue

        value = int(nums[0])

        # MIN
        if any(w in sentence for w in [
            "minimum", "at least", "not less", "above", "greater"
        ]):
            rules.append({
                "field": col,
                "operator": "min",
                "value": value
            })
            continue

        # MAX
        if any(w in sentence for w in [
            "maximum", "at most", "not more", "below", "less"
        ]):
            rules.append({
                "field": col,
                "operator": "max",
                "value": value
            })
            continue

        # EQUAL
        if any(w in sentence for w in [
            "equal", "equals", "fixed", "exact", "must be"
        ]):
            rules.append({
                "field": col,
                "operator": "equal",
                "value": value
            })

    # SAFE FALLBACK
    if not rules and len(columns) > 0:
        rules.append({
            "field": columns[0],
            "operator": "not_null",
            "value": None
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
# SIDEBAR (UPDATED ✅)
# ---------------------------
st.sidebar.header("Inputs")

# ✅ Policy FIRST
policy_file = st.sidebar.file_uploader("Upload Policy Documents", ["txt", "csv", "docx", "pdf"])
policy_text = st.sidebar.text_area("Or paste policy")

# ✅ Dataset BELOW
data_file = st.sidebar.file_uploader("Upload Dataset", ["csv", "xlsx"])

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
        st.write(rules)

    if st.button("Run Compliance Check"):

        data["Result"] = data.apply(lambda x: evaluate_rules(x, rules), axis=1)

        total = len(data)
        compliant = (data["Result"] == "✅ Compliant").sum()

        st.markdown(f"""
        <div style="background:#e3a389;padding:20px;border-radius:8px;text-align:center;">
            <h3>Results Dashboard</h3>
            <p>Total: {total}</p>
            <p>Compliant: {compliant} ✅</p>
            <p>Non-Compliant: {total - compliant} ❌</p>
        </div>
        """, unsafe_allow_html=True)

        st.dataframe(data)

else:
    st.info("Upload dataset to start")
