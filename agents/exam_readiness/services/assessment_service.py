from typing import Dict, Any, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import uuid
import logging
import re
from .llm_client import query_llm
from .rag_service import RAGService

_logger = logging.getLogger(__name__)

_ALLOWED_TYPES = {"mcq", "short_text", "essay", "coding", "math"}


def _normalize_question(q: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize question dict to match model schema"""
    question_text = q.get("question_text") or q.get("questionText") or q.get("text") or ""
    raw_type = q.get("question_type") or q.get("type") or ""
    options = q.get("options") or []
    correct_answer = q.get("correct_answer") or q.get("answer") or ""
    marks = q.get("marks", 1)
    difficulty = (q.get("difficulty") or "").lower() or None

    qt = str(raw_type).lower().strip()
    if qt == "mathematical":
        qt = "math"

    if not isinstance(options, list):
        options = [str(options)]
    options = [str(o) for o in options]

    return {
        "question_id": q.get("question_id") or str(uuid.uuid4()),
        "question_text": str(question_text),
        "question_type": qt if qt in _ALLOWED_TYPES else "mcq",
        "options": options,
        "correct_answer": str(correct_answer) if correct_answer is not None else "",
        "expected_keywords": q.get("expected_keywords") or [],
        "marks": int(marks) if str(marks).isdigit() else 1,
        "difficulty": difficulty if difficulty in {"easy", "medium", "hard"} else None,
        "metadata": q.get("metadata") or {},
    }


def _build_type_specific_prompt(
    question_type: str,
    count: int,
    subject: str,
    assessment_type: str,
    difficulty: str,
    allow_latex: bool,
    rag_context: Optional[str],
) -> str:
    """Build a specialized prompt for a specific question type"""
    
    # Assessment type time/style profiles
    profiles = {
        "quiz": {
            "time_per_q": "1–3 minutes",
            "marks_range": "1–2 marks",
            "style": "Ultra-concise, single-concept, rapid recall",
        },
        "exam": {
            "time_per_q": "5–20 minutes",
            "marks_range": "2–10 marks",
            "style": "Structured, academic rigor, may require multi-step reasoning",
        },
        "assignment": {
            "time_per_q": "2–8 hours",
            "marks_range": "10–30 marks",
            "style": "Deep, project-like, real-world scenarios with deliverables",
        },
    }
    
    profile = profiles.get(assessment_type, profiles["quiz"])
    
    latex_clause = (
        "- Use LaTeX/Markdown for math: inline ($...$) or display ($$...$$). Escape backslashes as \\\\."
        if allow_latex else
        "- NO LaTeX. Write math in plain text."
    )
    
    rag_block = f"""
AUTHORITATIVE SOURCE MATERIAL:
{rag_context}
Base questions on this material when relevant.
""" if rag_context else ""

    # Type-specific instructions
    type_instructions = {
        "mcq": f"""
QUESTION TYPE: Multiple Choice (MCQ)

FORMAT REQUIREMENTS:
- Provide EXACTLY 4 options labeled A, B, C, D
- One option must be unambiguously correct
- Distractors should be plausible but clearly wrong
- Use the "options" array: ["text of A", "text of B", "text of C", "text of D"]
- Set "correct_answer" to the EXACT text of the correct option

STYLE FOR {assessment_type.upper()}:
- {profile['style']}
- Time per question: {profile['time_per_q']}
- Marks: {profile['marks_range']}

EXAMPLE OUTPUT:
{{
  "question_text": "What is the time complexity of binary search on a sorted array?",
  "question_type": "mcq",
  "options": ["O(n)", "O(log n)", "O(n log n)", "O(1)"],
  "correct_answer": "O(log n)",
  "marks": 2,
  "difficulty": "easy"
}}
""",
        
        "short_text": f"""
QUESTION TYPE: Short Answer

FORMAT REQUIREMENTS:
- Expect a brief answer (1-3 sentences or a single term/value)
- Set "options" to an empty array []
- "correct_answer" should be the expected brief response or key term

STYLE FOR {assessment_type.upper()}:
- {profile['style']}
- Time per question: {profile['time_per_q']}
- Marks: {profile['marks_range']}

EXAMPLE OUTPUT:
{{
  "question_text": "Name the HTTP method used to update an existing resource.",
  "question_type": "short_text",
  "options": [],
  "correct_answer": "PUT or PATCH",
  "marks": 1,
  "difficulty": "easy"
}}
""",
        
        "essay": f"""
QUESTION TYPE: Essay / Long Answer

FORMAT REQUIREMENTS:
- Require structured, multi-paragraph responses
- Set "options" to []
- "correct_answer" should outline key points or a model answer structure
- Include word count guidance in question_text

STYLE FOR {assessment_type.upper()}:
- {profile['style']}
- Time per question: {profile['time_per_q']}
- Marks: {profile['marks_range']}
- For assignments: require citations, analysis, evaluation

EXAMPLE OUTPUT:
{{
  "question_text": "Explain the CAP theorem and discuss trade-offs in distributed database design. Provide examples of systems that prioritize different aspects. (500-800 words)",
  "question_type": "essay",
  "options": [],
  "correct_answer": "Model answer should cover: definition of Consistency, Availability, Partition tolerance; trade-offs (CP vs AP); examples like MongoDB (CP) vs Cassandra (AP); real-world implications.",
  "marks": 8,
  "difficulty": "medium"
}}
""",
        
        "coding": f"""
QUESTION TYPE: Coding Problem

FORMAT REQUIREMENTS:
- Clearly specify: input format, output format, constraints
- Set "options" to []
- "correct_answer" should be a working code solution
- IMPORTANT: Use \\n for newlines in code, escape all quotes and backslashes properly for JSON
- Keep code simple and avoid complex nested structures

STYLE FOR {assessment_type.upper()}:
- {profile['style']}
- Time per question: {profile['time_per_q']}
- Marks: {profile['marks_range']}
- For assignments: require documentation, test cases, complexity analysis

JSON FORMATTING RULES FOR CODE:
- Use \\n for line breaks (not actual newlines)
- Escape backslashes: \\\\ 
- Escape quotes: \\"
- Keep the code concise to avoid JSON parsing issues

EXAMPLE OUTPUT:
{{
  "question_text": "Write a function that reverses a string. Include type hints.",
  "question_type": "coding",
  "options": [],
  "correct_answer": "def reverse_string(s: str) -> str:\\n    return s[::-1]",
  "marks": 5,
  "difficulty": "easy"
}}
""",
        
        "math": f"""
QUESTION TYPE: Mathematical Problem

FORMAT REQUIREMENTS:
- Use proper notation {latex_clause}
- Set "options" to []
- "correct_answer" should show step-by-step solution
- For proofs: outline logical structure

STYLE FOR {assessment_type.upper()}:
- {profile['style']}
- Time per question: {profile['time_per_q']}
- Marks: {profile['marks_range']}

EXAMPLE OUTPUT:
{{
  "question_text": "Prove that the sum of angles in a triangle is 180 degrees using parallel line properties.",
  "question_type": "math",
  "options": [],
  "correct_answer": "Draw triangle ABC. Extend side BC to point D. Draw line through A parallel to BC. Angles BAC + CAD = 180 (straight line). Angle CAD = angle ACB (alternate interior angles).",
  "marks": 5,
  "difficulty": "medium"
}}
"""
    }

    prompt = f"""
You are an expert assessment designer generating {count} questions of type "{question_type}" ONLY.

SUBJECT: {subject}
ASSESSMENT TYPE: {assessment_type}
DIFFICULTY BIAS: {difficulty}
QUESTION COUNT: {count}

{type_instructions.get(question_type, "")}

{rag_block}

CRITICAL OUTPUT REQUIREMENTS:
1. Return ONLY a JSON array of {count} question objects
2. NO code fences, NO prose, NO comments
3. Each object uses these EXACT keys:
   - "question_text": string
   - "question_type": "{question_type}"
   - "options": array
   - "correct_answer": string
   - "marks": integer
   - "difficulty": "easy" | "medium" | "hard"

Generate {count} high-quality {question_type} questions now. Return ONLY the JSON array.
"""
    return prompt.strip()


def _generate_single_type(
    question_type: str,
    count: int,
    subject: str,
    assessment_type: str,
    difficulty: str,
    allow_latex: bool,
    rag_context: Optional[str],
) -> Tuple[str, List[Dict[str, Any]], Optional[str]]:
    """Generate questions for a single type"""
    if count <= 0:
        return question_type, [], None
    
    try:
        prompt = _build_type_specific_prompt(
            question_type=question_type,
            count=count,
            subject=subject,
            assessment_type=assessment_type,
            difficulty=difficulty,
            allow_latex=allow_latex,
            rag_context=rag_context,
        )
        
        raw = query_llm(prompt)
        
        # Strip code fences and clean response
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw = "\n".join(lines).strip()
        
        # Try to parse JSON with better error handling
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as json_err:
            # Log the problematic JSON for debugging
            _logger.error(f"JSON parse error for {question_type}: {json_err}")
            _logger.error(f"Raw response (first 500 chars): {raw[:500]}")
            
            # Try to extract JSON array if wrapped in text
            import re
            json_match = re.search(r'\[\s*\{.*\}\s*\]', raw, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
                except:
                    return question_type, [], f"Failed to parse JSON even after extraction: {str(json_err)}"
            else:
                return question_type, [], f"JSON parse error: {str(json_err)}"
        
        if not isinstance(data, list):
            return question_type, [], f"LLM did not return array for {question_type}"
        
        # Normalize
        normalized = [_normalize_question(q) for q in data]
        
        # Validate
        if len(normalized) != count:
            return question_type, [], f"Expected {count} questions, got {len(normalized)}"
        
        return question_type, normalized, None
        
    except Exception as e:
        return question_type, [], f"Generation error: {str(e)}"


def generate_questions_by_type(
    subject: str,
    assessment_type: str,
    difficulty: str,
    type_counts: Dict[str, int],
    allow_latex: bool = True,
    rag_context: Optional[str] = None,
    pdf_paths: Optional[List[str]] = None,
    rag_top_k: int = 6,
    rag_max_chars: int = 4000,
) -> Tuple[List[Dict[str, Any]], Dict[str, Optional[str]]]:
    """Generate questions by calling LLM separately for each type"""
    
    # Build RAG context if PDFs provided
    effective_rag_context = rag_context
    if pdf_paths:
        rag_service = RAGService()
        for path in pdf_paths:
            rag_service.load_pdfs([path])
        results = rag_service.search(subject, k=rag_top_k)
        context_text = "\n\n".join([r.content for r in results])
        if len(context_text) > rag_max_chars:
            context_text = context_text[:rag_max_chars] + "\n[truncated]"
        effective_rag_context = context_text
    
    # Filter zero counts
    filtered_counts = {k: int(v) for k, v in type_counts.items() if int(v) > 0}
    
    all_questions = []
    type_errors = {}
    
    # Generate in parallel
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(
                _generate_single_type,
                qtype,
                count,
                subject,
                assessment_type,
                difficulty,
                allow_latex,
                effective_rag_context,
            ): qtype
            for qtype, count in filtered_counts.items()
        }
        
        for future in as_completed(futures):
            qtype, questions, error = future.result()
            type_errors[qtype] = error
            if not error:
                all_questions.extend(questions)
    
    return all_questions, type_errors