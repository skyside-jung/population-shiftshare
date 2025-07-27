
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io

st.title("Chungnam Population Forecast Comparison (Shift-Share Model)")

uploaded_file = st.file_uploader("Upload Excel file with input and national population", type="xlsx")

if uploaded_file:
    # Load sheets
    df_effect = pd.read_excel(uploaded_file, sheet_name="충남_효과산정")
    df_actual = pd.read_excel(uploaded_file, sheet_name="충청남도")
    df_national = pd.read_excel(uploaded_file, sheet_name="전국총인구_연령별")

    df_effect = df_effect[df_effect["Age_Group"] != "합계"]
    df_actual = df_actual[df_actual["Age_Group"] != "합계"]
    df_national = df_national[df_national["Age_Group"] != "합계"]
    df_actual["Actual_2024"] = df_actual.iloc[:, 3]

    # ------ First Prediction using 2018–2019 derived Ng, Im ------
    pop = df_effect["V_ij_t"].copy()
    for _ in range(5):
        rs_step = pop + df_effect["Rs"]
        im_step = 0.2 * rs_step.shift(1, fill_value=rs_step[0]) + 0.8 * rs_step
        ng_factor = df_effect["V_t1"].iloc[0] / df_effect["V_t"].iloc[0]
        pop = (ng_factor * im_step).round()
    df_effect["Predicted_2024_v1"] = pop.astype(int)

    df_compare_v1 = pd.merge(
        df_effect[["Age_Group", "Predicted_2024_v1"]],
        df_actual[["Age_Group", "Actual_2024"]],
        on="Age_Group",
        how="inner"
    )
    df_compare_v1["Diff_v1"] = df_compare_v1["Predicted_2024_v1"] - df_compare_v1["Actual_2024"]
    df_compare_v1["Diff(%)_v1"] = (df_compare_v1["Diff_v1"] / df_compare_v1["Actual_2024"] * 100).round(2)

    # ------ Second Prediction using 2024 national population for Ng/Im ------
    v_total_2018 = df_national["2018"].sum()
    v_total_2024 = df_national[2024].sum()
    ng_ratio = v_total_2024 / v_total_2018
    df_effect["Ng_2024"] = df_effect["V_ij_t"] * (ng_ratio - 1)

    v_i_2018 = df_national["2018"].values
    v_i_2024 = df_national[2024].values
    im_terms = (v_i_2024 / v_i_2018) - (v_total_2024 / v_total_2018)
    df_effect["Im_2024"] = df_effect["V_ij_t"] * im_terms

    df_effect["Predicted_2024_v2"] = (
        df_effect["V_ij_t"] + df_effect["Ng_2024"] + df_effect["Im_2024"] + df_effect["Rs"]
    ).round().astype(int)

    df_compare_v2 = pd.merge(
        df_effect[["Age_Group", "Predicted_2024_v2"]],
        df_actual[["Age_Group", "Actual_2024"]],
        on="Age_Group",
        how="inner"
    )
    df_compare_v2["Diff_v2"] = df_compare_v2["Predicted_2024_v2"] - df_compare_v2["Actual_2024"]
    df_compare_v2["Diff(%)_v2"] = (df_compare_v2["Diff_v2"] / df_compare_v2["Actual_2024"] * 100).round(2)

    # ------ Visualization ------
    st.subheader("1. Prediction Error Comparison")
    df_result = pd.merge(
        df_compare_v1[["Age_Group", "Predicted_2024_v1", "Diff(%)_v1"]],
        df_compare_v2[["Age_Group", "Predicted_2024_v2", "Diff(%)_v2"]],
        on="Age_Group"
    )
    df_result = pd.merge(df_result, df_actual[["Age_Group", "Actual_2024"]], on="Age_Group")
    st.dataframe(df_result)

    st.subheader("2. Line Chart: Actual vs Predictions")
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    ax1.plot(df_result["Age_Group"], df_result["Actual_2024"], label="Actual", marker="s")
    ax1.plot(df_result["Age_Group"], df_result["Predicted_2024_v1"], label="Predicted (2018–2019 Ng/Im)", marker="o")
    ax1.plot(df_result["Age_Group"], df_result["Predicted_2024_v2"], label="Predicted (2024 National Ng/Im)", marker="^")
    ax1.set_title("Population Forecast vs Actual by Age Group")
    ax1.set_xlabel("Age Group")
    ax1.set_ylabel("Population")
    ax1.legend()
    ax1.tick_params(axis='x', rotation=45)
    ax1.grid(True)
    st.pyplot(fig1)

    st.subheader("3. Bar Chart: Error Rate Comparison")
    fig2, ax2 = plt.subplots(figsize=(12, 5))
    bar_width = 0.35
    x = range(len(df_result))
    ax2.bar(x, df_result["Diff(%)_v1"], width=bar_width, label="2018–2019 Ng/Im")
    ax2.bar([i + bar_width for i in x], df_result["Diff(%)_v2"], width=bar_width, label="2024 National Ng/Im")
    ax2.set_xticks([i + bar_width / 2 for i in x])
    ax2.set_xticklabels(df_result["Age_Group"], rotation=45)
    ax2.set_ylabel("Error Rate (%)")
    ax2.set_title("Prediction Error Rate by Age Group")
    ax2.axhline(0, color='gray', linestyle='--')
    ax2.legend()
    ax2.grid(True)
    st.pyplot(fig2)

    # ------ Excel Export ------
    st.subheader("4. Download Comparison Result")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_result.to_excel(writer, index=False, sheet_name="Comparison")
        df_effect.to_excel(writer, index=False, sheet_name="Effect_Data")
        writer.close()
    st.download_button(
        label="Download Comparison Result (.xlsx)",
        data=buffer.getvalue(),
        file_name="Chungnam_2024_Prediction_Comparison.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
