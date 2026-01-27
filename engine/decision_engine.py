"""
Decision Engine
Aggregates all module scores and makes final PASS/REJECT/FLAG decision
"""

import os
import json
from datetime import datetime
from enum import Enum


class Decision(Enum):
    """Possible KYC decisions"""
    PASS = "PASS"
    REJECT = "REJECT"
    FLAG = "FLAG"


class DecisionEngine:
    """
    Decision Engine for Video KYC verification.
    Combines all module scores and applies business rules.
    """

    def __init__(self):
        """Initialize decision engine with scoring weights and thresholds"""
        print("Initializing Decision Engine...")

        # Module weights (must sum to 1.0)
        self.weights = {
            'liveness': 0.25,          # 25% - RBI mandatory
            'face_match': 0.25,        # 25% - RBI mandatory
            'script_compliance': 0.20, # 20% - Important for compliance
            'document_verification': 0.15,  # 15% - Document checks
            'behavior': 0.10,          # 10% - Suspicious behavior
            'consent': 0.05            # 5% - Consent verification
        }

        # Thresholds for decisions
        self.thresholds = {
            'pass': 75,      # Score >= 75 -> PASS
            'flag': 50,      # Score 50-74 -> FLAG
            'reject': 50     # Score < 50 -> REJECT
        }

        # Instant reject conditions (bypass scoring)
        self.instant_reject_rules = [
            'liveness_failed',
            'face_mismatch',
            'no_consent',
            'not_in_india',
            'not_independent',
            'aadhaar_not_masked',
            'critical_behavior_flag'
        ]

        # Instant flag conditions
        self.instant_flag_rules = [
            'high_behavior_risk',
            'multiple_hesitations',
            'script_incomplete'
        ]

        print(f"  Weights: {self.weights}")
        print(f"  Pass threshold: {self.thresholds['pass']}")
        print("  Decision engine initialized")

    def calculate_weighted_score(self, module_scores):
        """
        Calculate weighted average score from all modules

        Args:
            module_scores: Dictionary of module name -> score (0-100)

        Returns:
            Weighted average score
        """
        total_score = 0
        total_weight = 0

        for module, weight in self.weights.items():
            if module in module_scores:
                score = module_scores[module]
                if score is not None:
                    total_score += score * weight
                    total_weight += weight

        # Normalize if not all modules present
        if total_weight > 0 and total_weight < 1:
            total_score = total_score / total_weight

        return round(total_score, 2)

    def check_instant_conditions(self, module_results):
        """
        Check for conditions that trigger instant REJECT or FLAG

        Args:
            module_results: Full results from all modules

        Returns:
            Tuple of (decision_override, reasons)
        """
        instant_reject_reasons = []
        instant_flag_reasons = []

        # Check liveness
        liveness = module_results.get('liveness', {})
        if liveness.get('liveness_score', 100) < 50:
            instant_reject_reasons.append('Liveness check failed - possible replay attack')
        if not liveness.get('is_live', True):
            instant_reject_reasons.append('Video is not live')

        # Check face match
        face_match = module_results.get('face_match', {})
        if face_match.get('score', 100) < 50:
            instant_reject_reasons.append('Face does not match document')
        if face_match.get('confidence', 'HIGH') == 'LOW':
            instant_flag_reasons.append('Low confidence in face match')

        # Check script compliance for critical items
        script = module_results.get('script_compliance', {})
        if script.get('script_compliance', {}).get('critical_failures', 0) > 0:
            missing = script.get('script_compliance', {}).get('missing_critical', [])
            for item in missing:
                if 'india' in item.get('expected_text', '').lower():
                    instant_reject_reasons.append('Customer not confirmed in India')
                if 'independent' in item.get('expected_text', '').lower():
                    instant_reject_reasons.append('Customer not attending independently')

        # Check behavior
        behavior = module_results.get('behavior', {})
        if behavior.get('risk_level', 'LOW') == 'HIGH':
            instant_flag_reasons.append('High risk behavior detected')
        if len(behavior.get('behavior_analysis', {}).get('critical_flags', [])) > 0:
            instant_reject_reasons.append('Critical suspicious behavior detected')

        # Determine override
        if instant_reject_reasons:
            return Decision.REJECT, instant_reject_reasons
        elif instant_flag_reasons:
            return Decision.FLAG, instant_flag_reasons
        else:
            return None, []

    def make_decision(self, module_results):
        """
        Make final KYC decision based on all module results

        Args:
            module_results: Dictionary containing results from all modules
                Expected keys: liveness, face_match, script_compliance,
                              document_verification, behavior, consent

        Returns:
            Decision dictionary with verdict and details
        """
        print(f"\n{'='*60}")
        print("DECISION ENGINE")
        print(f"{'='*60}")

        # Extract scores from module results
        module_scores = {
            'liveness': module_results.get('liveness', {}).get('liveness_score', 0),
            'face_match': module_results.get('face_match', {}).get('score', 0),
            'script_compliance': module_results.get('script_compliance', {}).get('score', 0),
            'document_verification': module_results.get('document_verification', {}).get('score', 50),
            'behavior': module_results.get('behavior', {}).get('score', 100),
            'consent': module_results.get('consent', {}).get('score', 100)
        }

        print("Module Scores:")
        for module, score in module_scores.items():
            weight = self.weights.get(module, 0) * 100
            print(f"  {module}: {score}/100 (weight: {weight}%)")

        # Calculate weighted score
        final_score = self.calculate_weighted_score(module_scores)
        print(f"\nWeighted Score: {final_score}/100")

        # Check instant conditions first
        override_decision, override_reasons = self.check_instant_conditions(module_results)

        if override_decision:
            decision = override_decision
            decision_reason = override_reasons[0] if override_reasons else "Automatic trigger"
            print(f"\nWARNING:  Instant {decision.value} triggered!")
            for reason in override_reasons:
                print(f"   - {reason}")
        else:
            # Apply threshold-based decision
            if final_score >= self.thresholds['pass']:
                decision = Decision.PASS
                decision_reason = "All checks passed with sufficient score"
            elif final_score >= self.thresholds['flag']:
                decision = Decision.FLAG
                decision_reason = "Score below pass threshold, requires manual review"
            else:
                decision = Decision.REJECT
                decision_reason = "Score too low, verification failed"

        # Build result
        result = {
            'decision': decision.value,
            'final_score': final_score,
            'decision_reason': decision_reason,
            'override_applied': override_decision is not None,
            'override_reasons': override_reasons if override_decision else [],
            'module_scores': module_scores,
            'module_passed': {
                module: score >= 60
                for module, score in module_scores.items()
            },
            'thresholds': self.thresholds,
            'weights': self.weights,
            'timestamp': datetime.now().isoformat(),
            'recommendations': self._generate_recommendations(module_scores, module_results)
        }

        # Print final decision
        self._print_decision(result)

        return result

    def _generate_recommendations(self, module_scores, module_results):
        """Generate recommendations based on results"""
        recommendations = []

        # Check each module for issues
        if module_scores.get('liveness', 0) < 60:
            recommendations.append({
                'module': 'liveness',
                'issue': 'Low liveness score',
                'recommendation': 'Verify video is not a replay. Check for natural blinks and movements.'
            })

        if module_scores.get('face_match', 0) < 60:
            recommendations.append({
                'module': 'face_match',
                'issue': 'Face match failed',
                'recommendation': 'Manually verify face against document. Consider re-recording with better lighting.'
            })

        if module_scores.get('script_compliance', 0) < 60:
            recommendations.append({
                'module': 'script_compliance',
                'issue': 'Script not followed completely',
                'recommendation': 'Review transcript for missing mandatory questions.'
            })

        if module_scores.get('behavior', 0) < 60:
            recommendations.append({
                'module': 'behavior',
                'issue': 'Suspicious behavior detected',
                'recommendation': 'Review flagged segments for evasion or resistance patterns.'
            })

        # Add module-specific recommendations
        behavior_results = module_results.get('behavior', {})
        if behavior_results.get('risk_level') == 'HIGH':
            critical_flags = behavior_results.get('behavior_analysis', {}).get('critical_flags', [])
            if critical_flags:
                recommendations.append({
                    'module': 'behavior',
                    'issue': f'{len(critical_flags)} critical flags detected',
                    'recommendation': 'Manual review required. Check for third-party involvement or fraud indicators.'
                })

        return recommendations

    def _print_decision(self, result):
        """Print final decision"""
        decision = result['decision']

        # Color coding for terminal (if supported)
        if decision == 'PASS':
            status = '[PASS] APPROVED'
        elif decision == 'FLAG':
            status = 'WARNING:  FLAGGED FOR REVIEW'
        else:
            status = '[REJECT] REJECTED'

        print(f"\n{'='*60}")
        print(f"FINAL DECISION: {status}")
        print(f"{'='*60}")
        print(f"Score: {result['final_score']}/100")
        print(f"Reason: {result['decision_reason']}")

        if result['recommendations']:
            print(f"\nRecommendations:")
            for rec in result['recommendations'][:3]:
                print(f"  - [{rec['module']}] {rec['recommendation']}")

        print(f"{'='*60}\n")

    def save_decision(self, result, output_path):
        """Save decision to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Decision saved to: {output_path}")


def make_kyc_decision(module_results, output_dir=None):
    """
    Convenience function to make KYC decision

    Args:
        module_results: Results from all analysis modules
        output_dir: Optional directory to save decision

    Returns:
        Decision result
    """
    engine = DecisionEngine()
    result = engine.make_decision(module_results)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(output_dir, f'decision_{timestamp}.json')
        engine.save_decision(result, output_path)

    return result


if __name__ == '__main__':
    # Test with sample data
    sample_results = {
        'liveness': {'liveness_score': 85, 'is_live': True},
        'face_match': {'score': 78, 'confidence': 'MEDIUM'},
        'script_compliance': {'score': 90, 'script_compliance': {'critical_failures': 0}},
        'document_verification': {'score': 85},
        'behavior': {'score': 95, 'risk_level': 'LOW', 'behavior_analysis': {'critical_flags': []}},
        'consent': {'score': 100}
    }

    result = make_kyc_decision(sample_results, 'outputs/decisions')
    print(f"\nTest Decision: {result['decision']}")
