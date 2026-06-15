import streamlit as st
import pandas as pd
import re

# ---------------------------
# PAGE SETUP
# ---------------------------
st.set_page_config(page_title="Compliance System", layout="wide")
st.title("📊 Compliance Monitoring System")

# ---------------------------
# RULE GENERATOR
# ---------------------------
def generate_rules_from_text(policy_text):
    rules = []
    text = policy_text.lower()

    for field, _, value in re.findall(r'(\w+)\s+(above|greater than)\s+(\d+)', text):
        rules.append({"field": field.capitalize(), "operator": "min", "value": int(value), "severity": "High"})

    for field, _, value in re.findall(r'(\w+)\s+(below|less than)\s+(\d+)', text):
        rules.append({"field": field.capitalize(), "operator": "max", "value": int(value), "severity": "High"})

    for field, v1, v2 in re.findall(r'(\w+)\s+between\s+(\d+)\s+and\s+(\d+)', text):
        rules.append({"field": field.capitalize(), "operator": "range", "value": (int(v1), int(v2)), "severity": "Medium"})

    for field, value in re.findall(r'(\w+)\s+equals\s+(\d+)', text):
        rules.append({"field": field.capitalize(), "operator": "equal", "value": int(value), "severity": "Medium"})

    for field in re.findall(r'(\w+)\s+(must not be empty|mandatory|should not be empty)', text):
        rules.append({"field": field[0].capitalize(), "operator": "not_null", "value": None, "severity": "High"})

    for val in re.findall(r'within\s+(\d+)\s+hours', text):
        rules.append({"field": "Time", "operator": "max", "value": int(val), "severity": "Critical"})

    return rules

# ---------------------------
# RULE ENGINE
# ---------------------------
def evaluate_rules(row, rules):
    issues = []

    for rule in rules:
        field = rule["field"]
        operator = rule["operator"]
        value = rule["value"]
        severity = rule["severity"]

        if field not in row:
            continue

        if operator == "min" and row[field] < value:
            issues.append(f"{field} < {value} ({severity})")

        elif operator == "max" and row[field] > value:
            issues.append(f"{field} > {value} ({severity})")

        elif operator == "range":
            if not (value[0] <= row[field] <= value[1]):
                issues.append(f"{field} not in range {value} ({severity})")

        elif operator == "equal" and row[field] != value:
            issues.append(f"{field} != {value} ({severity})")

        elif operator == "not_null" and pd.isna(row[field]):
            issues.append(f"{field} is null ({severity})")

    return "✅ Compliant" if not issues else "❌ " + ", ".join(issues)

# ---------------------------
# READ RULE FILE (ADDED)
# ---------------------------
def read_rules_file(file):
    if file.name.endswith(".txt"):
        return generate_rules_from_text(file.read().decode("utf-8"))

    elif file.name.endswith(".csv"):
        df = pd.read_csv(file)
        return df.to_dict(orient="records")

    elif file.name.endswith(".docx"):
        from docx import Document
        doc = Document(file)
        text = " ".join([p.text for p in doc.paragraphs])
        return generate_rules_from_text(text)

    return []

# ---------------------------
# SIDEBAR
# ---------------------------
st.sidebar.header("Inputs")

data_file = st.sidebar.file_uploader("Upload Data", type=["csv", "xlsx"])
rules_file = st.sidebar.file_uploader("Upload Rules File", type=["csv", "txt", "docx"])

policy_text = st.sidebar.text_area("Policy Text")
generate = st.sidebar.button("Generate Rules")

# ---------------------------
# LOAD RULES
# ---------------------------
rules = []

if rules_file:
    rules = read_rules_file(rules_file)

elif generate and policy_text:
    rules = generate_rules_from_text(policy_text)
    st.session_state["rules"] = rules

elif "rules" in st.session_state:
    rules = st.session_state["rules"]

# ---------------------------
# MAIN
# ---------------------------
if data_file:

    if data_file.name.endswith(".csv"):
        data = pd.read_csv(data_file)
    else:
        data = pd.read_excel(data_file, engine="openpyxl")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Data")
        st.dataframe(data)

    with col2:
        st.subheader("Rules")
        st.write(rules if rules else "No rules")

    # SEARCH
    search = st.text_input("Search Name")

    if search:
        data = data[data["Name"].astype(str).str.contains(search, case=False, na=False)]

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
            <div style="background-color:#e3a389;padding:25px;border-radius:8px;text-align:center;font-size:18px;">
                <h3>Results Dashboard</h3>
                <p>Total Records: {total}</p>
                <p>Compliant: {compliant} ✅</p>
                <p>Non-Compliant: {violations} ❌</p>
            </div>
            """, unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            c1.metric("Total", total)
            c2.metric("Compliant", compliant)
            c3.metric("Violations", violations)

            chart = pd.DataFrame({
                "Status": ["Compliant", "Violations"],
                "Count": [compliant, violations]
            })
            st.bar_chart(chart.set_index("Status"))

            def highlight(row):
                return ['background-color: #ffcccc' if "❌" in row["Result"]
                        else 'background-color: #ccffcc'] * len(row)

            st.dataframe(data.style.apply(highlight, axis=1))

            csv = data.to_csv(index=False).encode('utf-8')
            st.download_button("Download Report", csv, "output.csv")

else:
    st.info("Upload data to start")
