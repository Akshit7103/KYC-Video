"""
Script Compliance Checker Module
Verifies if all mandatory KYC questions were asked per RBI guidelines
"""

import os
import json
import re
from difflib import SequenceMatcher


class ScriptChecker:
    """
    Checks if Video KYC call followed the mandatory script.
    Verifies all required questions were asked and proper responses received.
    """

    def __init__(self, script_path='data/scripts/rbi_kyc_script.json'):
        """
        Initialize script checker

        Args:
            script_path: Path to RBI KYC script JSON file
        """
        self.script_path = script_path
        self.script_data = None
        self.mandatory_checks = []

        print("Initializing Script Compliance Checker...")
        self._load_script()

    def _load_script(self):
        """Load the RBI KYC script"""
        try:
            with open(self.script_path, 'r', encoding='utf-8') as f:
                self.script_data = json.load(f)

            # Extract mandatory checks
            self._extract_mandatory_checks()

            print(f"  Loaded script: {self.script_data.get('script_name', 'Unknown')}")
            print(f"  Total sections: {self.script_data.get('total_sections', 0)}")
            print(f"  Mandatory checks: {len(self.mandatory_checks)}")

        except FileNotFoundError:
            print(f"  Warning: Script file not found at {self.script_path}")
            self._use_default_checks()

    def _extract_mandatory_checks(self):
        """Extract all mandatory checks from script"""
        self.mandatory_checks = []

        # Key phrases that MUST be in the call
        # These are extracted from the RBI script
        for section in self.script_data.get('sections', []):
            if not section.get('mandatory', False):
                continue

            for line in section.get('script_lines', []):
                text = line.get('text', '')

                # Skip template placeholders and grouping lines
                if (text.startswith('[') and text.endswith(']')) or line.get('group_with_next', False):
                    continue

                # Skip lines that are just instructions like "[Read address]"
                if text in ['[Read address]', '[Customer Name]', '[Bank Name]', '[Bank/NBFC Name]']:
                    continue

                check_item = {
                    'section': section['section_name'],
                    'section_id': section['section_id'],
                    'line_id': line.get('line_id', ''),
                    'text': text,
                    'speaker': line.get('speaker', 'agent'),
                    'critical': line.get('critical', False),
                    'expects_response': line.get('expects_response', False),
                    'expected_response': line.get('expected_response', ''),
                    'liveness_check': line.get('liveness_check', False),
                    'compliance_check': line.get('compliance_check', ''),
                    'action_required': line.get('action_required', '')
                }

                self.mandatory_checks.append(check_item)

        # Add critical checks from script
        for check in self.script_data.get('critical_checks', []):
            existing = next((m for m in self.mandatory_checks if m['line_id'] == check.get('line')), None)
            if existing:
                existing['critical'] = True
                existing['failure_action'] = check.get('failure_action', '')

    def _use_default_checks(self):
        """Use default mandatory checks if script not found"""
        self.mandatory_checks = [
            # Consent checks
            {'section': 'Introduction', 'text': 'video call is live and being recorded', 'critical': True},
            {'section': 'Introduction', 'text': 'currently present in India', 'critical': True, 'expects_response': True},
            {'section': 'Introduction', 'text': 'attending this call on your own', 'critical': True, 'expects_response': True},

            # Personal details
            {'section': 'Personal Details', 'text': 'full name', 'expects_response': True},
            {'section': 'Personal Details', 'text': 'date of birth', 'expects_response': True},
            {'section': 'Personal Details', 'text': 'purpose', 'expects_response': True},

            # Document verification
            {'section': 'PAN Verification', 'text': 'PAN card', 'critical': True, 'action_required': 'show_pan'},
            {'section': 'Aadhaar Verification', 'text': 'Aadhaar', 'critical': True, 'action_required': 'show_aadhaar'},
            {'section': 'Aadhaar Verification', 'text': 'masked', 'critical': True, 'compliance_check': True},

            # Liveness
            {'section': 'Liveness', 'text': 'blink', 'liveness_check': True},
            {'section': 'Liveness', 'text': 'turn your face', 'liveness_check': True},
            {'section': 'Liveness', 'text': 'smile', 'liveness_check': True},

            # Declarations
            {'section': 'Declarations', 'text': 'not acting on behalf', 'critical': True, 'expects_response': True},
            {'section': 'Declarations', 'text': 'illegal activities', 'critical': True, 'expects_response': True},
            {'section': 'Declarations', 'text': 'politically exposed', 'expects_response': True},
        ]

    def _normalize_text(self, text):
        """Normalize text for comparison"""
        if not text:
            return ''
        # Convert to lowercase, remove extra spaces
        text = text.lower().strip()
        text = re.sub(r'\s+', ' ', text)
        # Remove punctuation for matching
        text = re.sub(r'[^\w\s]', '', text)
        return text

    def _fuzzy_match(self, text1, text2, threshold=0.7):
        """
        Check if two texts are similar enough

        Args:
            text1: First text
            text2: Second text
            threshold: Minimum similarity ratio (0-1)

        Returns:
            Tuple of (is_match, similarity_score)
        """
        norm1 = self._normalize_text(text1)
        norm2 = self._normalize_text(text2)

        # Check if one contains the other
        if norm1 in norm2 or norm2 in norm1:
            return True, 1.0

        # Use SequenceMatcher for fuzzy matching
        ratio = SequenceMatcher(None, norm1, norm2).ratio()

        return ratio >= threshold, ratio

    def _keyword_match(self, keywords, text):
        """
        Check if key phrases are present in text

        Args:
            keywords: Key phrases to look for
            text: Text to search in

        Returns:
            Boolean indicating if keywords found
        """
        norm_text = self._normalize_text(text)

        if isinstance(keywords, str):
            keywords = [keywords]

        for keyword in keywords:
            norm_keyword = self._normalize_text(keyword)
            if norm_keyword in norm_text:
                return True

        return False

    def check_compliance(self, transcript):
        """
        Check if transcript complies with mandatory script

        Args:
            transcript: Transcript dictionary with 'full_text' and 'segments'

        Returns:
            Compliance check results
        """
        print(f"\n{'='*60}")
        print("SCRIPT COMPLIANCE CHECK")
        print(f"{'='*60}")

        full_text = transcript.get('full_text', '')
        segments = transcript.get('segments', [])

        results = {
            'checks': [],
            'passed_checks': 0,
            'failed_checks': 0,
            'critical_failures': 0,
            'total_checks': len(self.mandatory_checks),
            'compliance_score': 0,
            'sections_covered': set(),
            'missing_critical': [],
            'warnings': []
        }

        print(f"Running {len(self.mandatory_checks)} mandatory checks...")

        for check in self.mandatory_checks:
            check_text = check.get('text', '')
            section = check.get('section', 'Unknown')

            # Search for this phrase in transcript
            found = self._keyword_match(check_text, full_text)

            # If not found with keyword, try fuzzy match with segments
            if not found:
                for seg in segments:
                    match, score = self._fuzzy_match(check_text, seg.get('text', ''))
                    if match:
                        found = True
                        break

            check_result = {
                'section': section,
                'line_id': check.get('line_id', ''),
                'expected_text': check_text,
                'found': found,
                'critical': check.get('critical', False),
                'liveness_check': check.get('liveness_check', False)
            }

            if found:
                results['passed_checks'] += 1
                results['sections_covered'].add(section)
            else:
                results['failed_checks'] += 1
                if check.get('critical', False):
                    results['critical_failures'] += 1
                    results['missing_critical'].append(check_result)
                else:
                    results['warnings'].append(check_result)

            results['checks'].append(check_result)

        # Convert set to list for JSON serialization
        results['sections_covered'] = list(results['sections_covered'])

        # Calculate compliance score
        if results['total_checks'] > 0:
            # Weighted score: critical checks are worth more
            critical_checks = [c for c in results['checks'] if c['critical']]
            non_critical_checks = [c for c in results['checks'] if not c['critical']]

            critical_score = 0
            if critical_checks:
                critical_passed = sum(1 for c in critical_checks if c['found'])
                critical_score = (critical_passed / len(critical_checks)) * 60  # 60% weight

            non_critical_score = 0
            if non_critical_checks:
                non_critical_passed = sum(1 for c in non_critical_checks if c['found'])
                non_critical_score = (non_critical_passed / len(non_critical_checks)) * 40  # 40% weight

            results['compliance_score'] = round(critical_score + non_critical_score, 2)

        # Determine overall compliance
        results['is_compliant'] = (
            results['critical_failures'] == 0 and
            results['compliance_score'] >= 70
        )

        results['passed'] = results['is_compliant']

        # Print summary
        self._print_summary(results)

        return results

    def check_responses(self, transcript, qa_pairs=None):
        """
        Check if customer provided required responses

        Args:
            transcript: Transcript dictionary
            qa_pairs: Optional Q&A pairs from transcript

        Returns:
            Response check results
        """
        print("\nChecking customer responses...")

        if qa_pairs is None:
            qa_pairs = transcript.get('qa_pairs', [])

        # Expected affirmative responses
        affirmative_patterns = [
            'yes', 'yeah', 'haan', 'ji', 'correct', 'confirmed', 'ok', 'okay',
            'that is correct', 'i confirm', 'i agree'
        ]

        # Expected negative for PEP check
        negative_patterns = [
            'no', 'nahi', 'not', 'i am not'
        ]

        response_checks = []

        for check in self.mandatory_checks:
            if not check.get('expects_response', False):
                continue

            expected_response = check.get('expected_response', '')

            # Find matching Q&A (with flexible matching)
            matched_qa = None
            check_text_norm = self._normalize_text(check.get('text', ''))

            for qa in qa_pairs:
                question_text = qa.get('question', {}).get('text', '')
                answer_text = qa.get('answer', {}).get('text', '')

                # Check if question text matches
                question_match = self._keyword_match(check.get('text', ''), question_text)

                # For declarations, also check if answer text contains the declaration
                # (since answers now have format "Declaration → response")
                answer_contains_declaration = check_text_norm in self._normalize_text(answer_text)

                if question_match or answer_contains_declaration:
                    matched_qa = qa
                    break

            if matched_qa and matched_qa.get('answered', False):
                answer_text = matched_qa.get('answer', {}).get('text', '')
                response_delay = matched_qa.get('response_delay', 0)

                # Check if response is appropriate
                is_affirmative = any(p in self._normalize_text(answer_text) for p in affirmative_patterns)
                is_negative = any(p in self._normalize_text(answer_text) for p in negative_patterns)

                # For declarations and other statements, just answering is appropriate
                is_answered_appropriately = (
                    is_affirmative or
                    is_negative or
                    len(answer_text.split()) >= 2  # Name, date, PAN etc. (multi-word answers)
                )

                response_check = {
                    'question': check.get('text', ''),
                    'answer': answer_text,
                    'response_delay': response_delay,
                    'answered': True,
                    'appropriate': is_answered_appropriately,
                    'flags': []
                }

                # Flag unusual response delays (but not for immediate responses which are normal)
                if response_delay > 5:
                    response_check['flags'].append('long_hesitation')
                elif response_delay < 0.5 and response_delay > 0:
                    response_check['flags'].append('suspiciously_fast')

            else:
                response_check = {
                    'question': check.get('text', ''),
                    'answered': False,
                    'flags': ['no_response']
                }

            response_checks.append(response_check)

        answered_count = sum(1 for r in response_checks if r.get('answered', False))
        appropriate_count = sum(1 for r in response_checks if r.get('appropriate', False))

        return {
            'total_expected_responses': len(response_checks),
            'responses_received': answered_count,
            'appropriate_responses': appropriate_count,
            'response_rate': (answered_count / len(response_checks) * 100) if response_checks else 0,
            'checks': response_checks
        }

    def _print_summary(self, results):
        """Print compliance check summary"""
        print(f"\n{'='*60}")
        print("COMPLIANCE RESULT")
        print(f"{'='*60}")
        print(f"Compliance Score: {results['compliance_score']}/100")
        print(f"Checks Passed: {results['passed_checks']}/{results['total_checks']}")
        print(f"Critical Failures: {results['critical_failures']}")
        print(f"Sections Covered: {', '.join(results['sections_covered'])}")

        if results['missing_critical']:
            print(f"\nWARNING:  Missing Critical Items:")
            for item in results['missing_critical']:
                print(f"   - [{item['section']}] {item['expected_text'][:50]}...")

        if results['warnings']:
            print(f"\nWARNING:  Warnings ({len(results['warnings'])}):")
            for item in results['warnings'][:5]:  # Show first 5
                print(f"   - [{item['section']}] {item['expected_text'][:50]}...")

        print(f"\nCompliant: {'YES' if results['is_compliant'] else 'NO'}")
        print(f"{'='*60}\n")

    def get_compliance_score(self, transcript):
        """
        Get a single compliance score (0-100)

        Args:
            transcript: Transcript dictionary

        Returns:
            Score and detailed results
        """
        results = self.check_compliance(transcript)
        response_results = self.check_responses(transcript)

        # Combine scores
        script_score = results['compliance_score'] * 0.7  # 70% weight
        response_score = response_results['response_rate'] * 0.3  # 30% weight

        final_score = round(script_score + response_score, 2)

        return {
            'score': final_score,
            'passed': results['is_compliant'] and response_results['response_rate'] >= 80,
            'script_compliance': results,
            'response_compliance': response_results
        }

    def save_results(self, results, output_path):
        """Save compliance results to JSON"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Compliance results saved to: {output_path}")


def check_script_compliance(transcript, script_path='data/scripts/rbi_kyc_script.json', output_dir=None):
    """
    Convenience function to check script compliance

    Args:
        transcript: Transcript dictionary or path to transcript JSON
        script_path: Path to RBI KYC script
        output_dir: Optional output directory

    Returns:
        Compliance results
    """
    # Load transcript if path provided
    if isinstance(transcript, str):
        with open(transcript, 'r', encoding='utf-8') as f:
            transcript = json.load(f)

    checker = ScriptChecker(script_path)
    results = checker.get_compliance_score(transcript)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(output_dir, f'compliance_results_{timestamp}.json')
        checker.save_results(results, output_path)

    return results


if __name__ == '__main__':
    import sys

    if len(sys.argv) >= 2:
        transcript_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else 'outputs/compliance'

        if os.path.exists(transcript_path):
            results = check_script_compliance(transcript_path, output_dir=output_dir)
            print(f"Final Score: {results['score']}/100")
        else:
            print(f"Transcript not found: {transcript_path}")
    else:
        print("Usage: python script_checker.py <transcript_path> [output_dir]")
