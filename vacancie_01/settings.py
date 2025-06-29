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

PARTICIPANT_FIELDS = []
SESSION_FIELDS = []

SECRET_KEY = '12345678abcde'
LANGUAGE_CODE = 'en-us'
INSTALLED_APPS = ['otree']