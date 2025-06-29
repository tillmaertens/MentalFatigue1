from otree.api import *

doc = """
Applicants Selection Interface - allows selection between different applicant profiles
"""


class Applicant:
    """Class for a single applicant"""

    def __init__(self, applicant_id, name, description):
        self.id = applicant_id
        self.name = name
        self.description = description

    def get_documents(self):
        """Automatically generates document paths for this applicant"""
        return {
            'cv': f'applicants_{self.id}/cv_{self.id}.pdf',
            'job_reference': f'applicants_{self.id}/job_reference_{self.id}.pdf',
            'cover_letter': f'applicants_{self.id}/cover_letter_{self.id}.pdf'
        }

    def to_dict(self):
        """Converts the applicant to a dictionary for templates"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'documents': self.get_documents()
        }


# Functions before class definition
def create_applicants():
    applicants = []

    # Create applicant objects
    applicant_a = Applicant(
        applicant_id='a',
        name='Applicant A',
        description='Experienced software developer with 5 years in web development.'
    )

    applicant_b = Applicant(
        applicant_id='b',
        name='Applicant B',
        description='Marketing specialist with international experience and strong analytical skills.'
    )

    applicant_c = Applicant(
        applicant_id='c',
        name='Applicant C',
        description='Project manager with expertise in agile methodologies and team leadership.'
    )

    # Add objects to list
    applicants.append(applicant_a)
    applicants.append(applicant_b)
    applicants.append(applicant_c)

    return applicants


def get_applicants_data():
    applicant_objects = create_applicants()
    return [applicant.to_dict() for applicant in applicant_objects]


class C(BaseConstants):
    NAME_IN_URL = 'applicants'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

    # Data for templates
    APPLICANTS = get_applicants_data()


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    # Field to store which player role was selected
    selected_player = models.StringField(
        choices=['Recruiter', 'HR-Coordinator', 'Business-Partner'],
        blank=True
    )

    # Data tracking fields
    page_start_time = models.FloatField(blank=True)
    applicants_viewed = models.LongStringField(blank=True)
    time_spent_per_applicant = models.LongStringField(blank=True)