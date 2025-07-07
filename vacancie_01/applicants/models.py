from otree.api import *
import json
import time

doc = """
Mental Fatigue Experiment - 6 Sessions of 10min digital coworking with role rotation
"""


class Applicant:
    """Class for a single applicant"""

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
    applicant_a = Applicant('a', 'Applicant A', 'Software developer with 5 years experience.')
    applicant_b = Applicant('b', 'Applicant B', 'Marketing specialist with international experience.')
    applicant_c = Applicant('c', 'Applicant C', 'Project manager with agile expertise.')
    applicants.extend([applicant_a, applicant_b, applicant_c])
    return applicants


def get_applicants_data():
    applicant_objects = create_applicants()
    return [applicant.to_dict() for applicant in applicant_objects]


class C(BaseConstants):
    NAME_IN_URL = 'mental_fatigue'
    PLAYERS_PER_GROUP = 3
    NUM_ROUNDS = 6  # 6 sessions of 10 minutes each

    # Timing
    SESSION_DURATION_MINUTES = 10
    SESSION_DURATION_SECONDS = SESSION_DURATION_MINUTES * 60

    # Data for templates
    APPLICANTS = get_applicants_data()

    # Evaluation settings
    MIN_SCORE = 0
    MAX_SCORE = 8
    RELEVANCE_FACTORS = {'low': 1, 'normal': 2, 'high': 3}

    # Cognitive Load Test settings
    COGNITIVE_TEST_DURATION = 60  # seconds
    STROOP_WORDS = ['red', 'blue', 'green', 'yellow']
    STROOP_COLORS = ['#ff0000', '#0000ff', '#00ff00', '#ffff00']


class Subsession(BaseSubsession):
    def creating_session(self):
        """Initialize session data"""
        # Store session start time for each round
        for group in self.get_groups():
            group.session_start_time = time.time()


class Group(BaseGroup):
    # Session timing
    session_start_time = models.FloatField(
        doc="Unix timestamp when this session started"
    )

    session_end_time = models.FloatField(
        blank=True,
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

        total_possible_scores = len(evaluation) * 3  # 3 applicants per criterion
        filled_scores = 0

        for criterion_data in evaluation.values():
            scores = criterion_data.get('scores', {})
            filled_scores += len([s for s in scores.values() if s])

        self.session_completion_rate = (filled_scores / total_possible_scores * 100) if total_possible_scores > 0 else 0


class Player(BasePlayer):
    # Role selection for each round
    selected_role = models.StringField(
        choices=['Recruiter', 'HR-Coordinator', 'Business-Partner'],
        blank=True,
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
        blank=True,
        doc="When this player started the session"
    )

    session_end_timestamp = models.FloatField(
        blank=True,
        doc="When this player finished the session"
    )

    # Reaction time data (JSON array of measurements)
    reaction_times = models.LongStringField(
        blank=True,
        doc="JSON array of reaction times for various actions"
    )

    # Mouse movement data (for later analysis)
    mouse_movements = models.LongStringField(
        blank=True,
        doc="JSON array of mouse movement data"
    )

    # Self-assessment after each session (1-10 scales)
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

    # Physiological data placeholders (for future lab integration)
    eeg_data_file = models.StringField(
        blank=True,
        doc="Filename of EEG data for this session (for lab experiments)"
    )

    eye_tracking_data_file = models.StringField(
        blank=True,
        doc="Filename of eye tracking data for this session (for lab experiments)"
    )

    heart_rate_data = models.LongStringField(
        blank=True,
        doc="JSON array of heart rate measurements (if available)"
    )

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
        """Get fatigue progression across all completed rounds"""
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
