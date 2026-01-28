import os
import json
import logging
from typing import List, Dict, Any
import requests
from flask import current_app
from app.models import get_setting

logger = logging.getLogger(__name__)

class GeminiService:
    """Service to interact with Google Gemini (gemini-2.0-flash) for fast single-request analysis."""

    def __init__(self):
        self.api_key = get_setting('GOOGLE_API_KEY', os.environ.get('GOOGLE_API_KEY'))
        if not self.api_key:
            raise ValueError('GOOGLE_API_KEY not configured')
        # Model name (allow override via settings later if needed)
        self.model = current_app.config.get('GEMINI_MODEL', 'gemini-2.0-flash')
        # Endpoint
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        # Timeouts
        self.timeout = current_app.config.get('ANALYSIS_TIMEOUT', 300)

    def analyze_social_media_posts(self, posts: List[Dict], employee_info: Dict, selected_checks: List[str] = None) -> Dict[str, Any]:
        prompt = self._build_deep_analysis_prompt(posts, employee_info)
        response_text = self._generate_response(prompt)
        # Try to parse JSON from Gemini response
        try:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start != -1 and end > start:
                json_text = response_text[start:end]
                data = json.loads(json_text)
                return self._normalize_result(data, len(posts))
        except Exception as e:
            logger.error(f"Gemini parse error: {e}")
            logger.error(f"Raw Gemini response (truncated): {response_text[:300]}...")
        # Fallback
        return {
            'risk_score': None,
            'character_assessment': 'Analysis could not parse JSON response from Gemini.',
            'behavioral_insights': '',
            'red_flags': [],
            'positive_indicators': [],
            'confidence_score': 0.0,
            'summary': 'Unstructured analysis response received.',
            'posts_analyzed': len(posts),
            'analysis_model': self.model,
            'raw_response': response_text,
        }

    def _build_single_prompt(self, posts: List[Dict], employee_info: Dict, selected_checks: List[str] = None) -> str:
        all_sections = ['risk','character','behavior','redflags','positive','assessments']
        checks = [c for c in (selected_checks or []) if c in all_sections]
        if not checks:
            checks = all_sections

        extra = get_setting('PROMPT_EXTRA_INSTRUCTIONS', '') or ''
        ov = {
            'risk': get_setting('PROMPT_RISK', '') or '',
            'character': get_setting('PROMPT_CHARACTER', '') or '',
            'behavior': get_setting('PROMPT_BEHAVIOR', '') or '',
            'redflags': get_setting('PROMPT_REDFLAGS', '') or '',
            'positive': get_setting('PROMPT_POSITIVE', '') or '',
            'assessments': get_setting('PROMPT_ASSESSMENTS', '') or '',
        }

        default_dims = [
            'political_orientation',
            'religious_orientation',
            'violence_tendency',
            'political_or_religious_affiliation',
            'suitability_for_sensitive_positions',
        ]
        try:
            dims_setting = get_setting('ASSESSMENT_DIMENSIONS', None)
            selected_dims = json.loads(dims_setting) if dims_setting else default_dims
        except Exception:
            selected_dims = default_dims

        posts_text = ''
        for i, post in enumerate(posts[:60], 1):
            platform = post.get('platform', 'unknown')
            text = post.get('text', '')
            created_at = post.get('created_at', 'unknown')
            posts_text += f"\n--- Post {i} ({platform}) ---\n"
            posts_text += f"Date: {created_at}\n"
            posts_text += f"Content: {text}\n"

        sections_text = []
        if 'risk' in checks:
            sections_text.append("1. RISK ASSESSMENT: Provide a 0-100 score with concise reasoning and citations. " + ov['risk'])
        if 'character' in checks:
            sections_text.append("2. CHARACTER ASSESSMENT: Personality traits, values, patterns; include reasoning & citations. " + ov['character'])
        if 'behavior' in checks:
            sections_text.append("3. BEHAVIORAL INSIGHTS: Communication patterns and concerning behaviors; include reasoning & citations. " + ov['behavior'])
        if 'redflags' in checks:
            sections_text.append("4. RED FLAGS: List items with reason and citation. " + ov['redflags'])
        if 'positive' in checks:
            sections_text.append("5. POSITIVE INDICATORS: List items with reason and citation. " + ov['positive'])
        if 'assessments' in checks:
            bullet_dims = "\n".join([f"   - {k.replace('_',' ')}" for k in selected_dims])
            sections_text.append("6. SPECIFIC ASSESSMENTS: For each dimension, add justification and citation(s):\n" + bullet_dims + "\n" + ov['assessments'])

        sections_block = "\n\n".join(sections_text)

        prompt = f"""
You are an AI analyst. Handle Arabic and English. Use exact quotes; do not fabricate. Avoid speculation beyond evidence.

EMPLOYEE INFORMATION:
- Employee ID: {employee_info.get('employee_id', 'N/A')}
- Name: {employee_info.get('full_name', 'N/A')}
- Department: {employee_info.get('department', 'N/A')}
- Position: {employee_info.get('position', 'N/A')}

SOCIAL MEDIA POSTS:
{posts_text}

ANALYSIS REQUIREMENTS:
{sections_block}

EXTRA INSTRUCTIONS (admin): {extra}

Return ONLY JSON:
{{
  "risk_score": <number 0-100>,
  "character_assessment": "<text>",
  "behavioral_insights": "<text>",
  "red_flags": ["<item (reason, citation)>", "..."],
  "positive_indicators": ["<item (reason, citation)>", "..."],
  "confidence_score": <number 0-100>,
  "summary": "<brief summary>",
  "assessments": {{
    "political_orientation": "<summary or 'unknown'>",
    "religious_orientation": "<summary or 'unknown'>",
    "violence_tendency": "<summary or 'unknown'>",
    "political_or_religious_affiliation": "<summary or 'unknown'>",
    "suitability_for_sensitive_positions": "<yes/no with justification or 'unknown'>",
    "discrimination_or_bias": "<summary or 'unknown'>",
    "personal_issues_shared": "<summary or 'unknown'>"
  }}
}}
"""
        return prompt

    def _build_deep_analysis_prompt(self, posts: List[Dict], employee_info: Dict) -> str:
        """Build enhanced deep analysis prompt for comprehensive psychological profiling."""
        
        # Prepare posts with metadata
        posts_text = ""
        for i, post in enumerate(posts[:50], 1):
            platform = post.get('platform', 'unknown')
            text = post.get('text', '')
            created_at = post.get('created_at', 'unknown')
            engagement = post.get('likes', 0) + post.get('comments', 0) + post.get('shares', 0)
            
            posts_text += f"\n--- Post {i} ({platform}) ---\n"
            posts_text += f"Timestamp: {created_at}\n"
            posts_text += f"Engagement: {engagement} interactions\n"
            posts_text += f"Content: {text}\n"
        
        prompt = f'''
You are a forensic behavioral psychologist and OSINT analyst specializing in deep personality assessment through digital footprints. Your analysis combines psycholinguistic profiling, behavioral pattern recognition, network analysis, and threat assessment methodologies used by intelligence agencies.

SUBJECT PROFILE:
- Employee ID: {employee_info.get('employee_id', 'N/A')}
- Name: {employee_info.get('full_name', 'N/A')}
- Department: {employee_info.get('department', 'N/A')}
- Position: {employee_info.get('position', 'N/A')}

SOCIAL MEDIA CORPUS:
{posts_text}

ANALYTICAL FRAMEWORK:

You must perform a multi-layered forensic analysis examining the following dimensions. For EVERY assertion, provide specific evidence with exact citations [Post X - date: "quoted text"] and analytical reasoning explaining the psychological or behavioral significance.

1. PSYCHOLINGUISTIC PROFILE (Advanced Text Analysis)
   Analyze the subject's communication patterns at a deep level:
   
   a) Cognitive Patterns:
      - Thinking style: Abstract vs. concrete reasoning tendencies
      - Complexity of thought: Vocabulary sophistication, sentence structure patterns
      - Cognitive biases: Confirmation bias, attribution errors, binary thinking
      - Analytical vs. emotional reasoning balance
      - Evidence of critical thinking or susceptibility to misinformation
   
   b) Emotional Landscape:
      - Baseline emotional state across timeline
      - Emotional volatility: Frequency and intensity of mood shifts
      - Affective vocabulary: Range and depth of emotional expression
      - Emotional regulation capabilities
      - Triggers: Recurring themes that elicit strong reactions
      - Ratio of positive/negative/neutral affect
   
   c) Linguistic Markers:
      - Use of absolutes ("always," "never") indicating rigid thinking
      - Personal pronouns analysis (I vs. we - individualism vs. collectivism)
      - Temporal orientation (past/present/future focus)
      - Certainty vs. hedging language
      - Power dynamics in language (dominant/submissive patterns)
      - Code-switching between formal/informal registers

2. BEHAVIORAL PATTERN MATRIX
   Map observable behavior patterns over time:
   
   a) Posting Behavior Analytics:
      - Temporal patterns: Peak activity times, frequency changes
      - Content evolution: Thematic shifts over time
      - Consistency vs. volatility in posting behavior
      - Impulsivity markers: Evidence of unfiltered or reactive posting
      - Deletion patterns or content modification (if observable)
   
   b) Social Interaction Dynamics:
      - Conflict engagement: How does subject handle disagreement?
      - Social mimicry: Adoption of others' language/ideas
      - Boundary management: Professional vs. personal disclosure boundaries
      - Reciprocity patterns: Give vs. take in social exchanges
      - Social proof seeking: Validation-seeking behaviors
      - In-group/out-group dynamics: Tribal affiliations and hostility patterns
   
   c) Self-Presentation Strategy:
      - Authenticity vs. persona construction
      - Impression management tactics
      - Consistency between stated values and demonstrated behavior
      - Identity markers emphasized (professional, personal, ideological)
      - Narcissistic indicators: Self-promotion, grandiosity, attention-seeking

3. PSYCHOLOGICAL VULNERABILITY ASSESSMENT
   Identify potential exploitable weaknesses or concerning patterns:
   
   a) Stress Indicators:
      - Evidence of financial stress (job concerns, money complaints)
      - Relationship distress (family conflict, romantic issues)
      - Health concerns (physical or mental health mentions)
      - Occupational burnout signals
      - Substance use references (alcohol, drugs, medications)
   
   b) Personality Pathology Markers:
      - Narcissistic traits: Grandiosity, need for admiration, lack of empathy
      - Antisocial indicators: Rule-breaking pride, manipulation, aggression
      - Paranoid thinking: Excessive distrust, conspiracy theories
      - Impulsivity and poor judgment
      - Emotional instability or reactivity
   
   c) Exploitation Vulnerabilities:
      - Susceptibility to manipulation or social engineering
      - Ideological extremism receptivity
      - Authority compliance vs. defiance patterns
      - Peer pressure susceptibility
      - Financial desperation indicators
      - Loneliness or social isolation

4. IDEOLOGICAL & BELIEF SYSTEM MAPPING
   Deep dive into worldview and value structures:
   
   a) Core Value Architecture:
      - Moral foundations: Care, fairness, loyalty, authority, sanctity
      - Priority hierarchies: What matters most to this person?
      - Value conflicts or contradictions
      - Moral absolutism vs. relativism
   
   b) Ideological Positioning:
      - Political ideology: Specific positions on spectrum with nuance
      - Religious/spiritual framework: Depth of conviction, fundamentalism markers
      - Social justice orientation: Equity vs. hierarchy preference
      - Nationalism vs. globalism
      - Authoritarianism vs. libertarianism
      - Traditionalism vs. progressivism
   
   c) Radicalization Risk Indicators:
      - Grievance narratives: Perceived injustices or victimization
      - Enemy construction: Demonization of out-groups
      - Violence glorification or justification
      - Apocalyptic or millenarian thinking
      - Isolation from mainstream narratives
      - Engagement with extremist content or rhetoric
      - Trajectory analysis: Movement toward or away from extreme positions

5. THREAT SURFACE ANALYSIS
   Security-focused risk evaluation:
   
   a) Operational Security Failures:
      - Oversharing of sensitive information (location, schedule, access)
      - Relationship disclosures that create leverage points
      - Credential exposure or security hygiene issues
      - Awareness of surveillance or lack thereof
   
   b) Insider Threat Indicators:
      - Grievances against employer or government
      - Financial motivation markers
      - Ideological opposition to organizational mission
      - Access bragging or security policy complaints
      - Unexplained lifestyle changes
      - Foreign contact patterns (if observable)
   
   c) Compromise Susceptibility:
      - Blackmail vulnerability: Secrets, embarrassing content
      - Coercion points: Loved ones, debts, legal issues
      - Ideological recruitment vulnerability
      - Honey trap susceptibility markers

6. SOCIAL NETWORK ANALYSIS
   Examine relationships and influence patterns:
   
   a) Network Composition:
      - Diversity of connections: Echo chamber vs. heterogeneous network
      - Influential nodes: Who does the subject amplify or defer to?
      - Toxic associations: Extremist, criminal, or high-risk connections
      - Professional vs. personal network segregation
   
   b) Influence Vectors:
      - Information sources: Media diet quality and bias
      - Opinion leaders the subject follows
      - Susceptibility to viral misinformation
      - Information verification habits

7. TEMPORAL EVOLUTION & TRAJECTORY ANALYSIS
   Map changes over the observation period:
   
   a) Directional Trends:
      - Radicalization trajectory (toward or away from extremes)
      - Mental health trajectory (deteriorating or improving)
      - Professionalism trajectory
      - Stability trajectory (increasing chaos or order)
   
   b) Inflection Points:
      - Significant events that changed posting patterns
      - Crisis moments revealing character under stress
      - Recovery patterns from setbacks

8. DECEPTION & AUTHENTICITY INDICATORS
   Assess truthfulness and consistency:
   
   a) Consistency Analysis:
      - Internal contradictions in stated beliefs
      - Behavior vs. stated values discrepancies
      - Timeline inconsistencies
   
   b) Deception Markers:
      - Linguistic indicators of deception (hedging, vagueness)
      - Defensive reactions to questions
      - Exaggeration or embellishment patterns
      - Selective truth-telling

9. PROTECTIVE FACTORS & POSITIVE INDICATORS
   Balance the assessment with strengths:
   
   a) Resilience Markers:
      - Healthy coping mechanisms
      - Strong social support evidence
      - Growth mindset indicators
      - Adversity recovery patterns
   
   b) Prosocial Behaviors:
      - Empathy demonstrations
      - Community contribution
      - Helping behaviors
      - Civic engagement
      - Ethical reasoning displays

10. PREDICTIVE RISK MODELING
    Synthesize findings into forward-looking assessment:
    
    a) Probability Estimates:
       - Likelihood of policy violations
       - Insider threat probability
       - Radicalization risk
       - Compromise susceptibility
       - Crisis event likelihood
    
    b) Behavioral Predictions:
       - Expected behavior under stress
       - Loyalty under pressure
       - Ethical decision-making in gray areas
       - Response to authority challenges

CRITICAL ANALYSIS REQUIREMENTS:

1. EVIDENCE STANDARD: Every claim must be supported by:
   - Direct quote: [Post X - date: "exact text"]
   - Contextual analysis: Why this matters psychologically/behaviorally
   - Pattern evidence: Is this isolated or recurring? (cite multiple instances)

2. NUANCE & DEPTH: Avoid surface-level observations. Explain:
   - The psychological mechanisms behind observed behaviors
   - Alternative interpretations of ambiguous data
   - Confidence levels for each assertion (high/medium/low)
   - Cultural context considerations (especially for Arabic content)

3. TEMPORAL AWARENESS: Note when patterns changed, emerged, or intensified

4. HOLISTIC INTEGRATION: Connect insights across dimensions to build a coherent psychological profile

5. ARABIC LANGUAGE HANDLING: 
   - Preserve original Arabic quotes with English translations
   - Account for cultural nuances in expression
   - Consider regional dialect implications
   - Recognize code-switching significance

6. COUNTERINDICATIONS: Actively look for evidence that contradicts initial hypotheses

OUTPUT FORMAT (JSON):
{{
    "risk_score": <0-100, with detailed justification>,
    "confidence_score": <0-100>,
    
    "psycholinguistic_profile": {{
        "cognitive_patterns": "<detailed analysis with citations>",
        "emotional_landscape": "<detailed analysis with citations>",
        "linguistic_markers": "<detailed analysis with citations>"
    }},
    
    "behavioral_matrix": {{
        "posting_behavior": "<detailed analysis with citations>",
        "social_dynamics": "<detailed analysis with citations>",
        "self_presentation": "<detailed analysis with citations>"
    }},
    
    "psychological_vulnerabilities": {{
        "stress_indicators": ["<specific vulnerability: evidence [Post X] reasoning>"],
        "personality_pathology": ["<specific indicator: evidence [Post X] reasoning>"],
        "exploitation_vectors": ["<specific vulnerability: evidence [Post X] reasoning>"]
    }},
    
    "ideological_mapping": {{
        "core_values": "<detailed analysis with citations>",
        "political_ideology": "<specific positioning with evidence>",
        "religious_framework": "<specific analysis with evidence>",
        "radicalization_indicators": ["<specific indicator: evidence [Post X] reasoning>"],
        "radicalization_trajectory": "<toward/away/stable with reasoning>"
    }},
    
    "threat_surface": {{
        "opsec_failures": ["<specific failure: evidence [Post X] impact assessment>"],
        "insider_threat_markers": ["<specific indicator: evidence [Post X] reasoning>"],
        "compromise_vectors": ["<specific vulnerability: evidence [Post X] reasoning>"]
    }},
    
    "social_network": {{
        "network_quality": "<assessment with evidence>",
        "toxic_associations": ["<specific association: evidence [Post X] risk level>"],
        "influence_sources": ["<source: evidence [Post X] impact assessment>"]
    }},
    
    "temporal_analysis": {{
        "trajectory_summary": "<overall direction with evidence>",
        "critical_inflection_points": ["<date/period: event, impact on behavior>"],
        "trend_analysis": "<improving/declining/stable with specifics>"
    }},
    
    "authenticity_assessment": {{
        "deception_indicators": ["<indicator: evidence [Post X] reasoning>"],
        "consistency_score": "<high/medium/low with analysis>",
        "authenticity_rating": "<assessment with evidence>"
    }},
    
    "protective_factors": {{
        "resilience_markers": ["<factor: evidence [Post X]>"],
        "prosocial_behaviors": ["<behavior: evidence [Post X]>"],
        "stability_anchors": ["<factor: evidence [Post X]>"]
    }},
    
    "predictive_assessment": {{
        "insider_threat_probability": "<percentage with reasoning>",
        "radicalization_risk": "<low/medium/high/critical with detailed reasoning>",
        "compromise_susceptibility": "<low/medium/high with specific vectors>",
        "crisis_likelihood": "<assessment with triggers>",
        "predicted_behaviors_under_stress": "<specific predictions with reasoning>"
    }},
    
    "red_flags": [
        "<HIGH PRIORITY flag: detailed evidence [Post X, Y, Z] + psychological significance + risk assessment>"
    ],
    
    "positive_indicators": [
        "<strength: detailed evidence [Post X, Y] + significance>"
    ],
    
    "executive_summary": "<2-3 paragraph synthesis of key findings, overall assessment, and primary recommendations>",
    
    "recommendations": [
        "<specific action: rationale>",
        "<monitoring focus: rationale>",
        "<mitigation strategy: rationale>"
    ],
    
    "analytical_gaps": [
        "<area where more data needed>",
        "<ambiguity requiring clarification>",
        "<contradiction requiring investigation>"
    ]
}}

ANALYTICAL STANCE:
- Maintain objectivity while being unflinchingly thorough
- Acknowledge uncertainty where evidence is ambiguous
- Distinguish between facts, inferences, and speculation
- Consider cultural and contextual factors
- Prioritize security-relevant findings without manufacturing threats
- Balance sensitivity to civil liberties with security imperatives
'''
        
        return prompt

    def _generate_response(self, prompt: str) -> str:
        # Log the full prompt payload for audit purposes
        logger.info(f"FULL PROMPT PAYLOAD (Gemini):\n{prompt}")

        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}
        # Ask for JSON output explicitly
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.9,
                "maxOutputTokens": 3072,
                "responseMimeType": "application/json"
            }
        }
        try:
            resp = requests.post(self.api_url, headers=headers, params=params, json=payload, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                # Newer API returns candidates with content.parts[0].text
                text = ''
                try:
                    candidates = data.get('candidates', [])
                    if candidates:
                        parts = candidates[0].get('content', {}).get('parts', [])
                        if parts:
                            text = parts[0].get('text', '')
                except Exception:
                    text = resp.text
                return text or resp.text
            else:
                raise Exception(f"Gemini API error: {resp.status_code} - {resp.text}")
        except requests.exceptions.Timeout:
            raise Exception(f"Gemini API timeout after {self.timeout} seconds")
        except Exception as e:
            raise Exception(f"Gemini API request failed: {str(e)}")

    def _normalize_result(self, data: Dict[str, Any], posts_count: int) -> Dict[str, Any]:
        result = {
            'risk_score': data.get('risk_score'),
            'character_assessment': data.get('character_assessment', ''),
            'behavioral_insights': data.get('behavioral_insights', ''),
            'red_flags': data.get('red_flags', []) or [],
            'positive_indicators': data.get('positive_indicators', []) or [],
            'confidence_score': data.get('confidence_score'),
            'summary': data.get('summary', '') or data.get('executive_summary', ''),
            'posts_analyzed': posts_count,
            'analysis_model': self.model,
            'raw_response': json.dumps(data)[:4000],
        }

        # --- Deep Analysis Field Mapping ---
        # Map complex nested JSON fields into the text columns if they exist
        
        # 1. Character Assessment Augmentation
        char_sections = []
        if result['character_assessment']:
            char_sections.append(result['character_assessment'])
        
        if data.get('psycholinguistic_profile'):
            pp = data['psycholinguistic_profile']
            char_sections.append("\n### Psycholinguistic Profile")
            for k, v in pp.items():
                char_sections.append(f"**{k.replace('_', ' ').title()}:** {v}")
        
        if data.get('ideological_mapping'):
            im = data['ideological_mapping']
            char_sections.append("\n### Ideological Mapping")
            for k, v in im.items():
                val = v if isinstance(v, str) else json.dumps(v)
                char_sections.append(f"**{k.replace('_', ' ').title()}:** {val}")

        if data.get('authenticity_assessment'):
            aa = data['authenticity_assessment']
            char_sections.append("\n### Authenticity Assessment")
            for k, v in aa.items():
                val = v if isinstance(v, str) else json.dumps(v)
                char_sections.append(f"**{k.replace('_', ' ').title()}:** {val}")

        result['character_assessment'] = "\n\n".join(char_sections)

        # 2. Behavioral Insights Augmentation
        beh_sections = []
        if result['behavioral_insights']:
            beh_sections.append(result['behavioral_insights'])

        # Behavioral Matrix
        if data.get('behavioral_matrix'):
            bm = data['behavioral_matrix']
            beh_sections.append("\n### Behavioral Matrix")
            for k, v in bm.items():
                beh_sections.append(f"**{k.replace('_', ' ').title()}:** {v}")

        # Psychological Vulnerabilities
        if data.get('psychological_vulnerabilities'):
            pv = data['psychological_vulnerabilities']
            beh_sections.append("\n### Psychological Vulnerabilities")
            for k, v in pv.items():
                val = ", ".join(v) if isinstance(v, list) else str(v)
                beh_sections.append(f"**{k.replace('_', ' ').title()}:** {val}")

        # Threat Surface
        if data.get('threat_surface'):
            ts = data['threat_surface']
            beh_sections.append("\n### Threat Surface")
            for k, v in ts.items():
                val = ", ".join(v) if isinstance(v, list) else str(v)
                beh_sections.append(f"**{k.replace('_', ' ').title()}:** {val}")

        # Social Network
        if data.get('social_network'):
            sn = data['social_network']
            beh_sections.append("\n### Social Network Analysis")
            for k, v in sn.items():
                val = ", ".join(v) if isinstance(v, list) else str(v)
                beh_sections.append(f"**{k.replace('_', ' ').title()}:** {val}")
        
        # Temporal Analysis
        if data.get('temporal_analysis'):
            ta = data['temporal_analysis']
            beh_sections.append("\n### Temporal Analysis")
            for k, v in ta.items():
                val = ", ".join(v) if isinstance(v, list) else str(v)
                beh_sections.append(f"**{k.replace('_', ' ').title()}:** {val}")

        # Protective Factors
        if data.get('protective_factors'):
            pf = data['protective_factors']
            beh_sections.append("\n### Protective Factors")
            for k, v in pf.items():
                val = ", ".join(v) if isinstance(v, list) else str(v)
                beh_sections.append(f"**{k.replace('_', ' ').title()}:** {val}")

        # Predictive Assessment
        if data.get('predictive_assessment'):
            pa = data['predictive_assessment']
            beh_sections.append("\n### Predictive Assessment")
            for k, v in pa.items():
                val = v if isinstance(v, str) else json.dumps(v)
                beh_sections.append(f"**{k.replace('_', ' ').title()}:** {val}")

        # Merge assessments into behavioral_insights for rendering in Specific Assessments panel
        assessments = data.get('assessments') or {}
        if isinstance(assessments, dict) and assessments:
            parts = []
            mapping = {
                'political_orientation': 'Political orientation',
                'religious_orientation': 'Religious orientation',
                'violence_tendency': 'Violence tendency',
                'political_or_religious_affiliation': 'Political/Religious affiliation',
                'suitability_for_sensitive_positions': 'Suitability for sensitive positions',
                'discrimination_or_bias': 'Bias against class/gender/color',
                'personal_issues_shared': 'Personal problems shared publicly',
            }
            for k, label in mapping.items():
                v = assessments.get(k)
                if v:
                    parts.append(f"{label}: {v}")
            if parts:
                joined = "\n".join(parts)
                beh_sections.append("\n### Specific Assessments\n" + joined)
        
        result['behavioral_insights'] = "\n\n".join(beh_sections)

        return result

    def test_connection(self) -> Dict[str, Any]:
        """Quick connectivity and permissions test for Gemini API."""
        try:
            prompt = "Respond with JSON: {\"ok\": true}"
            text = self._generate_response(prompt)
            if '"ok": true' in text:
                return {
                    'status': 'success',
                    'message': f'Gemini API is working with model "{self.model}"'
                }
            return {
                'status': 'warning',
                'message': 'Gemini API responded but JSON check did not match.'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Gemini API test failed: {str(e)}'
            }

    def analyze_comprehensive(self, posts, employee_info):
        """
        Orchestrate a multi-stage comprehensive analysis, yielding status updates.
        Generator that yields: ('status', 'message') or ('result', final_dict)
        """
        yield ('status', 'Initializing comprehensive forensic analysis protocol (Gemini)...')
        
        stages = [
            ('risk', 'Running Risk & Threat Assessment...'),
            ('psycholinguistic', 'Analyzing Psycholinguistic Profile...'),
            ('behavioral', 'Constructing Behavioral Matrix...'),
            ('ideological', 'Mapping Ideological Framework...')
        ]
        
        final_result = {
            'risk_score': 0,
            'confidence_score': 0,
            'red_flags': [],
            'positive_indicators': [],
            'character_assessment': '',
            'behavioral_insights': '',
            'summary': '',
            'raw_response': {},
            'posts_analyzed': len(posts),
            'analysis_model': self.model
        }
        
        def merge_list(target, source):
            existing = set(target)
            for item in source:
                if item not in existing:
                    target.append(item)
                    existing.add(item)

        aggregated_raw = {}

        for stage_name, status_msg in stages:
            yield ('status', status_msg)
            
            prompt = self._build_stage_prompt(stage_name, posts, employee_info)
            # Call Gemini (returns string)
            resp_text = self._generate_response(prompt)
            
            # Parse
            response_data = {}
            try:
                # Naive JSON extraction
                start = resp_text.find('{')
                end = resp_text.rfind('}') + 1
                if start != -1 and end > start:
                    response_data = json.loads(resp_text[start:end])
                else:
                    # Try direct load
                    response_data = json.loads(resp_text)
            except Exception as e:
                logger.error(f"Gemini parse error in stage {stage_name}: {e}")
                # We won't yield error to user, just skip data
            
            if not response_data:
                yield ('status', f'Warning: Stage {stage_name} yielded no valid JSON.')
                aggregated_raw[stage_name] = {"error": "Invalid JSON", "raw": resp_text}
                continue
                
            aggregated_raw[stage_name] = response_data
            
            # --- Merge Logic (Similar to OpenAI) ---
            if stage_name == 'risk':
                final_result['risk_score'] = response_data.get('risk_score', 0)
                final_result['confidence_score'] = response_data.get('confidence_score', 0)
                merge_list(final_result['red_flags'], response_data.get('red_flags', []))
                merge_list(final_result['positive_indicators'], response_data.get('positive_indicators', []))
                final_result['summary'] = response_data.get('executive_summary', '')

            elif stage_name == 'psycholinguistic':
                sections = []
                if 'psycholinguistic_profile' in response_data:
                    pp = response_data['psycholinguistic_profile']
                    for k, v in pp.items():
                        sections.append(f"### {k.replace('_', ' ').title()}\n{v}")
                final_result['character_assessment'] = "\n\n".join(sections)

            elif stage_name == 'behavioral':
                sections = []
                if 'behavioral_matrix' in response_data:
                    bm = response_data['behavioral_matrix']
                    for k, v in bm.items():
                        sections.append(f"### {k.replace('_', ' ').title()}\n{v}")
                if 'social_network' in response_data:
                     sn = response_data['social_network']
                     sections.append(f"### Social Network Analysis\n{json.dumps(sn, indent=2)}")
                final_result['behavioral_insights'] = "\n\n".join(sections)

            elif stage_name == 'ideological':
                sections = []
                sections.append("\n## Ideological & Belief Mapping")
                if 'ideological_mapping' in response_data:
                    im = response_data['ideological_mapping']
                    for k, v in im.items():
                        val = v if isinstance(v, str) else json.dumps(v)
                        sections.append(f"**{k.replace('_', ' ').title()}:** {val}")
                final_result['character_assessment'] += "\n\n" + "\n\n".join(sections)

            yield ('status', f'Stage {stage_name} complete.')

        final_result['raw_response'] = json.dumps(aggregated_raw)
        yield ('status', 'Finalizing comprehensive report...')
        yield ('result', final_result)

    def _build_stage_prompt(self, stage, posts, employee_info):
        # Prepare posts context
        posts_text = ""
        for i, post in enumerate(posts[:50], 1):
             platform = post.get('platform', 'unknown')
             created_at = post.get('created_at', 'unknown')
             text = post.get('text', '')
             posts_text += f"[{i}] {created_at} ({platform}): {text}\n"

        profile = f"Subject: {employee_info.get('full_name')} ({employee_info.get('position')})"
        
        # Reuse prompt strings from OpenAI implementation for consistency
        # (Shortened here for brevity in ReplaceChunk, but in practice they are full length)
        # Using exact full strings ensures same behavior.
        
        common_prompt = ""
        if stage == 'risk':
            common_prompt = f'''FOCUS: Security Threats, Radicalization, Red Flags, Insider Threat Risks.
            Return JSON: {{ "risk_score": <0-100>, "confidence_score": <0-100>, "red_flags": [], "positive_indicators": [], "executive_summary": "", "threat_surface": {{}} }}'''
        elif stage == 'psycholinguistic':
             common_prompt = f'''FOCUS: Cognitive Patterns, Emotional Intelligence, Linguistic Markers.
             Return JSON: {{ "psycholinguistic_profile": {{ "cognitive_patterns": "", "emotional_landscape": "", "linguistic_markers": "" }} }}'''
        elif stage == 'behavioral':
             common_prompt = f'''FOCUS: Posting Habits, Social Dynamics, Self-Presentation.
             Return JSON: {{ "behavioral_matrix": {{ "posting_behavior": "", "social_dynamics": "", "self_presentation": "" }}, "social_network": {{}} }}'''
        elif stage == 'ideological':
             common_prompt = f'''FOCUS: Values, Political/Religious Beliefs, Radicalization Trajectory.
             Return JSON: {{ "ideological_mapping": {{ "core_values": "", "political_ideology": "", "religious_framework": "", "radicalization_trajectory": "" }} }}'''

        return f"""
        You are a forensic behavioral psychologist. Analyze these posts for {profile}.
        {common_prompt}
        
        POSTS:
        {posts_text}
        """
