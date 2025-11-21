from otree.api import *
import pandas as pd
import os

doc = """
Mental Fatigue Experiment: 8 rounds: Baseline + 6 Vacancies + Final Results
"""


class Applicant:
    """
    Data container for applicant information and document management.
    Handles dynamic document path generation for different vacancy periods.
    """

    def __init__(self, applicant_id, name, description, doc_suffix=''):
        """
        Initialize applicant with basic information.

        Args:
        applicant_id (str): Unique identifier ('a', 'b', 'c')
        name (str): Display name (e.g., 'Applicant A')
        description (str): Role description or placeholder text
        doc_suffix (str): Vacancy-specific suffix ('1' or '2', defaults to '')
        """
        self.id = applicant_id
        self.name = name
        self.description = description
        self.doc_suffix = doc_suffix

    def get_documents(self):
        """
        Generates file paths for applicant documents based on current vacancy.
        Returns:
        dict: Document paths with keys 'cv', 'job_reference', 'cover_letter'
        """
        return {
            'cv': f'applicants_{self.id}/cv_{self.id}{self.doc_suffix}.pdf',
            'job_reference': f'applicants_{self.id}/job_reference_{self.id}{self.doc_suffix}.pdf',
            'cover_letter': f'applicants_{self.id}/cover_letter_{self.id}{self.doc_suffix}.pdf'
        }

    def to_dict(self):
        """
        Converts applicant object to dictionary format for template usage.
        Combines basic applicant data with document paths for easy access in oTree templates and JavaScript code.

        Returns:
        dict: Complete applicant data including documents
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'documents': self.get_documents()
        }


def load_metadata_criteria(round_number=None, player=None):
    """
    Loads evaluation criteria from Excel metadata files for current vacancy.

    Returns:
    dict: Organized criteria data containing:
        - criteria: List of all criteria with scores and metadata
        - predefined_criteria: List of criteria that should be pre-loaded in HR interface
        - categories: List of unique category names
        - criteria_by_category: Dictionary grouping criteria by category
    """
    try:
        # Determine which metadata files to use based on vacancy
        if round_number and player:
            vacancy_info = get_vacancy_info(round_number, player)
            if vacancy_info:
                metadata_paths = vacancy_info['metadata_files']
            else:
                # Fallback to all three files if vacancy info not available
                metadata_paths = ['_static/applicants/metadata1.xlsx', '_static/applicants/metadatanew.xlsx']

        # Find first existing metadata file from the paths list
        file_path = None
        for path in metadata_paths:
            if os.path.exists(path):
                file_path = path
                break

        if not file_path:
            raise FileNotFoundError("metadata Excel file not found")

        # Load Excel file with pandas (header=1 means second row contains headers)
        df = pd.read_excel(file_path, header=1)

        criteria_data = []  # List of all criteria objects
        predefined_criteria = []  # List of predefined criteria for auto-loading
        categories = []  # List of unique category names

        for index, row in df.iterrows():
            name_value = row.get('requirement_name')
            category_value = row.get('requirement_category')
            relevance_value = row.get('requirement_relevance')
            need_defined_by = row.get('requirement_need_defined_by')  # Check for predefined criteria

            applicant_a_score = row.get('applicant_a_points')
            applicant_b_score = row.get('applicant_b_points')
            applicant_c_score = row.get('applicant_c_points')

            # Only process rows with valid criterion names
            if pd.notna(name_value) and str(name_value).strip():
                # Build criterion object with all metadata
                criterion = {
                    'name': str(name_value).strip(),
                    'category': str(category_value).strip() if pd.notna(category_value) else 'general',
                    'relevance': str(relevance_value).strip() if pd.notna(relevance_value) else 'normal',
                    'need_defined_by': str(need_defined_by).strip() if pd.notna(need_defined_by) else 'tender',
                    'scores': {
                        'applicant_a': int(applicant_a_score) if pd.notna(applicant_a_score) else 0,
                        'applicant_b': int(applicant_b_score) if pd.notna(applicant_b_score) else 0,
                        'applicant_c': int(applicant_c_score) if pd.notna(applicant_c_score) else 0,
                    }
                }

                # Add Business Partner point descriptions
                for points in range(9):  # 0-8
                    point_field = f'requirement_point_is_{points}'
                    point_value = row.get(point_field)
                    if pd.notna(point_value):
                        criterion[point_field] = str(point_value).strip()

                # Add criterion to main list
                criteria_data.append(criterion)

                # Check if this criterion should be predefined in HR interface
                if need_defined_by and str(need_defined_by).strip().lower() == 'predefined':
                    predefined_criteria.append(criterion)

                if criterion['category'] not in categories:
                    categories.append(criterion['category'])

        # Organize criteria by category for template dropdown menus
        criteria_by_category = {}
        for category in categories:
            criteria_by_category[category] = [
                c for c in criteria_data if c['category'] == category
            ]

        return {
            'criteria': criteria_data,
            'predefined_criteria': predefined_criteria,
            'categories': categories,
            'criteria_by_category': criteria_by_category
        }

    except Exception as e:
        return {
            'criteria': [],
            'predefined_criteria': [],
            'categories': [],
            'criteria_by_category': {}
        }


def get_vacancy_info(round_number, player):
    """
    Maps round numbers to vacancy periods for the 5-round structure.

    Args:
    round_number (int): Current round number (1-5)
    player (Player): Player object (not used but kept for consistency)

    Returns:
    dict: Vacancy configuration from get_vacancy_config(), or None if baseline/results rounds
    """
    from . import models  # Import to avoid circular import

    if round_number == models.C.VACANCY_1_ROUND:
        return get_vacancy_config(1)
    elif round_number == models.C.VACANCY_2_ROUND:
        return get_vacancy_config(2)
    elif round_number == models.C.VACANCY_3_ROUND:
        return get_vacancy_config(3)
    elif round_number == models.C.VACANCY_4_ROUND:
        return get_vacancy_config(4)
    elif round_number == models.C.VACANCY_5_ROUND:
        return get_vacancy_config(5)
    elif round_number == models.C.VACANCY_6_ROUND:
        return get_vacancy_config(6)
    else:
        return None


def get_vacancy_config(vacancy_number):
    """
    Provides vacancy-specific settings with unlimited time for Vacancy 1.

    Args:
        vacancy_number (int): Vacancy identifier (1-6)

    Returns:
        dict: Vacancy configuration containing:
            - vacancy: Vacancy number (1-6)
            - duration_seconds: None for vacancy 1 (unlimited), 720s (12 minutes) for vacancies 2-6
            - metadata_files: List with Excel metadata file path
            - doc_suffix: String suffix for document versioning ('1' to '6')
            - job_desc_file: PDF filename for job description
    """
    if vacancy_number == 1:
        job_desc_file = 'job_description_1.pdf'
    elif vacancy_number == 2:
        job_desc_file = 'job_description_2.pdf'
    elif vacancy_number == 3:
        job_desc_file = 'job_description_3.pdf'
    elif vacancy_number == 4:
        job_desc_file = 'job_description_4.pdf'
    elif vacancy_number == 5:
        job_desc_file = 'job_description_5.pdf'
    else:  # vacancy_number == 6
        job_desc_file = 'job_description_6.pdf'

    return {
        'vacancy': vacancy_number,
        'duration_seconds': None if vacancy_number == 1 else 12 * 60,  # Unlimited for V1, 12min for V2, V3
        'metadata_files': [f'_static/applicants/metadata{vacancy_number}.xlsx'],
        'doc_suffix': str(vacancy_number),
        'job_desc_file': job_desc_file
    }


def get_applicants_data_for_vacancy(vacancy_info=None):
    """
    Creates applicant objects with appropriate document suffixes for current vacancy.

    Args:
    vacancy_info (dict, optional): Vacancy configuration from get_vacancy_config().
                                If None, defaults to vacancy 1 documents.

    Returns:
    list: List of applicant dictionaries ready for template usage, each containing:
        - id: Applicant identifier ('a', 'b', 'c')
        - name: Display name ('Applicant A', 'Applicant B', 'Applicant C')
        - description: Role description placeholder
        - documents: Dictionary with CV, job reference, and cover letter paths
    """
    applicants = []

    # Extract document suffix from vacancy info, default to '1' for vacancy 1
    doc_suffix = vacancy_info['doc_suffix'] if vacancy_info else '1'

    # Create three standard applicants with vacancy-specific document suffixes
    applicant_a = Applicant('a', 'Applicant A', 'Recruiter Mask', doc_suffix)
    applicant_b = Applicant('b', 'Applicant B', 'Recruiter Mask', doc_suffix)
    applicant_c = Applicant('c', 'Applicant C', 'Recruiter Mask', doc_suffix)

    # Add all applicants to list
    applicants.extend([applicant_a, applicant_b, applicant_c])

    # Convert applicant objects to dictionaries for template usage
    return [applicant.to_dict() for applicant in applicants]


def get_applicant_ids():
    """
    Provides consistent applicant IDs used throughout the application
    for form validation, score checking, and template loops.

    Returns:
    list: Applicant IDs ['a', 'b', 'c']
    """
    applicants = get_applicants_data_for_vacancy()
    return [applicant['id'] for applicant in applicants]


def should_show_vacancy_session(round_number):
    """
    Determines if current round should display vacancy task sessions.

    Args:
        round_number (int): Current round number to check (1-8)

    Returns:
        bool: True if round is a vacancy session (rounds 2-7), False otherwise
    """
    from . import models  # Import to avoid circular import

    return round_number in [models.C.VACANCY_1_ROUND, models.C.VACANCY_2_ROUND, models.C.VACANCY_3_ROUND,
                            models.C.VACANCY_4_ROUND, models.C.VACANCY_5_ROUND, models.C.VACANCY_6_ROUND]


def assign_static_role(player):
    """
    Assigns static roles per player based on player ID.

    Each player keeps the same role across all six vacancies:
    - Player 1: Always Recruiter
    - Player 2: Always HR-Coordinator
    - Player 3: Always Business-Partner

    Args:
    player (Player): Player object to assign role to

    Returns:
    str: Assigned role name, or existing role if already set
    """

    # This prevents overwriting historical player data when accessing in_round()
    if not player.selected_role:
        roles = [C.RECRUITER_ROLE, C.HR_COORDINATOR_ROLE, C.BUSINESS_PARTNER_ROLE]

        # Static role assignment based on player ID (no rotation)
        role_index = (player.id_in_group - 1) % 3
        player.selected_role = roles[role_index]

    return player.selected_role


class C(BaseConstants):
    """
    oTree experiment configuration
    """

    NAME_IN_URL = 'mental_fatigue'
    PLAYERS_PER_GROUP = 3
    NUM_ROUNDS = 8

    # 8-round structure definition
    CONSENT_ROUND = 1
    VACANCY_1_ROUND = 2
    VACANCY_2_ROUND = 3
    VACANCY_3_ROUND = 4
    VACANCY_4_ROUND = 5
    VACANCY_5_ROUND = 6
    VACANCY_6_ROUND = 7
    FINAL_RESULTS_ROUND = 8

    VACANCY_2_DURATION_MINUTES = 12
    VACANCY_2_DURATION_SECONDS = VACANCY_2_DURATION_MINUTES * 60

    VACANCY_3_DURATION_MINUTES = 12
    VACANCY_3_DURATION_SECONDS = VACANCY_3_DURATION_MINUTES * 60

    VACANCY_4_DURATION_MINUTES = 12
    VACANCY_4_DURATION_SECONDS = VACANCY_4_DURATION_MINUTES * 60

    VACANCY_5_DURATION_MINUTES = 12
    VACANCY_5_DURATION_SECONDS = VACANCY_5_DURATION_MINUTES * 60

    VACANCY_6_DURATION_MINUTES = 12
    VACANCY_6_DURATION_SECONDS = VACANCY_6_DURATION_MINUTES * 60

    # Data for templates
    APPLICANTS = get_applicants_data_for_vacancy()
    METADATA = load_metadata_criteria()
    CRITERIA_DATA = METADATA['criteria']
    CATEGORIES = METADATA['categories']
    CRITERIA_BY_CATEGORY = METADATA['criteria_by_category']

    # Evaluation settings
    MIN_SCORE = 0
    MAX_SCORE = 8
    RELEVANCE_FACTORS = {'low': 1, 'normal': 2, 'high': 3}

    # Cognitive Load Test settings
    COGNITIVE_TEST_DURATION = 22
    COGNITIVE_TEST_TOTAL_QUESTIONS = 20
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

    # Sessions configurations
    SESSIONS_PER_VACANCY = 1

    # Debug mode activated if set to True: No Video Meeting
    DEBUG_MODE = False


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    """
    Stores role assignments, performance metrics, self-assessments, and cognitive test results
    for each player across all rounds in the 8-round structure.
    """
    # Role assignment
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
        doc="JSON string containing criteria data for validation"
    )

    criteria_correct_this_session = models.IntegerField(
        blank=True,
        doc="Number of criteria correctly entered"
    )

    criteria_incorrect_this_session = models.IntegerField(
        blank=True,
        doc="Number of criteria incorrectly entered"
    )

    # Post-Task Self-Assessment (0-100 scale)
    fatigue_level = models.IntegerField(
        min=0, max=100,
        blank=True,
        doc="Self-reported fatigue level (0=not tired, 100=extremely tired)"
    )

    mental_effort = models.IntegerField(
        min=0, max=100,
        blank=True,
        doc="Self-reported mental effort required (0=very low, 100=very high)"
    )

    concentration_difficulty = models.IntegerField(
        min=0, max=100,
        blank=True,
        doc="Difficulty concentrating (0=very easy, 100=very difficult)"
    )

    motivation_level = models.IntegerField(
        min=0, max=100,
        blank=True,
        doc="Current motivation level (0=very low, 100=very high)"
    )

    # Baseline-specific measures (0-100 scale)
    baseline_mfi_wander = models.IntegerField(
        min=0, max=100,
        blank=True,
        doc="Baseline: My thoughts easily wander (0=not at all, 100=extremely)"
    )

    baseline_mfi_concentration = models.IntegerField(
        min=0, max=100,
        blank=True,
        doc="Baseline: Effort to concentrate (0=not at all, 100=extremely)"
    )

    baseline_zfe_dread = models.IntegerField(
        min=0, max=100,
        blank=True,
        doc="Baseline: Dread doing things (0=not at all, 100=extremely)"
    )

    baseline_kss_alertness = models.IntegerField(
        min=0, max=100,
        blank=True,
        doc="Baseline: Alertness level (0=extremely alert, 100=extremely sleepy)"
    )

    baseline_motivation = models.IntegerField(
        min=0, max=100,
        blank=True,
        doc="Baseline: Motivation for upcoming tasks (0=not motivated, 100=extremely motivated)"
    )

    baseline_afi_follow = models.IntegerField(
        min=0, max=100,
        blank=True,
        doc="Baseline: Ability to follow through on plans (0=not at all, 100=extremely well)"
    )

    # Effort-Cost measure
    effort_cost_worth = models.IntegerField(
        min=0, max=100,
        blank=True,
        doc="Task felt worth the mental energy (0=not worth it, 100=definitely worth it)"
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

    # Methods
    def is_recruiter(self):
        return self.selected_role == C.RECRUITER_ROLE

    def is_hr_coordinator(self):
        return self.selected_role == C.HR_COORDINATOR_ROLE

    def is_business_partner(self):
        return self.selected_role == C.BUSINESS_PARTNER_ROLE

    def validate_criteria_data(self, criteria_data):
        """
        Validates criteria data against metadata and updates correct/incorrect counters
        """
        correct_count = 0
        incorrect_count = 0

        # Load correct answers from metadata for current vacancy
        metadata = load_metadata_criteria(self.round_number, self)

        # Check each criterion the player evaluated
        for criterion_name, data in criteria_data.items():
            # Find correct answers for this criterion
            criterion_metadata = None
            for criterion in metadata['criteria']:
                if criterion['name'].strip().lower() == criterion_name.strip().lower():
                    criterion_metadata = criterion
                    break

            if criterion_metadata:
                # Validate scores and relevance against correct answers
                scores_correct = True
                relevance_correct = True

                # Check scores for each applicant
                for applicant_id in get_applicant_ids():
                    entered_score = data['scores'].get(applicant_id, 0)
                    correct_score = criterion_metadata['scores'].get(f'applicant_{applicant_id}', 0)

                    if int(entered_score) != int(correct_score):
                        scores_correct = False
                        break

                # Check relevance level
                entered_relevance = data.get('relevance', 'normal')
                correct_relevance = criterion_metadata.get('relevance', 'normal')

                if entered_relevance != correct_relevance:
                    relevance_correct = False

                if scores_correct and relevance_correct:
                    correct_count += 1
                else:
                    incorrect_count += 1

        # Update player's performance counters
        self.criteria_correct_this_session = correct_count
        self.criteria_incorrect_this_session = incorrect_count
