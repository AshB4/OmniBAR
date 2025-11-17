"""
Lightweight prompt quality evaluation objectives for OmniBAR.

These objectives provide real scoring without requiring LLM calls,
using heuristic-based analysis of prompt characteristics.
"""

import re
from typing import Dict, Any, Type
from pydantic import Field, model_validator

from omnibar.objectives.base import BaseBenchmarkObjective
from omnibar.core.types import FloatEvalResult


class PromptQualityObjective(BaseBenchmarkObjective):
    """
    Lightweight objective that evaluates prompt quality using heuristic analysis.

    Analyzes prompts for:
    - Appropriate length (not too short, not too long)
    - Question structure (presence of question marks, interrogative words)
    - Clarity indicators (specific terms, structure)
    - Actionability (clear intent, specific requests)

    Returns a score from 0.0 to 1.0 based on these factors.
    """

    name: str = "Prompt Quality Evaluator"
    description: str = "Evaluates prompt quality using heuristic analysis"
    category: str = "prompt_analysis"
    tags: list[str] = ["quality", "heuristic", "lightweight"]
    output_key: str = "prompt"

    # Specify the expected type of a valid evaluation result
    valid_eval_result_type: Type[FloatEvalResult] = FloatEvalResult

    # Hide eval_fn_kwargs from users by excluding them from the model schema
    eval_fn_kwargs: Dict[str, Any] = Field(default_factory=dict, exclude=True)

    @model_validator(mode='after')
    def _validate_objective(self):
        """Initialize eval_fn_kwargs after model initialization."""
        self.eval_fn_kwargs = {}
        return self

    def _eval_fn(self, goal: Any, formatted_output: Dict[str, Any], **kwargs) -> FloatEvalResult:
        """
        Evaluate prompt quality using heuristic analysis.

        Args:
            goal: Not used for this objective (kept for interface compatibility)
            formatted_output: Dictionary containing the prompt text

        Returns:
            FloatEvalResult: Score from 0.0 to 1.0 with quality assessment
        """
        prompt_text = str(formatted_output.get(self.output_key, "")).strip()

        if not prompt_text:
            return FloatEvalResult(
                result=0.0,
                message="Empty prompt - no content to evaluate"
            )

        # Calculate quality score based on multiple factors
        score_components = self._analyze_prompt_quality(prompt_text)
        final_score = sum(score_components.values()) / len(score_components)

        # Generate descriptive feedback
        feedback_parts = []
        if score_components['length_score'] < 0.5:
            feedback_parts.append("Consider adding more detail to your prompt")
        if score_components['structure_score'] < 0.5:
            feedback_parts.append("Try structuring your prompt more clearly")
        if score_components['clarity_score'] < 0.5:
            feedback_parts.append("Use more specific terms and examples")

        feedback = "; ".join(feedback_parts) if feedback_parts else "Good quality prompt with room for minor improvements"

        return FloatEvalResult(
            result=round(final_score, 3),
            message=feedback
        )

    def _analyze_prompt_quality(self, prompt: str) -> Dict[str, float]:
        """
        Analyze various aspects of prompt quality.

        Returns a dictionary of normalized scores (0.0 to 1.0) for different aspects.
        """
        # Length analysis (optimal range: 10-200 words)
        word_count = len(prompt.split())
        if word_count < 5:
            length_score = 0.2  # Too short
        elif word_count < 10:
            length_score = 0.5  # Short but acceptable
        elif word_count <= 150:
            length_score = 1.0  # Optimal length
        elif word_count <= 250:
            length_score = 0.7  # Long but still good
        else:
            length_score = 0.3  # Too long

        # Structure analysis (presence of questions, lists, etc.)
        has_questions = bool(re.search(r'\?', prompt))
        has_lists = bool(re.search(r'[\-\*]\s|\d+\.', prompt))
        has_structure = has_questions or has_lists

        interrogative_words = ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'can', 'could', 'would', 'should']
        has_interrogatives = any(word in prompt.lower() for word in interrogative_words)

        structure_score = min(1.0, (0.4 * has_questions + 0.3 * has_lists + 0.3 * has_interrogatives))

        # Clarity analysis (specific terms, examples, context)
        specific_indicators = [
            re.search(r'\d+', prompt),  # Numbers
            re.search(r'[A-Z][a-z]+', prompt),  # Proper nouns
            re.search(r'example|for instance|such as', prompt.lower()),  # Examples
            len(prompt.split()) > 15,  # Substantial content
        ]

        clarity_score = sum(1 for indicator in specific_indicators if indicator) / len(specific_indicators)

        # Actionability analysis (clear intent, specific requests)
        action_words = ['create', 'write', 'explain', 'describe', 'analyze', 'compare', 'summarize', 'generate', 'help']
        has_actions = any(word in prompt.lower() for word in action_words)

        imperative_start = prompt.strip().split()[0].lower() if prompt.strip() else ""
        has_imperative = imperative_start in ['please', 'can', 'could', 'would'] or prompt[0].isupper()

        actionability_score = min(1.0, 0.6 * has_actions + 0.4 * has_imperative)

        return {
            'length_score': length_score,
            'structure_score': structure_score,
            'clarity_score': clarity_score,
            'actionability_score': actionability_score,
        }

    async def _eval_fn_async(self, goal: Any, formatted_output: Dict[str, Any], **kwargs) -> FloatEvalResult:
        """Async wrapper that calls the sync evaluation function."""
        return self._eval_fn(goal, formatted_output, **kwargs)
