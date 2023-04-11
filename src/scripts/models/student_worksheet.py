from pydantic import BaseModel, validator
from enum import Enum


class OutputColums(Enum):
    session_id = "session_id"
    test_date = "test_date"
    student_guid = "student_guid"
    subject = "subject"
    assessment_guid = "assessment_guid"
    calculated_raw_score = "calculated_raw_score"
    scaled_score_based_on_calculated = "scaled_score_based_on_calculated"
    question_domain = "question_domain"
    domain_raw_score = "domain_raw_score"
    total_time_spent_on_test = "total_time_spent_on_test"
    time_spent_on_item = "time_spent_on_item"
    response_value = "response_value"
    response_raw_score = "response_raw_score"


class ResponseIn(BaseModel):
    """A single response row"""

    student_guid: str
    subject: str
    session_id: str
    response_id: str
    question_id: str
    item_reference_id: str
    assessment_guid: str

    test_date: str
    form_name: str
    total_time_spent_on_test: int
    number_of_items: int
    number_of_operational_items: int

    attempted: bool
    is_operational_question: bool
    question_type: str
    time_spent_on_item: int
    response_value: int
    response_raw_score: int
    response_max_score: int

    calculated_raw_score: int
    calculated_operational_score: int
    max_operational_score: int
    scaled_score_based_on_calculated: int

    question_domain: str
    domain_raw_score: int
    domain_max_score: int

    dt_score_updated: str
    dt_saved: str


class Response(ResponseIn):
    question_counter: int

    @classmethod
    def question_domain_header(cls, counter: int) -> str:
        return f"Question Domain {counter} Name"

    @classmethod
    def question_domain_raw_score_header(cls, counter: int) -> str:
        return f"Question Domain {counter} Raw Score"

    @classmethod
    def time_spent_on_item_header(cls, counter: int) -> str:
        return f"Time Spent on Question {counter}"

    @classmethod
    def response_value_header(cls, counter: int) -> str:
        return f"Response Value for Question {counter}"

    @classmethod
    def response_raw_score_header(cls, counter: int) -> str:
        return f"Response Raw Score for Question {counter}"


class Assessment(BaseModel):
    """A single consolidated test row for a particular student"""

    assessment_guid: str
    subject: str

    test_date: str
    total_time_spent_on_test: int

    calculated_raw_score: int
    scaled_score_based_on_calculated: int

    responses: list[Response]

    @validator("responses", pre=True)
    def parse_raw_responses(cls, v) -> list[Response]:
        wrong_type_error_message = "responses must be a list of `ResponseIn`"
        if not isinstance(v, list):
            raise ValueError(wrong_type_error_message)

        responses: list[Response] = []
        for i, raw_response in enumerate(v):
            if isinstance(raw_response, Response):
                responses.append(raw_response)
                continue

            elif not isinstance(raw_response, ResponseIn):
                raise ValueError(wrong_type_error_message)

            data = raw_response.dict() | {"question_counter": i + 1}  # question counters start at 1
            responses.append(Response.parse_obj(data))

        return responses


class Student(BaseModel):
    student_guid: str
    assessments: list[Assessment]


class DomainStudent(BaseModel):
    student_guid: str
    domain_raw_score: int
    domain_max_score: int


class Domain(BaseModel):
    question_domain: str
    domain_students: dict[str, DomainStudent] = {}


class Session(BaseModel):
    session_id: str
    domains: dict[str, Domain] = {}
    students: list[Student]

    def populate_domains(self) -> None:
        for student in self.students:
            for assessment in student.assessments:
                for response in assessment.responses:
                    if response.question_domain not in self.domains:
                        self.domains[response.question_domain] = Domain(question_domain=response.question_domain)

                    # all domain raw scores and max scores are the same per-student per-domain,
                    # so if the StudentDomain is missing, we use the values of this response
                    if student.student_guid not in self.domains[response.question_domain].domain_students:
                        self.domains[response.question_domain].domain_students[student.student_guid] = DomainStudent(
                            student_guid=student.student_guid,
                            domain_raw_score=response.domain_raw_score,
                            domain_max_score=response.domain_max_score,
                        )
