from otree.api import *

doc = """
Bewerberauswahl und Anzeige von PDF-Dokumenten.
"""

class C(BaseConstants):
    NAME_IN_URL = 'applicants'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
    APPLICANTS = ['a', 'b', 'c']
    BASE_PATH = r"C:\Users\tillm\OneDrive\Bachelorarbeit\OtreeProg\vacancy_01"

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    selected_applicant = models.StringField(initial='a')
