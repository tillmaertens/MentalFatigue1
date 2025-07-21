from otree.api import *
import json
import time
import pandas as pd
import os

doc = """
Mental Fatigue Experiment - 6 Sessions of 10min digital coworking with role rotation (right now 30 for debugging)
"""


class Applicant:
    def __init__(self, applicant_id, name, description):
        self.id = applicant_id
        self.name = name
        self.description = description

    def get_documents(self):
        return {
            'cv': f'applicants_{self.id}/cv_{self.id}.pdf',
            'job_reference': f'applicants_{self.id}/job_reference_{self.id}.pdf',
            'cover_letter': f'applicants_{self.id}/cover_letter_{self.id}.pdf'
        }

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'documents': self.get_documents()
        }


def create_applicants():
    applicants = []
    applicant_a = Applicant('a', 'Applicant A', 'Recruiter Mask')
    applicant_b = Applicant('b', 'Applicant B', 'Recruiter Mask')
    applicant_c = Applicant('c', 'Applicant C', 'Recruiter Mask')
    applicants.extend([applicant_a, applicant_b, applicant_c])
    return applicants


def get_applicants_data():
    applicant_objects = create_applicants()
    return [applicant.to_dict() for applicant in applicant_objects]


def load_metadata_criteria():
    try:
        metadata_path = [
            '_static/applicants/metadata1.xlsx',
        ]

        df = None
        file_path = None

        for path in metadata_path:
            if os.path.exists(path):
                file_path = path
                break

        if not file_path:
            raise FileNotFoundError("metadata1.xlsx not found")

        # Read the Excel file
        df = pd.read_excel(file_path, header=1)  # Header in row 2 (index 1)

        criteria_data = []
        categories = []

        for index, row in df.iterrows():
            # Check different possible column names
            name_value = None
            category_value = None

            # Try different column name variations
            for col in df.columns:
                col_lower = str(col).lower()
                if 'requirement_name' in col_lower or 'name' in col_lower:
                    name_value = row.get(col)
                elif 'requirement_category' in col_lower or 'category' in col_lower:
                    category_value = row.get(col)

            if pd.notna(name_value) and str(name_value).strip():
                criterion = {
                    'name': str(name_value).strip(),
                    'category': str(category_value).strip() if pd.notna(category_value) else 'general',
                }
                criteria_data.append(criterion)

                # Collect unique categories
                if criterion['category'] not in categories:
                    categories.append(criterion['category'])

        # Group criteria by category
        criteria_by_category = {}
        for category in categories:
            criteria_by_category[category] = [
                c for c in criteria_data if c['category'] == category
            ]

        return {
            'criteria': criteria_data,
            'categories': categories,
            'criteria_by_category': criteria_by_category
        }

    except Exception as e:
        # If there's any error, return empty structure
        return {
            'criteria': [],
            'categories': [],
            'criteria_by_category': {}
        }


class C(BaseConstants):
    NAME_IN_URL = 'mental_fatigue'
    PLAYERS_PER_GROUP = 3
    NUM_ROUNDS = 6

    # Timing
    SESSION_DURATION_MINUTES = 30
    SESSION_DURATION_SECONDS = SESSION_DURATION_MINUTES * 60

    # Data for templates
    APPLICANTS = get_applicants_data()

    # Load metadata criteria
    METADATA = load_metadata_criteria()
    CRITERIA_DATA = METADATA['criteria']
    CATEGORIES = METADATA['categories']
    CRITERIA_BY_CATEGORY = METADATA['criteria_by_category']

    # Evaluation settings
    MIN_SCORE = 0
    MAX_SCORE = 8
    RELEVANCE_FACTORS = {'low': 1, 'normal': 2, 'high': 3}

    # Cognitive Load Test settings
    COGNITIVE_TEST_DURATION = 30
    STROOP_WORDS = ['red', 'blue', 'green', 'yellow']
    STROOP_COLORS = ['#ff0000', '#0000ff', '#00ff00', '#ffff00']

    # Role constants
    RECRUITER_ROLE = 'Recruiter'
    HR_COORDINATOR_ROLE = 'HR-Coordinator'
    BUSINESS_PARTNER_ROLE = 'Business-Partner'


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    # Role selection for each round
    selected_role = models.StringField(
        choices=[
            [C.RECRUITER_ROLE, 'Recruiter'],
            [C.HR_COORDINATOR_ROLE, 'HR-Coordinator'],
            [C.BUSINESS_PARTNER_ROLE, 'Business-Partner']
        ],
        initial='',
        doc="Selected role for this session"
    )

    # Session performance tracking
    criteria_added_this_session = models.IntegerField(
        blank=True,
        doc="Number of criteria added by this player in current session"
    )

    # Self-assessment after each session
    fatigue_level = models.IntegerField(
        min=1, max=10,
        blank=True,
        doc="Self-reported fatigue level (1=not tired, 10=extremely tired)"
    )

    mental_effort = models.IntegerField(
        min=1, max=10,
        blank=True,
        doc="Self-reported mental effort required (1=very low, 10=very high)"
    )

    concentration_difficulty = models.IntegerField(
        min=1, max=10,
        blank=True,
        doc="Difficulty concentrating (1=very easy, 10=very difficult)"
    )

    motivation_level = models.IntegerField(
        min=1, max=10,
        blank=True,
        doc="Current motivation level (1=very low, 10=very high)"
    )

    # Cognitive Load Test Results
    cognitive_test_score = models.IntegerField(
        blank=True,
        doc="Score on cognitive load test (correct answers)"
    )

    cognitive_test_reaction_time = models.FloatField(
        blank=True,
        doc="Average reaction time in cognitive test (milliseconds)"
    )

    cognitive_test_errors = models.IntegerField(
        blank=True,
        doc="Number of errors in cognitive test"
    )

    # Methods for cleaner templates and logic
    def is_recruiter(self):
        return self.selected_role == C.RECRUITER_ROLE

    def is_hr_coordinator(self):
        return self.selected_role == C.HR_COORDINATOR_ROLE

    def is_business_partner(self):
        return self.selected_role == C.BUSINESS_PARTNER_ROLE

    def add_reaction_time(self, action_type, reaction_time_ms):
        try:
            times = json.loads(self.reaction_times) if self.reaction_times else []
        except json.JSONDecodeError:
            times = []

        times.append({
            'action': action_type,
            'reaction_time_ms': reaction_time_ms,
            'round': self.round_number
        })

        self.reaction_times = json.dumps(times)

    def get_cumulative_fatigue_trend(self):
        fatigue_data = []
        for round_num in range(1, self.round_number + 1):
            try:
                round_player = self.in_round(round_num)
                fatigue_data.append({
                    'round': round_num,
                    'fatigue': round_player.fatigue_level,
                    'mental_effort': round_player.mental_effort,
                    'concentration': round_player.concentration_difficulty,
                    'motivation': round_player.motivation_level,
                    'cognitive_score': round_player.cognitive_test_score,
                    'cognitive_rt': round_player.cognitive_test_reaction_time
                })
            except:
                continue
        return fatigue_data


# Utility function for role assignment
def ensure_all_roles_assigned(group):
    """Ensure all three roles are assigned to players"""
    selected_roles = [p.selected_role for p in group.get_players()]
    required_roles = [C.RECRUITER_ROLE, C.HR_COORDINATOR_ROLE, C.BUSINESS_PARTNER_ROLE]

    missing_roles = [role for role in required_roles if role not in selected_roles]
    unassigned_players = [p for p in group.get_players() if not p.selected_role]

    for i, player in enumerate(unassigned_players):
        if i < len(missing_roles):
            player.selected_role = missing_roles[i]
