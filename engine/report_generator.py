"""
Report Generator
Creates comprehensive KYC verification reports
"""

import os
import json
from datetime import datetime


class ReportGenerator:
    """
    Generates detailed KYC verification reports.
    Supports JSON and HTML formats.
    """

    def __init__(self):
        """Initialize report generator"""
        print("Initializing Report Generator...")

    def generate_report(self, video_path, decision_result, module_results, preprocessing_results=None):
        """
        Generate comprehensive KYC report

        Args:
            video_path: Path to analyzed video
            decision_result: Result from decision engine
            module_results: Results from all analysis modules
            preprocessing_results: Optional preprocessing info

        Returns:
            Report dictionary
        """
        report = {
            'report_id': datetime.now().strftime('%Y%m%d%H%M%S'),
            'generated_at': datetime.now().isoformat(),
            'video_file': os.path.basename(video_path),
            'video_path': video_path,

            # Executive Summary
            'summary': {
                'decision': decision_result.get('decision', 'UNKNOWN'),
                'final_score': decision_result.get('final_score', 0),
                'confidence': self._get_confidence_level(decision_result.get('final_score', 0)),
                'recommendation': decision_result.get('decision_reason', '')
            },

            # Video Metadata
            'video_metadata': preprocessing_results.get('video_metadata', {}) if preprocessing_results else {},

            # Module Scores
            'module_scores': decision_result.get('module_scores', {}),
            'module_passed': decision_result.get('module_passed', {}),

            # Detailed Results
            'detailed_results': {
                'liveness': self._summarize_liveness(module_results.get('liveness', {})),
                'face_match': self._summarize_face_match(module_results.get('face_match', {})),
                'script_compliance': self._summarize_script(module_results.get('script_compliance', {})),
                'behavior': self._summarize_behavior(module_results.get('behavior', {}))
            },

            # Red Flags
            'red_flags': self._collect_red_flags(module_results, decision_result),

            # Recommendations
            'recommendations': decision_result.get('recommendations', []),

            # Audit Trail
            'audit_trail': {
                'analysis_timestamp': datetime.now().isoformat(),
                'modules_executed': list(module_results.keys()),
                'processing_time': preprocessing_results.get('processing_time', 0) if preprocessing_results else 0
            }
        }

        return report

    def _get_confidence_level(self, score):
        """Convert score to confidence level"""
        if score >= 85:
            return 'HIGH'
        elif score >= 70:
            return 'MEDIUM'
        elif score >= 50:
            return 'LOW'
        else:
            return 'VERY LOW'

    def _summarize_liveness(self, liveness_result):
        """Summarize liveness results"""
        if not liveness_result:
            return {'status': 'NOT_ANALYZED'}

        detailed = liveness_result.get('detailed_results', {})

        return {
            'score': liveness_result.get('liveness_score', 0),
            'is_live': liveness_result.get('is_live', False),
            'confidence': liveness_result.get('confidence', 'UNKNOWN'),
            'checks': {
                'blink_detection': detailed.get('blink_analysis', {}).get('liveness_indicator', False),
                'head_movement': detailed.get('movement_analysis', {}).get('liveness_indicator', False),
                'screen_replay': not detailed.get('screen_replay_analysis', {}).get('screen_replay_detected', True),
                'texture_analysis': detailed.get('texture_analysis', {}).get('liveness_indicator', False)
            }
        }

    def _summarize_face_match(self, face_result):
        """Summarize face match results"""
        if not face_result:
            return {'status': 'NOT_ANALYZED'}

        return {
            'score': face_result.get('score', 0),
            'passed': face_result.get('passed', False),
            'confidence': face_result.get('confidence', 'UNKNOWN'),
            'max_similarity': face_result.get('max_similarity', 0),
            'verification_rate': face_result.get('details', {}).get('verification_rate', 0)
        }

    def _summarize_script(self, script_result):
        """Summarize script compliance results"""
        if not script_result:
            return {'status': 'NOT_ANALYZED'}

        script_compliance = script_result.get('script_compliance', {})

        return {
            'score': script_result.get('score', 0),
            'is_compliant': script_compliance.get('is_compliant', False),
            'checks_passed': script_compliance.get('passed_checks', 0),
            'checks_total': script_compliance.get('total_checks', 0),
            'critical_failures': script_compliance.get('critical_failures', 0),
            'sections_covered': script_compliance.get('sections_covered', [])
        }

    def _summarize_behavior(self, behavior_result):
        """Summarize behavior analysis results"""
        if not behavior_result:
            return {'status': 'NOT_ANALYZED'}

        behavior_analysis = behavior_result.get('behavior_analysis', {})

        return {
            'score': behavior_result.get('score', 0),
            'risk_level': behavior_result.get('risk_level', 'UNKNOWN'),
            'total_flags': behavior_analysis.get('total_flags', 0),
            'critical_flags': len(behavior_analysis.get('critical_flags', [])),
            'categories': behavior_analysis.get('category_counts', {})
        }

    def _collect_red_flags(self, module_results, decision_result):
        """Collect all red flags from analysis"""
        red_flags = []

        # From decision engine overrides
        for reason in decision_result.get('override_reasons', []):
            red_flags.append({
                'source': 'decision_engine',
                'severity': 'CRITICAL',
                'description': reason
            })

        # From liveness
        liveness = module_results.get('liveness', {})
        if not liveness.get('is_live', True):
            red_flags.append({
                'source': 'liveness',
                'severity': 'CRITICAL',
                'description': 'Video may not be live - possible replay attack'
            })

        detailed = liveness.get('detailed_results', {})
        if detailed.get('screen_replay_analysis', {}).get('screen_replay_detected', False):
            red_flags.append({
                'source': 'liveness',
                'severity': 'CRITICAL',
                'description': 'Screen replay attack detected'
            })

        # From face match
        face_match = module_results.get('face_match', {})
        if face_match.get('score', 100) < 50:
            red_flags.append({
                'source': 'face_match',
                'severity': 'CRITICAL',
                'description': f"Face match score too low: {face_match.get('score', 0)}%"
            })

        # From behavior
        behavior = module_results.get('behavior', {})
        behavior_analysis = behavior.get('behavior_analysis', {})
        for flag in behavior_analysis.get('critical_flags', [])[:5]:
            red_flags.append({
                'source': 'behavior',
                'severity': 'HIGH',
                'description': f"Suspicious statement: {flag.get('text', '')[:100]}",
                'timestamp': flag.get('timestamp_formatted', '')
            })

        # From script compliance
        script = module_results.get('script_compliance', {})
        script_compliance = script.get('script_compliance', {})
        for item in script_compliance.get('missing_critical', []):
            red_flags.append({
                'source': 'script_compliance',
                'severity': 'HIGH',
                'description': f"Missing critical check: {item.get('expected_text', '')[:50]}"
            })

        return red_flags

    def save_json_report(self, report, output_path):
        """Save report as JSON"""
        import numpy as np

        def convert_types(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_types(i) for i in obj]
            elif isinstance(obj, set):
                return list(obj)
            return obj

        clean_report = convert_types(report)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(clean_report, f, indent=2, ensure_ascii=False)
        print(f"JSON report saved to: {output_path}")

    def save_html_report(self, report, output_path):
        """Save report as HTML"""
        html = self._generate_html(report)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"HTML report saved to: {output_path}")

    def _generate_html(self, report):
        """Generate HTML report"""
        decision = report['summary']['decision']
        decision_color = {
            'PASS': '#28a745',
            'FLAG': '#ffc107',
            'REJECT': '#dc3545'
        }.get(decision, '#6c757d')

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video KYC Report - {report['report_id']}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
        header h1 {{ font-size: 1.8em; margin-bottom: 10px; }}
        .content {{ padding: 30px; }}
        .decision-box {{ text-align: center; padding: 30px; margin: 20px 0; border-radius: 10px; background: {decision_color}22; border: 2px solid {decision_color}; }}
        .decision-box h2 {{ color: {decision_color}; font-size: 2em; }}
        .decision-box .score {{ font-size: 3em; color: {decision_color}; margin: 10px 0; }}
        .section {{ margin: 30px 0; }}
        .section h3 {{ color: #667eea; border-bottom: 2px solid #667eea; padding-bottom: 10px; margin-bottom: 15px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .card {{ background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #667eea; }}
        .card h4 {{ color: #333; margin-bottom: 8px; }}
        .card .value {{ font-size: 1.5em; color: #667eea; }}
        .card.pass {{ border-color: #28a745; }}
        .card.pass .value {{ color: #28a745; }}
        .card.fail {{ border-color: #dc3545; }}
        .card.fail .value {{ color: #dc3545; }}
        .red-flags {{ background: #fff3cd; padding: 20px; border-radius: 8px; border-left: 4px solid #ffc107; }}
        .red-flag-item {{ padding: 10px; margin: 10px 0; background: white; border-radius: 5px; border-left: 3px solid #dc3545; }}
        .recommendations {{ background: #d1ecf1; padding: 20px; border-radius: 8px; }}
        .recommendations li {{ margin: 10px 0; padding: 10px; background: white; border-radius: 5px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #667eea; color: white; }}
        footer {{ text-align: center; padding: 20px; color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Video KYC Verification Report</h1>
            <p>Report ID: {report['report_id']}</p>
            <p>Generated: {report['generated_at']}</p>
        </header>

        <div class="content">
            <div class="decision-box">
                <h2>DECISION: {decision}</h2>
                <div class="score">{report['summary']['final_score']}/100</div>
                <p>Confidence: {report['summary']['confidence']}</p>
                <p>{report['summary']['recommendation']}</p>
            </div>

            <div class="section">
                <h3>Video Information</h3>
                <div class="grid">
                    <div class="card">
                        <h4>File</h4>
                        <p>{report['video_file']}</p>
                    </div>
                    <div class="card">
                        <h4>Duration</h4>
                        <p>{report['video_metadata'].get('duration_formatted', 'N/A')}</p>
                    </div>
                    <div class="card">
                        <h4>Resolution</h4>
                        <p>{report['video_metadata'].get('resolution', 'N/A')}</p>
                    </div>
                </div>
            </div>

            <div class="section">
                <h3>Module Scores</h3>
                <div class="grid">
                    {self._generate_module_cards(report['module_scores'], report['module_passed'])}
                </div>
            </div>

            <div class="section">
                <h3>Detailed Analysis</h3>
                <table>
                    <tr><th>Check</th><th>Status</th><th>Details</th></tr>
                    {self._generate_analysis_rows(report['detailed_results'])}
                </table>
            </div>

            {self._generate_red_flags_section(report['red_flags'])}

            {self._generate_recommendations_section(report['recommendations'])}
        </div>

        <footer>
            <p>Video KYC AI Checker - Automated Verification Report</p>
            <p>This report is generated automatically and may require manual review.</p>
        </footer>
    </div>
</body>
</html>"""
        return html

    def _generate_module_cards(self, scores, passed):
        """Generate HTML cards for each module"""
        cards = []
        for module, score in scores.items():
            status_class = 'pass' if passed.get(module, False) else 'fail'
            module_name = module.replace('_', ' ').title()
            cards.append(f'''
                <div class="card {status_class}">
                    <h4>{module_name}</h4>
                    <div class="value">{score}/100</div>
                    <p>{"PASSED" if passed.get(module, False) else "FAILED"}</p>
                </div>
            ''')
        return '\n'.join(cards)

    def _generate_analysis_rows(self, detailed):
        """Generate table rows for detailed analysis"""
        rows = []

        # Liveness
        liveness = detailed.get('liveness', {})
        if liveness.get('status') != 'NOT_ANALYZED':
            rows.append(f'''
                <tr>
                    <td>Liveness Detection</td>
                    <td>{"[PASS] PASS" if liveness.get('is_live', False) else "[FAIL] FAIL"}</td>
                    <td>Score: {liveness.get('score', 0)}, Confidence: {liveness.get('confidence', 'N/A')}</td>
                </tr>
            ''')

        # Face Match
        face = detailed.get('face_match', {})
        if face.get('status') != 'NOT_ANALYZED':
            rows.append(f'''
                <tr>
                    <td>Face Match</td>
                    <td>{"[PASS] PASS" if face.get('passed', False) else "[FAIL] FAIL"}</td>
                    <td>Score: {face.get('score', 0)}, Max Similarity: {face.get('max_similarity', 0):.1f}%</td>
                </tr>
            ''')

        # Script Compliance
        script = detailed.get('script_compliance', {})
        if script.get('status') != 'NOT_ANALYZED':
            rows.append(f'''
                <tr>
                    <td>Script Compliance</td>
                    <td>{"[PASS] PASS" if script.get('is_compliant', False) else "[FAIL] FAIL"}</td>
                    <td>Checks: {script.get('checks_passed', 0)}/{script.get('checks_total', 0)}, Critical Failures: {script.get('critical_failures', 0)}</td>
                </tr>
            ''')

        # Behavior
        behavior = detailed.get('behavior', {})
        if behavior.get('status') != 'NOT_ANALYZED':
            rows.append(f'''
                <tr>
                    <td>Behavior Analysis</td>
                    <td>Risk: {behavior.get('risk_level', 'N/A')}</td>
                    <td>Score: {behavior.get('score', 0)}, Flags: {behavior.get('total_flags', 0)}</td>
                </tr>
            ''')

        return '\n'.join(rows)

    def _generate_red_flags_section(self, red_flags):
        """Generate red flags HTML section"""
        if not red_flags:
            return ''

        flags_html = '\n'.join([
            f'''<div class="red-flag-item">
                <strong>[{flag.get('severity', 'INFO')}]</strong> {flag.get('description', '')}
                {f"<br><small>Timestamp: {flag.get('timestamp', '')}</small>" if flag.get('timestamp') else ''}
            </div>'''
            for flag in red_flags
        ])

        return f'''
            <div class="section">
                <h3>Red Flags ({len(red_flags)})</h3>
                <div class="red-flags">
                    {flags_html}
                </div>
            </div>
        '''

    def _generate_recommendations_section(self, recommendations):
        """Generate recommendations HTML section"""
        if not recommendations:
            return ''

        recs_html = '\n'.join([
            f'''<li><strong>[{rec.get('module', 'General')}]</strong> {rec.get('recommendation', '')}</li>'''
            for rec in recommendations
        ])

        return f'''
            <div class="section">
                <h3>Recommendations</h3>
                <div class="recommendations">
                    <ul>{recs_html}</ul>
                </div>
            </div>
        '''


def generate_report(video_path, decision_result, module_results, preprocessing_results=None, output_dir=None):
    """
    Convenience function to generate report

    Args:
        video_path: Path to analyzed video
        decision_result: Decision engine result
        module_results: All module results
        preprocessing_results: Optional preprocessing info
        output_dir: Optional output directory

    Returns:
        Report dictionary
    """
    generator = ReportGenerator()
    report = generator.generate_report(video_path, decision_result, module_results, preprocessing_results)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save JSON
        json_path = os.path.join(output_dir, f'kyc_report_{timestamp}.json')
        generator.save_json_report(report, json_path)

        # Save HTML
        html_path = os.path.join(output_dir, f'kyc_report_{timestamp}.html')
        generator.save_html_report(report, html_path)

    return report
