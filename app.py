import streamlit as st
import pandas as pd
import re

st.set_page_config(layout="wide")

# ---------------------------
# CUSTOM UI STYLE
# ---------------------------
st.markdown("""
<style>
.box {
    background-color: #1f607a;
    padding: 35px;
    text-align: center;
    color: white;
    border-radius: 8px;
    font-size: 18px;
}
.result-box {
    background-color: #e3a389;
    padding: 25px;
    text-align: center;
    border-radius: 8px;
    font-size: 18px;
}
.center {
    display: flex;
    justify-content: center;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 Compliance Monitoring System")

# ---------------------------
# RULE GENERATOR
# ---------------------------
def generate_rules_from_text(policy_text):
    rules = []
    text = policy_text.lower()

    for field, _, value in re.findall(r'(\w+)\s+(above|greater than)\s+(\d+)', text):
        rules.append({"field": field.capitalize(), "operator": "min", "value": int(value)})

    for field, _, value in re.findall(r'(\w+)\s+(below|less than)\s+(\d+)', text):
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

        if op == "min" and row[f] < v:
            issues.append(f"{f} < {v}")

        elif op == "max" and row[f] > v:
            issues.append(f"{f} > {v}")

        elif op == "range":
            if not (v[0] <= row[f] <= v[1]):
                issues.append(f"{f} not in {v}")

    return "✅" if not issues else "❌"

# ---------------------------
# TOP UI (UPLOAD BOXES)
# ---------------------------
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="box">Upload Policy document</div>', unsafe_allow_html=True)
    policy_file = st.file_uploader("", type=["txt"], key="policy_file")

with col2:
    st.markdown('<div class="box">HR report doc (Testing document)</div>', unsafe_allow_html=True)
    data_file = st.file_uploader("", type=["csv"], key="data_file")

# ---------------------------
# READ POLICY TEXT
# ---------------------------
policy_text = ""

if policy_file is not None:
    try:
        policy_text = policy_file.read().decode("utf-8")
    except:
        policy_text = ""

# ---------------------------
# CENTER BUTTON
# ---------------------------
st.markdown("<br>", unsafe_allow_html=True)

st.markdown('<div class="center">', unsafe_allow_html=True)
run = st.button("Test Compliance")
st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------
# MAIN LOGIC
# ---------------------------
if run and data_file is not None and policy_text != "":

    data = pd.read_csv(data_file)
    rules = generate_rules_from_text(policy_text)

    data["Result"] = data.apply(lambda x: evaluate_rules(x, rules), axis=1)

    total = len(data)
    compliant = data[data["Result"] == "✅"].shape[0]
    non_compliant = total - compliant

    # ---------------------------
    # RESULT DASHBOARD
    # ---------------------------
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(f"""
    <div class="result-box">
        <h3>Results Dashboard</h3>
        <p>Total Records: {total}</p>
        <p>Compliant: {compliant} ✅</p>
        <p>Non-Compliant: {non_compliant} ❌</p>
    </div>
    """, unsafe_allow_html=True)

    # ---------------------------
    # TABLE
    # ---------------------------
    st.subheader("Detailed Results")
    st.dataframe(data)

    # ---------------------------
    # DOWNLOAD
    # ---------------------------
    csv = data.to_csv(index=False).encode("utf-8")
    st.download_button("Download Report", csv, "output.csv")

else:
    st.info("Upload policy (.txt) and data (.csv) and click Test Compliance")
