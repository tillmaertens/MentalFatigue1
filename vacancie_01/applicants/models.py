from otree.api import *
import json

doc = """
Applicants Selection Interface
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


def create_applicants():
    """Create applicant objects"""
    applicants = []

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

    applicants.extend([applicant_a, applicant_b, applicant_c])
    return applicants


def get_applicants_data():
    """Get applicants data for templates"""
    applicant_objects = create_applicants()
    return [applicant.to_dict() for applicant in applicant_objects]


class C(BaseConstants):
    NAME_IN_URL = 'applicants'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

    # Data for templates
    APPLICANTS = get_applicants_data()

    # Evaluation settings
    MIN_SCORE = 0
    MAX_SCORE = 8

    # Relevance factors for Nutzwertanalyse
    RELEVANCE_FACTORS = {
        'low': 1,
        'normal': 2,
        'high': 3
    }


class Subsession(BaseSubsession):
    """Subsession model"""

    def creating_session(self):
        """Initialize session data"""
        pass


class Group(BaseGroup):
    """Group model - simplified without metadata complexity"""

    # Store simple evaluation data as JSON
    evaluation_data = models.LongStringField(
        initial='{}',
        doc="JSON string containing evaluation criteria and user scores"
    )

    def get_evaluation_data(self):
        """Get evaluation data as Python dictionary"""
        try:
            return json.loads(self.evaluation_data) if self.evaluation_data else {}
        except json.JSONDecodeError:
            return {}

    def set_evaluation_data(self, data_dict):
        """Set evaluation data from Python dictionary"""
        self.evaluation_data = json.dumps(data_dict)


class Player(BasePlayer):
    """Player model for individual data"""

    # Role selection
    selected_player = models.StringField(
        choices=['Recruiter', 'HR-Coordinator', 'Business-Partner'],
        blank=True,
        doc="Selected player role"
    )

    # Activity tracking
    page_start_time = models.FloatField(
        blank=True,
        doc="Timestamp when page was loaded"
    )

    # HR Coordinator specific fields
    criteria_added = models.IntegerField(
        initial=0,
        doc="Number of criteria added by this player"
    )

    scores_entered = models.IntegerField(
        initial=0,
        doc="Number of scores entered by this player"
    )