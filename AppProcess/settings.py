LANGUAGE_CODE = 'de'
SECRET_KEY = '1234567890abcdef'

SESSION_CONFIGS = [
    dict(
        name='applicants',
        display_name="Applicant Selection",
        num_demo_participants=1,
        app_sequence=['applicants'],
    ),
]

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00,
    participation_fee=0.00,
    doc=""
)

PARTICIPANT_FIELDS = []
SESSION_FIELDS = []
