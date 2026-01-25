from openai import OpenAI
from flask import current_app
import logging
import json
from app.models import get_setting

logger = logging.getLogger(__name__)

class OpenAICompatibleService:
    """
    Generic service for interacting with OpenAI-compatible APIs (Z.AI, OpenRouter, etc.).
    """
    
    def __init__(self, provider_type):
        """
        Initialize the service.
        
        Args:
            provider_type (str): 'z_ai' or 'openrouter'
        """
        self.provider_type = provider_type
        
        if provider_type == 'z_ai':
            self.api_key = get_setting('ZAI_API_KEY', current_app.config.get('ZAI_API_KEY'))
            self.base_url = get_setting('ZAI_API_BASE', current_app.config.get('ZAI_API_BASE', "https://open.bigmodel.cn/api/paas/v4/"))
            # Ensure model is set
            self.model = get_setting('ZAI_MODEL', current_app.config.get('ZAI_MODEL'))
            
        elif provider_type == 'openrouter':
            self.api_key = get_setting('OPENROUTER_API_KEY', current_app.config.get('OPENROUTER_API_KEY'))
            self.base_url = get_setting('OPENROUTER_API_BASE', current_app.config.get('OPENROUTER_API_BASE', "https://openrouter.ai/api/v1/"))
            self.model = get_setting('OPENROUTER_MODEL', current_app.config.get('OPENROUTER_MODEL'))
            
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
            
        if not self.api_key:
            # We don't raise error here to allow app to start, but check calling methods
            logger.warning(f"API key not found for {provider_type}")
            self.client = None
        else:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )

    def analyze_social_media_posts(self, posts, employee_info, selected_checks=None):
        """
        Analyze posts using the configured provider.
        """
        if not self.client:
            raise ValueError(f"API key for {self.provider_type} is not configured.")

        # Construct the prompt (Simulating what OllamaService/GeminiService do)
        # We reuse the logic broadly. 
        
        prompt = self._build_deep_analysis_prompt(posts, employee_info, selected_checks)
        
        try:
            # Call the API
            logger.info(f"Sending analysis request to {self.provider_type} using model {self.model}")
            
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert social media analyst for background checks. You output ONLY valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=self.model,
                response_format={ "type": "json_object" } # Using JSON mode which is supported by Z.AI and many OpenRouter models
            )
            
            response_content = chat_completion.choices[0].message.content
            
            # Parse JSON
            try:
                # Clean up if markdown code blocks are returned even in JSON mode
                if response_content.startswith("```json"):
                    response_content = response_content.replace("```json", "").replace("```", "")
                elif response_content.startswith("```"):
                    response_content = response_content.replace("```", "")
                    
                result = json.loads(response_content)
                result['analysis_model'] = f"{self.provider_type}:{self.model}"
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON Parse Error from {self.provider_type}: {e}")
                logger.error(f"Raw response: {response_content}")
                # Fallback structure
                return {
                    "risk_score": 0,
                    "character_assessment": "Analysis failed to parse.",
                    "red_flags": ["System error: Invalid JSON response from AI provider"],
                    "analysis_model": f"{self.provider_type}:{self.model}"
                }
                
        except Exception as e:
            logger.error(f"API Error ({self.provider_type}): {str(e)}")
            raise

    def _build_deep_analysis_prompt(self, posts: List[Dict], employee_info: Dict, selected_checks=None) -> str:
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
