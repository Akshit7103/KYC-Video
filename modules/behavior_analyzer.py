"""
Behavior Analyzer Module
Detects suspicious behavior patterns in Video KYC calls
Red flags: evasion, resistance, unusual responses
"""

import os
import json
import re
from collections import defaultdict


class BehaviorAnalyzer:
    """
    Analyzes customer behavior during Video KYC for red flags.
    Detects evasion, resistance, and suspicious patterns.
    """

    def __init__(self):
        """Initialize behavior analyzer with red flag patterns"""
        print("Initializing Behavior Analyzer...")

        # Define red flag patterns
        self._define_red_flags()

        print("  Behavior analyzer initialized")

    def _define_red_flags(self):
        """Define patterns that indicate suspicious behavior"""

        # Evasive/Resistant phrases (customer)
        self.evasive_patterns = [
            # Questions about why information is needed
            r'why do you need',
            r'why are you asking',
            r'why should i',
            r'what for',
            r'is this necessary',
            r'do i have to',
            r'i don\'t want to',
            r'none of your business',
            r'that\'s personal',
            r'i don\'t see why',

            # Refusal patterns
            r'i won\'t',
            r'i refuse',
            r'i can\'t tell',
            r'i don\'t have',
            r'not available',
            r'don\'t have it',
            r'left at home',
            r'forgot',
            r'can\'t find',

            # Deflection
            r'can we skip',
            r'let\'s move on',
            r'next question',
            r'i already told',
            r'i said before',
            r'you already asked',
        ]

        # Aggressive/Hostile patterns
        self.hostile_patterns = [
            r'this is stupid',
            r'waste of time',
            r'ridiculous',
            r'hurry up',
            r'too many questions',
            r'enough',
            r'stop asking',
            r'mind your own',
            r'none of your',
            r'what\'s the problem',
            r'just do it',
            r'just process',
        ]

        # Suspicious content patterns
        self.suspicious_patterns = [
            # Third party involvement
            r'my friend',
            r'someone is here',
            r'helping me',
            r'they told me',
            r'he said',
            r'she said',
            r'they said',

            # Location issues
            r'not in india',
            r'abroad',
            r'outside india',
            r'different country',

            # Identity concerns
            r'not my',
            r'borrowed',
            r'someone else',
            r'different name',
            r'changed name',
        ]

        # Hesitation patterns (often followed by uncertain responses)
        self.hesitation_patterns = [
            r'^um+',
            r'^uh+',
            r'^hmm+',
            r'^err+',
            r'let me think',
            r'i think',
            r'i guess',
            r'maybe',
            r'not sure',
            r'i don\'t know',
            r'i\'m not certain',
        ]

        # Compile all patterns
        self.all_patterns = {
            'evasive': [re.compile(p, re.IGNORECASE) for p in self.evasive_patterns],
            'hostile': [re.compile(p, re.IGNORECASE) for p in self.hostile_patterns],
            'suspicious': [re.compile(p, re.IGNORECASE) for p in self.suspicious_patterns],
            'hesitation': [re.compile(p, re.IGNORECASE) for p in self.hesitation_patterns]
        }

        # Severity weights
        self.severity_weights = {
            'evasive': 2,
            'hostile': 1.5,
            'suspicious': 3,  # Most severe
            'hesitation': 0.5
        }

    def analyze_text(self, text):
        """
        Analyze a single text segment for red flags

        Args:
            text: Text to analyze

        Returns:
            Dictionary with detected flags
        """
        if not text:
            return {'flags': [], 'score': 0}

        flags = []
        total_score = 0

        for category, patterns in self.all_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    flags.append({
                        'category': category,
                        'pattern': pattern.pattern,
                        'text_matched': text[:100],
                        'severity': self.severity_weights[category]
                    })
                    total_score += self.severity_weights[category]

        return {
            'flags': flags,
            'score': total_score,
            'has_red_flags': len(flags) > 0
        }

    def analyze_transcript(self, transcript):
        """
        Analyze full transcript for behavioral red flags

        Args:
            transcript: Transcript dictionary with segments

        Returns:
            Comprehensive behavior analysis
        """
        print(f"\n{'='*60}")
        print("BEHAVIOR ANALYSIS")
        print(f"{'='*60}")

        segments = transcript.get('segments', [])
        full_text = transcript.get('full_text', '')

        results = {
            'segment_analysis': [],
            'category_counts': defaultdict(int),
            'total_flags': 0,
            'risk_score': 0,
            'flagged_segments': [],
            'critical_flags': []
        }

        print(f"Analyzing {len(segments)} segments...")

        for seg in segments:
            text = seg.get('text', '')
            speaker = seg.get('speaker', 'unknown')

            # Only analyze customer speech for behavioral flags
            if speaker == 'agent':
                continue

            analysis = self.analyze_text(text)

            seg_result = {
                'timestamp': seg.get('start', 0),
                'timestamp_formatted': seg.get('start_formatted', ''),
                'text': text[:200],
                'speaker': speaker,
                'flags': analysis['flags'],
                'score': analysis['score']
            }

            results['segment_analysis'].append(seg_result)

            if analysis['has_red_flags']:
                results['flagged_segments'].append(seg_result)
                results['total_flags'] += len(analysis['flags'])

                for flag in analysis['flags']:
                    results['category_counts'][flag['category']] += 1

                    # Mark as critical if suspicious category
                    if flag['category'] == 'suspicious':
                        results['critical_flags'].append(seg_result)

        # Calculate risk score (0-100)
        max_expected_flags = len(segments) * 0.1  # Expect <10% segments to have flags
        if max_expected_flags > 0:
            flag_ratio = results['total_flags'] / max_expected_flags
            results['risk_score'] = min(100, flag_ratio * 50)
        else:
            results['risk_score'] = 0

        # Analyze response patterns
        results['response_patterns'] = self._analyze_response_patterns(segments)

        # Determine behavior score (inverted - lower is better behavior)
        behavior_score = 100 - results['risk_score']
        results['behavior_score'] = max(0, behavior_score)
        results['passed'] = results['behavior_score'] >= 60 and len(results['critical_flags']) == 0

        # Determine risk level
        if results['risk_score'] >= 60 or len(results['critical_flags']) > 0:
            results['risk_level'] = 'HIGH'
        elif results['risk_score'] >= 30:
            results['risk_level'] = 'MEDIUM'
        else:
            results['risk_level'] = 'LOW'

        # Convert defaultdict to regular dict
        results['category_counts'] = dict(results['category_counts'])

        self._print_summary(results)

        return results

    def _analyze_response_patterns(self, segments):
        """
        Analyze patterns in customer responses

        Args:
            segments: Transcript segments

        Returns:
            Response pattern analysis
        """
        customer_segments = [s for s in segments if s.get('speaker') == 'customer']

        if not customer_segments:
            return {
                'average_response_length': 0,
                'short_responses': 0,
                'interruptions': 0
            }

        # Calculate average response length
        response_lengths = [len(s.get('text', '').split()) for s in customer_segments]
        avg_length = sum(response_lengths) / len(response_lengths) if response_lengths else 0

        # Count very short responses (possibly evasive)
        short_responses = sum(1 for l in response_lengths if l <= 3)

        # Detect possible interruptions (responses that start very quickly)
        interruptions = 0
        for i, seg in enumerate(segments):
            if seg.get('speaker') == 'customer' and i > 0:
                prev_seg = segments[i - 1]
                if prev_seg.get('speaker') == 'agent':
                    response_gap = seg.get('start', 0) - prev_seg.get('end', 0)
                    if response_gap < 0.3:  # Less than 0.3 second gap
                        interruptions += 1

        return {
            'average_response_length': round(avg_length, 2),
            'short_responses': short_responses,
            'short_response_ratio': short_responses / len(customer_segments) if customer_segments else 0,
            'interruptions': interruptions
        }

    def analyze_timing(self, transcript):
        """
        Analyze timing patterns for suspicious behavior

        NOTE: For TTS-based recordings (system reads questions, human responds),
        very fast response times (0-0.5s) are NORMAL and EXPECTED, not suspicious.
        Only flag if response time is negative (actual interruption).

        Args:
            transcript: Transcript with segments

        Returns:
            Timing analysis results
        """
        segments = transcript.get('segments', [])

        # Calculate response times
        response_times = []
        for i, seg in enumerate(segments):
            if seg.get('speaker') == 'customer' and i > 0:
                prev_seg = segments[i - 1]
                if prev_seg.get('speaker') == 'agent':
                    response_time = seg.get('start', 0) - prev_seg.get('end', 0)
                    response_times.append({
                        'timestamp': seg.get('start', 0),
                        'response_time': response_time,
                        'question': prev_seg.get('text', '')[:50],
                        'answer': seg.get('text', '')[:50]
                    })

        if not response_times:
            return {
                'average_response_time': 0,
                'suspiciously_fast': 0,
                'long_hesitations': 0
            }

        avg_response = sum(r['response_time'] for r in response_times) / len(response_times)

        # Flag suspicious timings:
        # - Fast responses: Only flag if NEGATIVE (actual interruption)
        #   Don't flag 0-0.5s for TTS recordings - that's normal!
        # - Slow responses: Still flag long hesitations (>10s)
        fast_responses = [r for r in response_times if r['response_time'] < 0]  # Changed from 0.5 to 0
        slow_responses = [r for r in response_times if r['response_time'] > 10]  # Changed from 5 to 10

        return {
            'average_response_time': round(avg_response, 2),
            'suspiciously_fast': len(fast_responses),
            'long_hesitations': len(slow_responses),
            'fast_response_details': fast_responses[:5],
            'slow_response_details': slow_responses[:5]
        }

    def _print_summary(self, results):
        """Print behavior analysis summary"""
        print(f"\n{'='*60}")
        print("BEHAVIOR RESULT")
        print(f"{'='*60}")
        print(f"Behavior Score: {results['behavior_score']:.1f}/100")
        print(f"Risk Level: {results['risk_level']}")
        print(f"Total Flags: {results['total_flags']}")
        print(f"Critical Flags: {len(results['critical_flags'])}")

        if results['category_counts']:
            print(f"\nFlag Categories:")
            for cat, count in results['category_counts'].items():
                print(f"  - {cat}: {count}")

        if results['critical_flags']:
            print(f"\nWARNING:  Critical Flags Detected:")
            for flag in results['critical_flags'][:3]:
                print(f"   [{flag['timestamp_formatted']}] {flag['text'][:60]}...")

        print(f"\nPassed: {'YES' if results['passed'] else 'NO'}")
        print(f"{'='*60}\n")

    def get_behavior_score(self, transcript):
        """
        Get a single behavior score (0-100)

        Args:
            transcript: Transcript dictionary

        Returns:
            Score and detailed results
        """
        results = self.analyze_transcript(transcript)
        timing_results = self.analyze_timing(transcript)

        # Combine into final score
        base_score = results['behavior_score']

        # Deduct for timing issues (reduced penalty for TTS recordings)
        # - Long hesitations (>10s): 1 point each (was 2)
        # - Interruptions (negative time): 2 points each (was 3)
        timing_penalty = (timing_results['long_hesitations'] * 1 +
                         timing_results['suspiciously_fast'] * 2)
        adjusted_score = max(0, base_score - timing_penalty)

        return {
            'score': round(adjusted_score, 2),
            'passed': adjusted_score >= 60 and len(results['critical_flags']) == 0,
            'risk_level': results['risk_level'],
            'behavior_analysis': results,
            'timing_analysis': timing_results
        }

    def save_results(self, results, output_path):
        """Save behavior analysis results to JSON"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Behavior results saved to: {output_path}")


def analyze_behavior(transcript, output_dir=None):
    """
    Convenience function to analyze behavior

    Args:
        transcript: Transcript dictionary or path
        output_dir: Optional output directory

    Returns:
        Behavior analysis results
    """
    if isinstance(transcript, str):
        with open(transcript, 'r', encoding='utf-8') as f:
            transcript = json.load(f)

    analyzer = BehaviorAnalyzer()
    results = analyzer.get_behavior_score(transcript)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(output_dir, f'behavior_results_{timestamp}.json')
        analyzer.save_results(results, output_path)

    return results


if __name__ == '__main__':
    import sys

    if len(sys.argv) >= 2:
        transcript_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else 'outputs/behavior'

        if os.path.exists(transcript_path):
            results = analyze_behavior(transcript_path, output_dir)
            print(f"Behavior Score: {results['score']}/100")
            print(f"Risk Level: {results['risk_level']}")
        else:
            print(f"Transcript not found: {transcript_path}")
    else:
        print("Usage: python behavior_analyzer.py <transcript_path> [output_dir]")
