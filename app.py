import streamlit as st
import pandas as pd
import re
import spacy

# ---------------------------
# PAGE SETUP
# ---------------------------
st.set_page_config(page_title="Compliance System", layout="wide")
st.title("📊 NLP-Based Compliance Monitoring System")

# ---------------------------
# LOAD SPACY SAFELY
# ---------------------------
@st.cache_resource
def load_nlp():
    try:
        return spacy.load("en_core_web_sm")
    except:
        return None

nlp = load_nlp()

# ---------------------------
# RULE GENERATOR ✅ (NEVER EMPTY)
# ---------------------------
def generate_rules(policy_text, columns):
    rules = []

    text = policy_text.lower()

    # ---------------------------
    # ✅ SPAcY BASED EXTRACTION
    # ---------------------------
    if nlp:
        doc = nlp(policy_text)

        for sent in doc.sents:
            sentence = sent.text.lower()

            for col in columns:
                if col.lower() not in sentence:
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

                if nums:
                    val = int(nums[0])

                    if any(x in sentence for x in ["above", "greater", "minimum", "at least"]):
                        rules.append({"field": col, "operator": "min", "value": val})

                    elif any(x in sentence for x in ["below", "less", "maximum", "at most"]):
                        rules.append({"field": col, "operator": "max", "value": val})

                    elif any(x in sentence for x in ["equal", "equals", "is"]):
                        rules.append({"field": col, "operator": "equal", "value": val})

                # NOT NULL
                if any(x in sentence for x in ["mandatory", "required", "not empty"]):
                    rules.append({"field": col, "operator": "not_null", "value": None})

    # ---------------------------
    # ✅ FALLBACK (ENSURES RULES)
    # ---------------------------
    sentences = re.split(r"[.\n]", text)

    for sentence in sentences:
        for col in columns:

            if col.lower() not in sentence:
                continue

            nums = re.findall(r"\d+", sentence)

            if "between" in sentence and len(nums) >= 2:
                rules.append({
                    "field": col,
                    "operator": "range",
                    "value": (int(nums[0]), int(nums[1]))
                })
                continue

            if not nums:
                continue

            val = int(nums[0])

            if any(x in sentence for x in ["above", "at least", "min"]):
                rules.append({"field": col, "operator": "min", "value": val})

            elif any(x in sentence for x in ["below", "at most", "max"]):
                rules.append({"field": col, "operator": "max", "value": val})

    # ✅ REMOVE DUPLICATES
    unique_rules = []
    seen = set()
    for r in rules:
        key = (r["field"], r["operator"], str(r["value"]))
        if key not in seen:
            seen.add(key)
            unique_rules.append(r)

    return unique_rules

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
# UI
# ---------------------------
st.sidebar.header("Inputs")

data_file = st.sidebar.file_uploader("Upload Dataset", ["csv", "xlsx"])
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
