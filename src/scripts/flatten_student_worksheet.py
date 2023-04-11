from collections import defaultdict
import io
from tempfile import NamedTemporaryFile
import csv
from typing import Any
from scripts.models.student_worksheet import OutputColums, Response, ResponseIn, Assessment, Session, Student


def parse_student_worksheet(student_worksheet: io.BytesIO) -> list[ResponseIn]:
    student_worksheet.seek(0)
    wrapper = io.TextIOWrapper(student_worksheet, encoding="utf-8")
    return [ResponseIn.parse_obj(row) for row in csv.DictReader(wrapper)]


def build_sessions(raw_responses: list[ResponseIn]) -> list[Session]:
    """Convert a list of raw response rows into a structured list of sessions"""

    # Build hierarchy of Session -> Student -> Assessment -> Responses
    session_data: dict[str, dict[str, dict[str, list[ResponseIn]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    for response in raw_responses:
        session_data[response.session_id][response.student_guid][response.assessment_guid].append(response)

    # Loop through each nested collection and generate sessions
    sessions: list[Session] = []
    for session_id, student_data in session_data.items():
        students: list[Student] = []
        for student_guid, assessment_data in student_data.items():
            assessments: list[Assessment] = []
            for raw_responses in assessment_data.values():
                # all raw responses share the same top-level assessment data
                data = raw_responses[0].dict() | {"responses": raw_responses}
                assessments.append(Assessment.parse_obj(data))

            students.append(Student(student_guid=student_guid, assessments=assessments))
        new_session = Session(session_id=session_id, students=students)
        new_session.populate_domains()
        sessions.append(new_session)

    return sessions


def build_header_row(max_domain_count: int, max_question_count: int) -> list[str]:
    row: list[str] = []
    for column in OutputColums:
        # Domain Fields
        if column is OutputColums.question_domain:
            row.extend([Response.question_domain_header(i + 1) for i in range(max_domain_count)])

        elif column is OutputColums.domain_raw_score:
            row.extend([Response.question_domain_raw_score_header(i + 1) for i in range(max_domain_count)])

        # Response Fields
        elif column is OutputColums.time_spent_on_item:
            row.extend([Response.time_spent_on_item_header(i + 1) for i in range(max_question_count)])

        elif column is OutputColums.response_value:
            row.extend([Response.response_value_header(i + 1) for i in range(max_question_count)])

        elif column is OutputColums.response_raw_score:
            row.extend([Response.response_raw_score_header(i + 1) for i in range(max_question_count)])

        # Everything Else
        else:
            row.append(str(column.value))

    return row


def pad_row(row: list[str | None], actual_length: int, max_length: int) -> None:
    """Pad a row with extra empty cells if the actual length of a list is smaller than the max length"""

    if actual_length >= max_length:
        return

    row.extend([None] * (max_length - actual_length))


def build_rows_from_session(session: Session, max_domain_count: int, max_question_count: int) -> list[list[str | None]]:
    """Build a list of new CSV rows from a given session"""

    domains = list(session.domains.values())
    domains.sort(key=lambda x: x.question_domain)

    rows: list[list[str | None]] = []
    for student in session.students:
        for assessment in student.assessments:
            row: list[str | None] = []
            for column in OutputColums:
                # Parent Fields
                if column is OutputColums.session_id:
                    row.append(session.session_id)

                elif column is OutputColums.student_guid:
                    row.append(student.student_guid)

                # Domain Fields
                elif column is OutputColums.question_domain:
                    for domain in domains:
                        row.append(domain.question_domain)
                    pad_row(row, len(domains), max_domain_count)

                elif column is OutputColums.domain_raw_score:
                    for domain in domains:
                        domain_student = domain.domain_students.get(student.student_guid)
                        row.append(str(domain_student.domain_raw_score)) if domain_student else None
                    pad_row(row, len(domains), max_domain_count)

                # Response Fields
                elif column is OutputColums.time_spent_on_item:
                    for response in assessment.responses[:max_question_count]:
                        row.append(str(response.time_spent_on_item))
                    pad_row(row, len(assessment.responses), max_question_count)

                elif column is OutputColums.response_value:
                    for response in assessment.responses[:max_question_count]:
                        row.append(str(response.response_value))
                    pad_row(row, len(assessment.responses), max_question_count)

                elif column is OutputColums.response_raw_score:
                    for response in assessment.responses[:max_question_count]:
                        row.append(str(response.response_raw_score))
                    pad_row(row, len(assessment.responses), max_question_count)

                # Assessment Fields
                else:
                    value = getattr(assessment, column.value)
                    row.append(str(value))

            rows.append(row)

    return rows


def build_flattened_csv(sessions: list[Session], max_domain_count: int, max_question_count: int) -> str:
    """Build a new CSV file from a list of sessions and return the new filepath"""

    csv_file = NamedTemporaryFile(delete=False)
    with open(csv_file.name, "w") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(build_header_row(max_domain_count=max_domain_count, max_question_count=max_question_count))
        for session in sessions:
            csv_writer.writerows(
                build_rows_from_session(
                    session, max_domain_count=max_domain_count, max_question_count=max_question_count
                )
            )

    return csv_file.name


def main(student_worksheet: io.BytesIO, max_domain_count: int, max_question_count: int) -> str:
    """Flattens a student worksheet and returns the full path of the new flattened file"""

    raw_responses = parse_student_worksheet(student_worksheet)
    sessions = build_sessions(raw_responses)
    return build_flattened_csv(sessions, max_domain_count=max_domain_count, max_question_count=max_question_count)
