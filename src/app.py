import streamlit as st
from scripts import flatten_student_worksheet
import io

st.title("Student Worksheet Flattener")

student_worksheet_file: io.BytesIO | None = None
with st.form("input_student_worksheet"):
    student_worksheet_file = st.file_uploader("Student Worksheet", type=["csv"])
    student_worksheet_submitted = st.form_submit_button("Flatten Worksheet")
    max_domain_count = st.number_input(
        "Maximum Number of Domains",
        min_value=1,
        value=10,
        step=1,
        help=(
            "The maximum number of domains for any given worksheet. "
            "If fewer domains are present, the relevant cell values will be empty"
        ),
    )
    max_question_count = st.number_input(
        "Maximum Number of Questions",
        min_value=1,
        value=100,
        step=1,
        help=(
            "The maximum number of questions for any given assessment. "
            "If fewer questions are present on an assessment, the relevant cell values will be empty"
        ),
    )

    if student_worksheet_submitted:
        if not student_worksheet_file:
            st.markdown(
                '<span style="color:red">**Please upload the student worksheet in CSV format**</span>',
                unsafe_allow_html=True,
            )


if student_worksheet_file:
    flattened_student_worksheet_path = flatten_student_worksheet.main(
        student_worksheet_file, max_domain_count=int(max_domain_count), max_question_count=int(max_question_count)
    )

    new_filename = f"flattened-{student_worksheet_file.name}"
    if new_filename.split(".")[-1].lower() != "csv":
        new_filename += ".csv"

    with open(flattened_student_worksheet_path) as f:
        st.download_button(
            "Download Flattened Student Worksheet",
            f,
            file_name=new_filename,
            mime="text/csv",
        )
