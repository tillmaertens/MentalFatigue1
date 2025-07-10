# Your original settings with minimal research-focused additions

SESSION_CONFIGS = [
    dict(
        name='applicants_study',
        display_name="Mental Fatigue Simulation",
        app_sequence=['applicants'],
        num_demo_participants=3,
    ),
]

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00,
    participation_fee=0.00,
    doc="",
)

# These fields help track data across rounds for your fatigue analysis
PARTICIPANT_FIELDS = [
    'baseline_cognitive_score',  # For comparing cognitive decline
    'experiment_start_time',     # For overall experiment duration
    'total_sessions_completed'   # For completion tracking
]

SESSION_FIELDS = [
    'experiment_date',           # For research record keeping
    'completion_rate'            # For session success tracking
]

SECRET_KEY = '12345678abcde'
LANGUAGE_CODE = 'en-us'
INSTALLED_APPS = ['otree']