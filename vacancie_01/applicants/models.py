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
    applicant_a = Applicant('a', 'Applicant A', 'Placeholder Recruiter Mask')
    applicant_b = Applicant('b', 'Applicant B', 'Placeholder Recruiter Mask')
    applicant_c = Applicant('c', 'Applicant C', 'Placeholder Recruiter Mask')
    applicants.extend([applicant_a, applicant_b, applicant_c])
    return applicants


def get_applicants_data():
    applicant_objects = create_applicants()
    return [applicant.to_dict() for applicant in applicant_objects]


def load_metadata_criteria():
    """Load criteria from metadata Excel file"""
    try:
        # Try different possible paths for the Excel file
        possible_paths = [
            '_static/applicants/metadata1.xlsx',
        ]

        df = None
        file_path = None

        for path in possible_paths:
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

    # Role constants - prevents typos and makes templates cleaner
    RECRUITER_ROLE = 'Recruiter'
    HR_COORDINATOR_ROLE = 'HR-Coordinator'
    BUSINESS_PARTNER_ROLE = 'Business-Partner'


class Subsession(BaseSubsession):
    def creating_session(subsession):
        """Initialize session data"""
        # Store session start time for each round
        for group in subsession.get_groups():
            group.session_start_time = time.time()


class Group(BaseGroup):
    # Session timing
    session_start_time = models.FloatField(
        doc="Unix timestamp when this session started"
    )

    session_end_time = models.FloatField(
        initial=0.0,
        doc="Unix timestamp when this session ended"
    )

    # Evaluation data for this session
    evaluation_data = models.LongStringField(
        initial='{}',
        doc="JSON containing evaluation criteria and scores for this session"
    )

    # Performance metrics for this session
    total_criteria_added = models.IntegerField(
        initial=0,
        doc="Total number of criteria added by group in this session"
    )

    total_scores_entered = models.IntegerField(
        initial=0,
        doc="Total number of scores entered by group in this session"
    )

    session_completion_rate = models.FloatField(
        initial=0.0,
        doc="Percentage of evaluation completed in this session"
    )

    def get_evaluation_data(self):
        try:
            return json.loads(self.evaluation_data) if self.evaluation_data else {}
        except json.JSONDecodeError:
            return {}

    def set_evaluation_data(self, data_dict):
        self.evaluation_data = json.dumps(data_dict)

    def calculate_session_metrics(self):
        """Calculate performance metrics for this session"""
        evaluation = self.get_evaluation_data()

        self.total_criteria_added = len(evaluation)

        total_possible_scores = len(evaluation) * 3
        filled_scores = 0

        for criterion_data in evaluation.values():
            scores = criterion_data.get('scores', {})
            filled_scores += len([s for s in scores.values() if s])

        self.session_completion_rate = (filled_scores / total_possible_scores * 100) if total_possible_scores > 0 else 0


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
        initial=0,
        doc="Number of criteria added by this player in current session"
    )

    scores_entered_this_session = models.IntegerField(
        initial=0,
        doc="Number of scores entered by this player in current session"
    )

    clicks_this_session = models.IntegerField(
        initial=0,
        doc="Number of clicks made by this player in current session"
    )

    # Timing data
    session_start_timestamp = models.FloatField(
        initial=0.0,
        doc="When this player started the session"
    )

    session_end_timestamp = models.FloatField(
        initial=0.0,
        doc="When this player finished the session"
    )

    # Reaction time data (JSON array of measurements)
    reaction_times = models.LongStringField(
        initial='[]',
        doc="JSON array of reaction times for various actions"
    )

    # Mouse movement data (for later analysis)
    mouse_movements = models.LongStringField(
        initial='[]',
        doc="JSON array of mouse movement data"
    )

    # Self-assessment after each session
    fatigue_level = models.IntegerField(
        min=1, max=10,
        initial=1,
        doc="Self-reported fatigue level (1=not tired, 10=extremely tired)"
    )

    mental_effort = models.IntegerField(
        min=1, max=10,
        initial=1,
        doc="Self-reported mental effort required (1=very low, 10=very high)"
    )

    concentration_difficulty = models.IntegerField(
        min=1, max=10,
        initial=1,
        doc="Difficulty concentrating (1=very easy, 10=very difficult)"
    )

    motivation_level = models.IntegerField(
        min=1, max=10,
        initial=5,
        doc="Current motivation level (1=very low, 10=very high)"
    )

    # Cognitive Load Test Results
    cognitive_test_score = models.IntegerField(
        initial=0,
        doc="Score on cognitive load test (correct answers)"
    )

    cognitive_test_reaction_time = models.FloatField(
        initial=0.0,
        doc="Average reaction time in cognitive test (milliseconds)"
    )

    cognitive_test_errors = models.IntegerField(
        initial=0,
        doc="Number of errors in cognitive test"
    )

    # Physiological data placeholders (for future lab integration)
    eeg_data_file = models.StringField(
        initial='',
        doc="Filename of EEG data for this session (for lab experiments)"
    )

    eye_tracking_data_file = models.StringField(
        initial='',
        doc="Filename of eye tracking data for this session (for lab experiments)"
    )

    heart_rate_data = models.LongStringField(
        initial='[]',
        doc="JSON array of heart rate measurements (if available)"
    )

    # Helper methods for cleaner templates and logic
    def is_recruiter(self):
        return self.selected_role == C.RECRUITER_ROLE

    def is_hr_coordinator(self):
        return self.selected_role == C.HR_COORDINATOR_ROLE

    def is_business_partner(self):
        return self.selected_role == C.BUSINESS_PARTNER_ROLE

    def add_reaction_time(self, action_type, reaction_time_ms):
        """Add a reaction time measurement"""
        try:
            times = json.loads(self.reaction_times) if self.reaction_times else []
        except json.JSONDecodeError:
            times = []

        times.append({
            'timestamp': time.time(),
            'action': action_type,
            'reaction_time_ms': reaction_time_ms,
            'round': self.round_number
        })

        self.reaction_times = json.dumps(times)

    def add_mouse_movement(self, x, y, event_type):
        """Add mouse movement data"""
        try:
            movements = json.loads(self.mouse_movements) if self.mouse_movements else []
        except json.JSONDecodeError:
            movements = []

        movements.append({
            'timestamp': time.time(),
            'x': x,
            'y': y,
            'event': event_type,
            'round': self.round_number
        })

        self.mouse_movements = json.dumps(movements)

    def get_cumulative_fatigue_trend(self):
        """Get fatigue progression across all completed rounds - useful for analysis"""
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


# Utility function for role assignment - critical for your experiment
def ensure_all_roles_assigned(group):
    """Ensure all three roles are assigned to players"""
    selected_roles = [p.selected_role for p in group.get_players()]
    required_roles = [C.RECRUITER_ROLE, C.HR_COORDINATOR_ROLE, C.BUSINESS_PARTNER_ROLE]

    missing_roles = [role for role in required_roles if role not in selected_roles]
    unassigned_players = [p for p in group.get_players() if not p.selected_role]

    for i, player in enumerate(unassigned_players):
        if i < len(missing_roles):
            player.selected_role = missing_roles[i]