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

    # ABOVE / GREATER THAN
    for field, _, value in re.findall(r'(\w+)\s+(above|greater than)\s+(\d+)', text):
        rules.append({
            "field": field.capitalize(),
            "operator": "min",
            "value": int(value),
            "severity": "High"
        })

    # BELOW / LESS THAN
    for field, _, value in re.findall(r'(\w+)\s+(below|less than)\s+(\d+)', text):
        rules.append({
            "field": field.capitalize(),
            "operator": "max",
            "value": int(value),
            "severity": "High"
        })

    # BETWEEN RANGE
    for field, v1, v2 in re.findall(r'(\w+)\s+between\s+(\d+)\s+and\s+(\d+)', text):
        rules.append({
            "field": field.capitalize(),
            "operator": "range",
            "value": (int(v1), int(v2)),
            "severity": "Medium"
        })

    # EQUALS
    for field, value in re.findall(r'(\w+)\s+equals\s+(\d+)', text):
        rules.append({
            "field": field.capitalize(),
            "operator": "equal",
            "value": int(value),
            "severity": "Medium"
        })

    # NOT NULL
    for field in re.findall(r'(\w+)\s+(must not be empty|mandatory|should not be empty)', text):
        rules.append({
            "field": field[0].capitalize(),
            "operator": "not_null",
            "value": None,
            "severity": "High"
        })

    # SLA HOURS
    for val in re.findall(r'within\s+(\d+)\s+hours', text):
        rules.append({
            "field": "Time",
            "operator": "max",
            "value": int(val),
            "severity": "Critical"
        })

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
# SIDEBAR
# ---------------------------
st.sidebar.header("Inputs")

data_file = st.sidebar.file_uploader("Upload Data CSV", type=["csv"])
rules_file = st.sidebar.file_uploader("Upload Rules CSV", type=["csv"])

policy_text = st.sidebar.text_area("Policy Text")
generate = st.sidebar.button("Generate Rules")

# ---------------------------
# LOAD RULES
# ---------------------------
rules = []

if generate and policy_text:
    rules = generate_rules_from_text(policy_text)
    st.session_state["rules"] = rules

elif "rules" in st.session_state:
    rules = st.session_state["rules"]

elif rules_file:
    rules_df = pd.read_csv(rules_file)
    rules = rules_df.to_dict(orient="records")

# ---------------------------
# MAIN
# ---------------------------
if data_file:

    data = pd.read_csv(data_file)

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

            c1, c2, c3 = st.columns(3)
            c1.metric("Total", total)
            c2.metric("Compliant", compliant)
            c3.metric("Violations", violations)

            # CHART
            chart = pd.DataFrame({
                "Status": ["Compliant", "Violations"],
                "Count": [compliant, violations]
            })
            st.bar_chart(chart.set_index("Status"))

            # RESULTS TABLE
            def highlight(row):
                return ['background-color: #ffcccc' if "❌" in row["Result"]
                        else 'background-color: #ccffcc'] * len(row)

            st.dataframe(data.style.apply(highlight, axis=1))

            # DOWNLOAD
            csv = data.to_csv(index=False).encode('utf-8')
            st.download_button("Download Report", csv, "output.csv")

else:
    st.info("Upload data to start")