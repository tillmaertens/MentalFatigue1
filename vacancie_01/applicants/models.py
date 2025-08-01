from otree.api import *
import json
import pandas as pd
import os

doc = """
Mental Fatigue Experiment - 6 Sessions of 10min digital coworking with role rotation (right now 30 for debugging)
"""


class Applicant:
    def __init__(self, applicant_id, name, description, doc_suffix=''):
        self.id = applicant_id
        self.name = name
        self.description = description
        self.doc_suffix = doc_suffix

    def get_documents(self):
        return {
            'cv': f'applicants_{self.id}/cv_{self.id}{self.doc_suffix}.pdf',
            'job_reference': f'applicants_{self.id}/job_reference_{self.id}{self.doc_suffix}.pdf',
            'cover_letter': f'applicants_{self.id}/cover_letter_{self.id}{self.doc_suffix}.pdf'
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


def load_metadata_criteria(round_number=None, player=None):
    try:
        # Determine which metadata files to use based on vacancy
        if round_number and player:
            vacancy_info = get_vacancy_info(round_number, player)
            if vacancy_info:
                metadata_paths = vacancy_info['metadata_files']
            else:
                metadata_paths = ['_static/applicants/metadata1.xlsx', '_static/applicants/metadatanew.xlsx']
        else:
            metadata_paths = ['_static/applicants/metadata1.xlsx']

        df = None
        file_path = None

        for path in metadata_paths:
            if os.path.exists(path):
                file_path = path
                break

        if not file_path:
            raise FileNotFoundError("metadata Excel file not found")

        df = pd.read_excel(file_path, header=1)

        criteria_data = []
        categories = []

        for index, row in df.iterrows():
            name_value = row.get('requirement_name')
            category_value = row.get('requirement_category')
            relevance_value = row.get('requirement_relevance')

            # Scores für die drei Applicants
            applicant_a_score = row.get('applicant_a_points')
            applicant_b_score = row.get('applicant_b_points')
            applicant_c_score = row.get('applicant_c_points')

            if pd.notna(name_value) and str(name_value).strip():
                criterion = {
                    'name': str(name_value).strip(),
                    'category': str(category_value).strip() if pd.notna(category_value) else 'general',
                    'relevance': str(relevance_value).strip() if pd.notna(relevance_value) else 'normal',
                    'scores': {
                        'applicant_a': int(applicant_a_score) if pd.notna(applicant_a_score) else 0,
                        'applicant_b': int(applicant_b_score) if pd.notna(applicant_b_score) else 0,
                        'applicant_c': int(applicant_c_score) if pd.notna(applicant_c_score) else 0,
                    }
                }

                # Requirement_point_is_X fields for Business Partner
                for points in range(9):  # 0-8
                    point_field = f'requirement_point_is_{points}'
                    point_value = row.get(point_field)
                    if pd.notna(point_value):
                        criterion[point_field] = str(point_value).strip()

                criteria_data.append(criterion)

                if criterion['category'] not in categories:
                    categories.append(criterion['category'])

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
        return {
            'criteria': [],
            'categories': [],
            'criteria_by_category': {}
        }


def get_vacancy_info(round_number, player):
    """Returns current vacancy configuration based on round - fixed order: vacancy 1 then vacancy 2"""
    from . import models  # Import to avoid circular import

    if models.C.VACANCY_1_START_ROUND <= round_number <= models.C.VACANCY_1_END_ROUND:

        return get_vacancy_config(1)

    elif models.C.VACANCY_2_START_ROUND <= round_number <= models.C.VACANCY_2_END_ROUND:

        return get_vacancy_config(2)

    else:

        return None


def get_vacancy_config(vacancy_number):
    """Returns configuration for specific vacancy number"""
    if vacancy_number == 1:
        job_desc_file = 'job_description_1.pdf'
    else:
        job_desc_file = 'job_description_2.pdf'

    return {
        'vacancy': vacancy_number,
        'duration_seconds': 30 * 60 if vacancy_number == 1 else 10 * 60,
        'metadata_files': [f'_static/applicants/metadata{vacancy_number}.xlsx'],
        'doc_suffix': str(vacancy_number),
        'job_desc_file': job_desc_file
    }


def get_applicants_data_for_vacancy(vacancy_info=None):
    """Returns applicant data with appropriate document suffixes"""
    applicants = []
    doc_suffix = vacancy_info['doc_suffix'] if vacancy_info else '1'  # Default to '1'

    applicant_a = Applicant('a', 'Applicant A', 'Recruiter Mask', doc_suffix)
    applicant_b = Applicant('b', 'Applicant B', 'Recruiter Mask', doc_suffix)
    applicant_c = Applicant('c', 'Applicant C', 'Recruiter Mask', doc_suffix)
    applicants.extend([applicant_a, applicant_b, applicant_c])
    return [applicant.to_dict() for applicant in applicants]


def get_applicant_ids():
    """Returns dynamic list of applicant IDs"""
    applicants = get_applicants_data_for_vacancy()
    return [applicant['id'] for applicant in applicants]


def should_show_vacancy_session(round_number):
    """Utility function to determine if vacancy session should be shown"""
    from . import models  # Import to avoid circular import

    if models.C.VACANCY_1_START_ROUND <= round_number <= models.C.VACANCY_1_END_ROUND:
        return True
    elif models.C.VACANCY_2_START_ROUND <= round_number <= models.C.VACANCY_2_END_ROUND:
        return True  # Will check continue_to_second_vacancy in pages that need it
    return False


def get_static_file_path(filename):
    """Returns full path for static applicant files"""
    from . import models
    return models.C.STATIC_APPLICANTS_PATH + filename


# Utility function for role assignment
def ensure_all_roles_assigned(group):
    """Ensure all three roles are assigned to players"""
    from . import models
    selected_roles = [p.selected_role for p in group.get_players()]
    required_roles = [models.C.RECRUITER_ROLE, models.C.HR_COORDINATOR_ROLE, models.C.BUSINESS_PARTNER_ROLE]

    missing_roles = [role for role in required_roles if role not in selected_roles]
    unassigned_players = [p for p in group.get_players() if not p.selected_role]

    for i, player in enumerate(unassigned_players):
        if i < len(missing_roles):
            player.selected_role = missing_roles[i]


def assign_rotating_role(player):
    """Automatically assign rotating role based on player ID and round number"""
    roles = [C.RECRUITER_ROLE, C.HR_COORDINATOR_ROLE, C.BUSINESS_PARTNER_ROLE]

    # Calculate role index: rotates every round for each player
    role_index = (player.id_in_group - 1 + player.round_number - 1) % 3
    player.selected_role = roles[role_index]

    return player.selected_role

class C(BaseConstants):
    NAME_IN_URL = 'mental_fatigue'
    PLAYERS_PER_GROUP = 3
    NUM_ROUNDS = 14

    # Vacancy configurations
    VACANCY_1_DURATION_MINUTES = 30  # 30 minutes for vacancy 1
    VACANCY_2_DURATION_MINUTES = 10  # 10 minutes for vacancy 2
    VACANCY_1_DURATION_SECONDS = VACANCY_1_DURATION_MINUTES * 60
    VACANCY_2_DURATION_SECONDS = VACANCY_2_DURATION_MINUTES * 60

    VACANCY_1_START_ROUND = 1
    VACANCY_1_END_ROUND = 6
    VACANCY_1_RESULTS_ROUND = 7
    VACANCY_2_START_ROUND = 8
    VACANCY_2_END_ROUND = 13
    FINAL_RESULTS_ROUND = 14

    # Data for templates
    APPLICANTS = get_applicants_data_for_vacancy()

    # Load metadata criteria (default to vacancy 1)
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

    # File paths
    STATIC_APPLICANTS_PATH = '/static/applicants/'

    # Applicant colors for charts
    APPLICANT_COLORS = {
        'a': '#FF6384',
        'b': '#36A2EB',
        'c': '#FFCE56'
    }

    # Sessions per vacancy
    SESSIONS_PER_VACANCY = 6


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

    validation_data_json = models.LongStringField(
        blank=True,
        doc="JSON string containing criteria data for validation (hidden from admin)"
    )

    criteria_correct_this_session = models.IntegerField(
        blank=True,
        doc="Number of criteria correctly entered (scores and relevance match metadata)"
    )

    criteria_incorrect_this_session = models.IntegerField(
        blank=True,
        doc="Number of criteria incorrectly entered (scores or relevance don't match metadata)"
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

    def validate_criteria_data(self, criteria_data):
        """
        Validates criteria data against metadata and updates correct/incorrect counters
        criteria_data: dict with format {criterion_name: {scores: {a: score, b: score, c: score}, relevance: 'low/normal/high'}}
        """
        correct_count = 0
        incorrect_count = 0

        # Load current vacancy metadata
        metadata = load_metadata_criteria(self.round_number, self)

        for criterion_name, data in criteria_data.items():

            criterion_metadata = None
            for criterion in metadata['criteria']:
                if criterion['name'].strip().lower() == criterion_name.strip().lower():
                    criterion_metadata = criterion
                    break

            if criterion_metadata:
                # Prüfe Scores und Relevanz
                scores_correct = True
                relevance_correct = True

                # Prüfe Scores für jeden Applicant
                for applicant_id in get_applicant_ids():
                    entered_score = data['scores'].get(applicant_id, 0)
                    correct_score = criterion_metadata['scores'].get(f'applicant_{applicant_id}', 0)

                    if int(entered_score) != int(correct_score):
                        scores_correct = False
                        break

                # Prüfe Relevanz
                entered_relevance = data.get('relevance', 'normal')
                correct_relevance = criterion_metadata.get('relevance', 'normal')

                if entered_relevance != correct_relevance:
                    relevance_correct = False

                # Zähle richtig oder falsch
                if scores_correct and relevance_correct:
                    correct_count += 1
                else:
                    incorrect_count += 1

        # Update die Felder
        self.criteria_correct_this_session = correct_count
        self.criteria_incorrect_this_session = incorrect_count

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
