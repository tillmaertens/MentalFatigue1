from otree.api import *
from .models import C, get_vacancy_info, get_applicants_data_for_vacancy, \
    load_metadata_criteria, should_show_vacancy_session, get_applicant_ids, ensure_all_roles_assigned, \
    assign_rotating_role
import random
from docx import Document
import os


# ===== TRANSITION PAGE =====

class TransitionChoice(Page):
    form_model = 'player'
    form_fields = ['continue_to_second_vacancy']

    def is_displayed(self):
        return False

    def vars_for_template(self):
        # Fixed order: completed vacancy 1, next is vacancy 2
        return {
            'completed_vacancy': 1,
            'next_vacancy': 2,
        }


# ===== BASELINE & SETUP PAGES =====

class Consent(Page):

    def is_displayed(self):
        return self.player.round_number == 1


class RoleSelection(Page):
    form_model = 'player'
    form_fields = ['selected_role']

    def is_displayed(self):
        return should_show_vacancy_session(self.player.round_number)

    def vars_for_template(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        session_number = self.get_vacancy_session_number()
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

        return {
            'session_number': session_number,
            'vacancy_number': vacancy_number,
            'total_sessions': C.SESSIONS_PER_VACANCY
        }

    def get_vacancy_session_number(self):
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return round_num - C.VACANCY_1_START_ROUND + 1
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            return round_num - C.VACANCY_2_START_ROUND + 1
        return 1


class WaitForRoles(WaitPage):
    """Wait for all players to select roles"""

    def after_all_players_arrive(group):
        ensure_all_roles_assigned(group)

    def is_displayed(self):
        displayed = should_show_vacancy_session(self.player.round_number)
        print(
            f"WaitForRoles.is_displayed: Player {self.player.id_in_group}, Round {self.player.round_number}, Display: {displayed}")
        return displayed


# ===== MAIN TASK PAGES =====

class Recruiter(Page):

    def is_displayed(self):
        if not should_show_vacancy_session(self.player.round_number):
            return False

        # AUTOMATISCHE ROLLENZUWEISUNG
        assign_rotating_role(self.player)
        return self.player.is_recruiter()

    def get_timeout_seconds(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        return vacancy_info['duration_seconds'] if vacancy_info else C.VACANCY_1_DURATION_SECONDS

    timeout_seconds = property(get_timeout_seconds)

    def vars_for_template(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        applicants_data = get_applicants_data_for_vacancy(vacancy_info)

        applicants_with_content = []
        doc_suffix = vacancy_info['doc_suffix'] if vacancy_info else '1'

        for applicant in applicants_data:
            applicant_data = applicant.copy()
            applicant_data['description'] = self.get_word_content(applicant['id'], doc_suffix)
            applicants_with_content.append(applicant_data)

        # Calculate session number within vacancy
        session_number = self.get_vacancy_session_number()
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

        return {
            'applicants': applicants_with_content,
            'session_number': session_number,
            'vacancy_number': vacancy_number,
            'remaining_time': vacancy_info['duration_seconds'] if vacancy_info else C.VACANCY_1_DURATION_SECONDS,
            'static_path': C.STATIC_APPLICANTS_PATH,
            'total_sessions': C.SESSIONS_PER_VACANCY
        }

    def get_vacancy_session_number(self):
        """Calculate session number within the current vacancy (1-6)"""
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return round_num - C.VACANCY_1_START_ROUND + 1
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            return round_num - C.VACANCY_2_START_ROUND + 1
        return 1

    def get_word_content(self, applicant_id, doc_suffix='1'):
        """Load and convert word doc to html"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))

            doc_path = os.path.join(
                current_dir,
                '..',
                '_static',
                'applicants',
                f'recruiter_maske_{applicant_id}{doc_suffix}.docx'  # Updated filename
            )

            doc_path = os.path.normpath(doc_path)
            document = Document(doc_path)
            html_content = self.convert_docx_to_html(document)
            return html_content

        except Exception as e:
            return f"<p><em>Error loading document: {str(e)}</em></p>"

    def convert_docx_to_html(self, document):
        """Convert Word document to HTML"""
        html_parts = []

        # Process paragraphs
        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if text:
                if paragraph.style.name.startswith('Heading'):
                    level = 3  # Default H3
                    if 'Heading 1' in paragraph.style.name:
                        level = 2
                    elif 'Heading 2' in paragraph.style.name:
                        level = 3
                    html_parts.append(f'<h{level}>{text}</h{level}>')
                else:
                    if any(run.bold for run in paragraph.runs):
                        html_parts.append(f'<p><strong>{text}</strong></p>')
                    else:
                        html_parts.append(f'<p>{text}</p>')

        # Process tables
        for table in document.tables:
            html_parts.append('<table style="width:100%; border-collapse: collapse; margin: 10px 0;">')

            for row_idx, row in enumerate(table.rows):
                html_parts.append('<tr>')
                for cell in row.cells:
                    cell_text = cell.text.strip()
                    # Check if it's a header row
                    if row_idx == 0 or any(run.bold for para in cell.paragraphs for run in para.runs):
                        html_parts.append(
                            f'<td style="border: 1px solid #ddd; padding: 5px; font-weight: bold; background-color: #f5f5f5;">{cell_text}</td>')
                    else:
                        html_parts.append(f'<td style="border: 1px solid #ddd; padding: 5px;">{cell_text}</td>')
                html_parts.append('</tr>')

            html_parts.append('</table>')

        if not html_parts:
            return "<p><em>The Word document is empty or could not be read.</em></p>"

        return ''.join(html_parts)


class HRCoordinator(Page):
    form_model = 'player'
    form_fields = ['criteria_added_this_session', 'validation_data_json']

    def is_displayed(self):
        if not should_show_vacancy_session(self.player.round_number):
            return False

        # AUTOMATISCHE ROLLENZUWEISUNG
        assign_rotating_role(self.player)
        return self.player.is_hr_coordinator()

    def get_timeout_seconds(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        return vacancy_info['duration_seconds'] if vacancy_info else C.VACANCY_1_DURATION_SECONDS

    timeout_seconds = property(get_timeout_seconds)

    def get_vacancy_session_number(self):
        """Calculate session number within the current vacancy (1-6)"""
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return round_num - C.VACANCY_1_START_ROUND + 1
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            return round_num - C.VACANCY_2_START_ROUND + 1
        return 1

    def before_next_page(self):
        """Validation using form data"""
        import json

        try:
            validation_data_str = self.player.validation_data_json or '{}'

            if not validation_data_str or validation_data_str == '{}':
                self.player.criteria_correct_this_session = 0
                self.player.criteria_incorrect_this_session = 0
                return

            criteria_data = json.loads(validation_data_str)
            correct_count = 0
            incorrect_count = 0

            # Load vacancy-specific metadata
            metadata = load_metadata_criteria(self.player.round_number, self.player)
            metadata_criteria = metadata['criteria']

            for criterion_name, data in criteria_data.items():
                # Find the criterion in metadata
                criterion_metadata = None
                for criterion in metadata_criteria:
                    if criterion['name'].strip().lower() == criterion_name.strip().lower():
                        criterion_metadata = criterion
                        break

                if criterion_metadata:
                    # Check scores and relevance
                    scores_correct = True
                    relevance_correct = True

                    # Check scores for each applicant
                    for applicant_id in get_applicant_ids():
                        entered_score = data['scores'].get(applicant_id, 0)
                        correct_score = criterion_metadata['scores'].get(f'applicant_{applicant_id}', 0)

                        if int(entered_score or 0) != int(correct_score):
                            scores_correct = False
                            break

                    # Check relevance
                    entered_relevance = data.get('relevance', 'normal')
                    correct_relevance = criterion_metadata.get('relevance', 'normal')
                    relevance_correct = entered_relevance == correct_relevance

                    # Count correct or incorrect
                    if scores_correct and relevance_correct:
                        correct_count += 1
                    else:
                        incorrect_count += 1
                else:
                    incorrect_count += 1

            # Update Player fields
            self.player.criteria_correct_this_session = correct_count
            self.player.criteria_incorrect_this_session = incorrect_count

        except Exception as e:
            self.player.criteria_correct_this_session = 0
            self.player.criteria_incorrect_this_session = 0

    def vars_for_template(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        applicants_data = get_applicants_data_for_vacancy(vacancy_info)

        # Load vacancy-specific metadata
        metadata = load_metadata_criteria(self.player.round_number, self.player)

        session_number = self.get_vacancy_session_number()
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

        return {
            'applicants': applicants_data,
            'min_score': C.MIN_SCORE,
            'max_score': C.MAX_SCORE,
            'session_number': session_number,
            'vacancy_number': vacancy_number,
            'remaining_time': vacancy_info['duration_seconds'] if vacancy_info else C.VACANCY_1_DURATION_SECONDS,
            'criteria_data': metadata['criteria'],
            'categories': metadata['categories'],
            'criteria_by_category': metadata['criteria_by_category'],
            'relevance_factors': C.RELEVANCE_FACTORS,
            'job_desc_file': vacancy_info['job_desc_file'] if vacancy_info else 'job_description_1.pdf',
            'static_path': C.STATIC_APPLICANTS_PATH,
            'applicant_colors': C.APPLICANT_COLORS,
            'applicant_ids': get_applicant_ids(),
            'total_sessions': C.SESSIONS_PER_VACANCY
        }


class BusinessPartner(Page):

    def is_displayed(self):
        # AUTOMATISCHE ROLLENZUWEISUNG
        if should_show_vacancy_session(self.player.round_number):
            assign_rotating_role(self.player)
            return self.player.is_business_partner()
        return False

    def should_show_vacancy_session(self):
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return True
        return False

    def get_timeout_seconds(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        return vacancy_info['duration_seconds'] if vacancy_info else C.VACANCY_1_DURATION_SECONDS

    timeout_seconds = property(get_timeout_seconds)

    def get_vacancy_session_number(self):
        """Calculate session number within the current vacancy (1-6)"""
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return round_num - C.VACANCY_1_START_ROUND + 1
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            return round_num - C.VACANCY_2_START_ROUND + 1
        return 1

    def vars_for_template(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        applicants_data = get_applicants_data_for_vacancy(vacancy_info)

        # Load vacancy-specific metadata
        metadata = load_metadata_criteria(self.player.round_number, self.player)

        session_number = self.get_vacancy_session_number()
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

        return {
            'applicants': applicants_data,
            'session_number': session_number,
            'vacancy_number': vacancy_number,
            'remaining_time': vacancy_info['duration_seconds'] if vacancy_info else C.VACANCY_1_DURATION_SECONDS,
            'criteria_data': metadata['criteria'],
            'categories': metadata['categories'],
            'criteria_by_category': metadata['criteria_by_category'],
            'static_path': C.STATIC_APPLICANTS_PATH,
            'min_score': C.MIN_SCORE,
            'max_score': C.MAX_SCORE,
            'total_sessions': C.SESSIONS_PER_VACANCY
        }


class SelfAssessment(Page):
    form_model = 'player'
    form_fields = ['fatigue_level', 'mental_effort', 'concentration_difficulty', 'motivation_level']

    def is_displayed(self):
        if not should_show_vacancy_session(self.player.round_number):
            return False
        return True

    def get_vacancy_session_number(self):
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return round_num - C.VACANCY_1_START_ROUND + 1
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            return round_num - C.VACANCY_2_START_ROUND + 1
        return 1

    def vars_for_template(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        session_number = self.get_vacancy_session_number()
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

        return {
            'session_number': session_number,
            'vacancy_number': vacancy_number,
            'role_played': self.player.selected_role,
            'total_sessions': C.SESSIONS_PER_VACANCY
        }


class CognitiveTestInstructions(Page):
    timeout_seconds = 20

    def is_displayed(self):
        if not should_show_vacancy_session(self.player.round_number):
            return False
        return True

    def get_vacancy_session_number(self):
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return round_num - C.VACANCY_1_START_ROUND + 1
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            return round_num - C.VACANCY_2_START_ROUND + 1
        return 1

    def vars_for_template(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        session_number = self.get_vacancy_session_number()
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

        return {
            'session_number': session_number,
            'vacancy_number': vacancy_number,
            'total_sessions': C.SESSIONS_PER_VACANCY
        }


class CognitiveTest(Page):
    form_model = 'player'
    form_fields = ['cognitive_test_score', 'cognitive_test_reaction_time', 'cognitive_test_errors']
    timeout_seconds = 30

    def is_displayed(self):
        if not should_show_vacancy_session(self.player.round_number):
            return False

        return True

    def get_vacancy_session_number(self):
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return round_num - C.VACANCY_1_START_ROUND + 1
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            return round_num - C.VACANCY_2_START_ROUND + 1
        return 1

    def vars_for_template(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        session_number = self.get_vacancy_session_number()
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

        # Generate random Stroop test items
        test_items = []
        color_mapping = {
            '#ff0000': 'red',
            '#0000ff': 'blue',
            '#00ff00': 'green',
            '#ffff00': 'yellow'
        }

        for i in range(20):
            word = random.choice(C.STROOP_WORDS)
            color_hex = random.choice(C.STROOP_COLORS)
            color_name = color_mapping[color_hex]

            test_items.append({
                'word': word,
                'color': color_hex,
                'correct_answer': color_name
            })

        return {
            'test_items': test_items,
            'test_duration': 30,
            'session_number': session_number,
            'vacancy_number': vacancy_number,
            'total_sessions': C.SESSIONS_PER_VACANCY
        }


class CognitiveTestResults(Page):
    timeout_seconds = 20

    def is_displayed(self):
        if not should_show_vacancy_session(self.player.round_number):
            return False

        return True

    def get_vacancy_session_number(self):
        round_num = self.player.round_number
        if C.VACANCY_1_START_ROUND <= round_num <= C.VACANCY_1_END_ROUND:
            return round_num - C.VACANCY_1_START_ROUND + 1
        elif C.VACANCY_2_START_ROUND <= round_num <= C.VACANCY_2_END_ROUND:
            return round_num - C.VACANCY_2_START_ROUND + 1
        return 1

    def vars_for_template(self):
        vacancy_info = get_vacancy_info(self.player.round_number, self.player)
        session_number = self.get_vacancy_session_number()
        vacancy_number = vacancy_info['vacancy'] if vacancy_info else 1

        return {
            'session_number': session_number,
            'vacancy_number': vacancy_number,
            'score': self.player.field_maybe_none('cognitive_test_score') or 0,
            'reaction_time': self.player.field_maybe_none('cognitive_test_reaction_time') or 0,
            'errors': self.player.field_maybe_none('cognitive_test_errors') or 0,
            'total_items': 20,
            'total_sessions': C.SESSIONS_PER_VACANCY
        }


# ===== FINAL RESULTS =====

class FinalResults(Page):

    def is_displayed(self):
        return (self.player.round_number == C.VACANCY_1_RESULTS_ROUND or
                self.player.round_number == C.FINAL_RESULTS_ROUND)

    def vars_for_template(self):
        is_vacancy_1_results = self.player.round_number == C.VACANCY_1_RESULTS_ROUND
        show_next_button = is_vacancy_1_results

        if is_vacancy_1_results:
            start_round = C.VACANCY_1_START_ROUND  # 1
            end_round = C.VACANCY_1_END_ROUND  # 6
            results_vacancy = 1
        else:
            start_round = C.VACANCY_2_START_ROUND  # 8
            end_round = C.VACANCY_2_END_ROUND  # 13
            results_vacancy = 2

        # Compile results WITH NULL SAFETY
        all_sessions_data = []
        for round_num in range(start_round, end_round + 1):
            try:
                round_player = self.player.in_round(round_num)

                # SAFE ACCESS WITH TRY-EXCEPT FOR oTree FIELDS
                def safe_get(field_func, default=0):
                    try:
                        value = field_func()
                        return value if value is not None else default
                    except:
                        return default

                session_data = {
                    'session': round_num - start_round + 1,  # Display as 1-6
                    'role': safe_get(lambda: round_player.selected_role, 'Unknown'),
                    'fatigue_level': safe_get(lambda: round_player.fatigue_level),
                    'mental_effort': safe_get(lambda: round_player.mental_effort),
                    'concentration_difficulty': safe_get(lambda: round_player.concentration_difficulty),
                    'motivation_level': safe_get(lambda: round_player.motivation_level),
                    'cognitive_score': safe_get(lambda: round_player.cognitive_test_score),
                    'cognitive_reaction_time': safe_get(lambda: round_player.cognitive_test_reaction_time),
                    'criteria_added': safe_get(lambda: round_player.criteria_added_this_session),
                    'criteria_correct': safe_get(lambda: round_player.criteria_correct_this_session),
                    'criteria_incorrect': safe_get(lambda: round_player.criteria_incorrect_this_session),
                }
                all_sessions_data.append(session_data)
            except Exception as e:
                continue

        # Calculate trends WITH NULL SAFETY
        fatigue_values = [s['fatigue_level'] for s in all_sessions_data if
                          s['fatigue_level'] and s['fatigue_level'] > 0]
        cognitive_values = [s['cognitive_score'] for s in all_sessions_data if
                            s['cognitive_score'] and s['cognitive_score'] > 0]
        effort_values = [s['mental_effort'] for s in all_sessions_data if s['mental_effort'] and s['mental_effort'] > 0]
        concentration_values = [s['concentration_difficulty'] for s in all_sessions_data if
                                s['concentration_difficulty'] and s['concentration_difficulty'] > 0]
        motivation_values = [s['motivation_level'] for s in all_sessions_data if
                             s['motivation_level'] and s['motivation_level'] > 0]

        # SAFE CALCULATIONS
        average_fatigue = sum(fatigue_values) / len(fatigue_values) if fatigue_values else 0
        fatigue_increase = fatigue_values[-1] - fatigue_values[0] if len(fatigue_values) >= 2 else 0
        cognitive_decline = cognitive_values[0] - cognitive_values[-1] if len(cognitive_values) >= 2 else 0

        # Additional averages
        average_effort = sum(effort_values) / len(effort_values) if effort_values else 0
        average_concentration = sum(concentration_values) / len(concentration_values) if concentration_values else 0
        average_motivation = sum(motivation_values) / len(motivation_values) if motivation_values else 0

        result = {
            'all_sessions': all_sessions_data,
            'results_vacancy': results_vacancy,
            'total_sessions_completed': len(all_sessions_data),
            'average_fatigue': average_fatigue,
            'fatigue_increase': fatigue_increase,
            'cognitive_decline': cognitive_decline,
            'average_effort': average_effort,
            'average_concentration': average_concentration,
            'average_motivation': average_motivation,
            'show_next_button': show_next_button,
            'is_vacancy_1_results': is_vacancy_1_results
        }
        return result


page_sequence = [
    Consent,
    Recruiter,
    HRCoordinator,
    BusinessPartner,
    SelfAssessment,
    CognitiveTestInstructions,
    CognitiveTest,
    CognitiveTestResults,
    FinalResults
]
