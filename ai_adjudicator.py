"""
AI Adjudicator for Falsifi - LLM-based quality scoring
"""
import os
from openai import OpenAI
from typing import Dict, Tuple, Optional
import json

class AIAdjudicator:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the AI adjudicator with OpenAI API key."""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
    
    def evaluate_refutation(self, bounty_title: str, bounty_description: str, 
                           refutation_content: str, sources: Optional[str] = None) -> Dict:
        """
        Evaluate a refutation using LLM.
        
        Returns a dict with:
        - score: 0-100 quality score
        - feedback: Detailed feedback
        - status: 'approved', 'rejected', or 'flagged'
        - flags: List of issues found
        """
        if not self.client:
            # Fallback: simple heuristic if no API key
            return self._fallback_evaluation(refutation_content)
        
        try:
            prompt = self._build_prompt(bounty_title, bounty_description, 
                                       refutation_content, sources)
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content
            return self._parse_response(result_text)
            
        except Exception as e:
            print(f"AI Adjudication error: {e}")
            return self._fallback_evaluation(refutation_content)
    
    def _system_prompt(self) -> str:
        return """You are an expert in critical thinking, logic, and debate.
Your task is to evaluate refutations of claims and ideas.

Evaluate the refutation on these criteria:
1. Logical validity - Does the argument follow logically?
2. Evidence quality - Are claims supported by evidence?
3. Relevance - Does it address the core claim?
4. Rhetorical quality - Is it clear, concise, and well-structured?
5. Tone - Is it constructive and not needlessly hostile?

Provide a score (0-100) and detailed feedback.
Flag egregiously bad-faith arguments (spam, nonsense, personal attacks without substance).

Respond in JSON format:
{
  "score": 75,
  "feedback": "Detailed feedback here...",
  "status": "approved|flagged|rejected",
  "flags": ["list", "of", "issues"]
}"""
    
    def _build_prompt(self, bounty_title: str, bounty_description: str,
                     refutation_content: str, sources: Optional[str] = None) -> str:
        prompt = f"""BOUNTY CLAIM:
Title: {bounty_title}
Description: {bounty_description}

REFUTATION SUBMITTED:
{refutation_content}
"""
        if sources:
            prompt += f"\nSOURCES PROVIDED:\n{sources}\n"
        
        prompt += "\nEvaluate this refutation and provide your assessment in the requested JSON format."
        return prompt
    
    def _parse_response(self, response_text: str) -> Dict:
        """Parse the LLM response, handling potential formatting issues."""
        try:
            # Try to extract JSON from the response
            # Handle cases where LLM might wrap in markdown code blocks
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
            
            result = json.loads(json_str)
            
            # Ensure required fields exist
            return {
                'score': result.get('score', 50),
                'feedback': result.get('feedback', 'No feedback provided'),
                'status': result.get('status', 'approved'),
                'flags': result.get('flags', [])
            }
        except json.JSONDecodeError:
            # Fallback parsing if JSON fails
            return {
                'score': 50,
                'feedback': response_text[:500],
                'status': 'approved',
                'flags': ['parsing_error']
            }
    
    def _fallback_evaluation(self, refutation_content: str) -> Dict:
        """Simple heuristic evaluation when AI is unavailable."""
        content_length = len(refutation_content)
        word_count = len(refutation_content.split())
        
        # Basic quality heuristics
        score = 50  # Default
        flags = []
        
        if word_count < 20:
            score -= 20
            flags.append("too_short")
        
        if word_count > 100:
            score += 10
        
        # Check for spam indicators
        spam_phrases = ['click here', 'buy now', 'limited time', 'make money fast']
        if any(phrase in refutation_content.lower() for phrase in spam_phrases):
            score = 10
            flags.append("spam_detected")
        
        # Check for all caps (shouting)
        caps_ratio = sum(1 for c in refutation_content if c.isupper()) / max(len(refutation_content), 1)
        if caps_ratio > 0.5:
            score -= 10
            flags.append("excessive_caps")
        
        score = max(0, min(100, score))
        
        status = 'flagged' if flags else 'approved'
        if score < 30:
            status = 'rejected'
        
        return {
            'score': score,
            'feedback': f'Automated evaluation (AI unavailable). Length: {word_count} words. Issues: {", ".join(flags) if flags else "None"}',
            'status': status,
            'flags': flags
        }
    
    def calculate_reward(self, ai_score: float, creator_rating: int, 
                        bounty_amount: int) -> int:
        """
        Calculate reward based on AI score and creator rating.
        
        Formula: Weighted combination with creator rating having more weight
        """
        if creator_rating is None:
            # If no creator rating yet, use AI score as interim
            normalized_score = ai_score / 100
        else:
            # Creator rating (1-10) gets 70% weight, AI score gets 30%
            normalized_creator = creator_rating / 10
            normalized_ai = ai_score / 100
            normalized_score = (0.7 * normalized_creator) + (0.3 * normalized_ai)
        
        reward = int(normalized_score * bounty_amount)
        return max(0, reward)
    
    def should_return_bond(self, ai_score: float, creator_rating: Optional[int]) -> bool:
        """Determine if bond should be returned based on quality."""
        if creator_rating is not None:
            # If creator rated it, use their rating
            return creator_rating >= 5
        
        # Otherwise use AI score
        return ai_score >= 40