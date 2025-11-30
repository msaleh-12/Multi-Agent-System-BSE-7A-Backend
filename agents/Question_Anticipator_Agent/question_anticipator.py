# ------------------------------------------------------------
# langraph_main.py – LangGraph re-write of Question Anticipator
# ------------------------------------------------------------
"""
Question Anticipator Agent – LangGraph Edition
Features
--------
- Same logic as the original (patterns, RAG, LLM fall-backs, memory, etc.)
- Fully orchestrated via LangGraph
- State is a single TypedDict that flows through the graph
- FastAPI endpoint simply invokes the graph and returns the final state
- **FIXED: Gemini provider (free tier) with correct SDK**
"""

from __future__ import annotations
import os, json, hashlib, random, re, time, requests
from datetime import datetime
from typing import TypedDict, List, Dict, Optional, Any, TYPE_CHECKING
from collections import Counter, defaultdict
import google.generativeai as genai

# --------------- LangGraph & LangChain ---------------
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

# --------------- FastAPI ---------------
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --------------- Optional libs ---------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if TYPE_CHECKING:
    import chromadb
chromadb: Any = None
try:
    import chromadb
    from chromadb.config import Settings
except Exception:
    chromadb = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

# --------------- Config ---------------
CHROMA_DB_PATH      = os.getenv("CHROMA_DB_PATH", "./chroma_db")
EMBEDDING_MODEL     = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY")  # get from https://makersuite.google.com/app/apikey

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

LLM_PROVIDER        = os.getenv("LLM_PROVIDER", "gemini").lower()   # default → Gemini
LLM_MODEL           = os.getenv("LLM_MODEL", "models/gemini-2.0-flash-exp")
GROK_API_KEY        = os.getenv("GROK_API_KEY")
OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY")
INCLUDE_ANSWERS     = os.getenv("INCLUDE_ANSWERS", "false").lower() in ("1", "true", "yes")
LLM_BASE_URL        = None
os.environ["PYTHONUTF8"] = os.environ.get("PYTHONUTF8", "1")

# --------------- Pydantic models ---------------
class PastPaper(BaseModel):
    year: str
    questions: List[str]

class ExamPattern(BaseModel):
    mcqs: int
    short_questions: int
    long_questions: int

class InputData(BaseModel):
    syllabus: List[str]
    past_papers: List[PastPaper]
    exam_pattern: ExamPattern
    weightage: Dict[str, int] = {}
    difficulty_preference: str = "medium"
    include_answers: Optional[bool] = False

class PredictedQuestion(BaseModel):
    topic: str
    question_text: str
    difficulty_level: str
    question_type: str
    probability_score: float
    options: Optional[List[str]] = None
    correct_option: Optional[int] = None
    rag_used: Optional[bool] = False
    rag_score: Optional[float] = 0.0

class AgentOutput(BaseModel):
    predicted_questions: List[PredictedQuestion]
    from_memory: bool = False
    processing_time: float = 0.0
    memory_hash: Optional[str] = None

# --------------- LangGraph State ---------------
class GraphState(TypedDict):
    input_data: Dict[str, Any]
    input_hash: str
    memory_result: Optional[Dict[str, Any]]
    pattern_analysis: Optional[Dict[str, Any]]
    generated_questions: List[Dict[str, Any]]
    output: Dict[str, Any]
    timestamp: str

# --------------- Utilities ---------------
def safe_hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

def normalize_topic(t: str) -> str:
    return re.sub(r"\s+", " ", t.strip())

# --------------- VectorMemory ---------------
class VectorMemory:
    def __init__(self, collection_name: str = "question_predictions"):
        self.collection_name = collection_name
        self.client: Optional["chromadb.PersistentClient"] = None
        self.collection = None
        self.embeddings_model = None

        if chromadb is None:
            print("⚠ chromadb not installed – memory disabled")
            return

        try:
            self.client = chromadb.PersistentClient(
                path=CHROMA_DB_PATH,
                settings=Settings(anonymized_telemetry=False, allow_reset=True),
            )
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
            except Exception:
                self.collection = self.client.create_collection(name=self.collection_name)
            print(f"✓ Vector memory initialised at {CHROMA_DB_PATH}")
        except Exception as e:
            print(f"✗ ChromaDB init failed: {e}")

        if SentenceTransformer is not None:
            try:
                self.embeddings_model = SentenceTransformer(EMBEDDING_MODEL)
                print(f"✓ Embedding model loaded: {EMBEDDING_MODEL}")
            except Exception as e:
                print(f"⚠ Embedding model failed: {e}")

    def embed_text(self, text: str) -> List[float]:
        if not self.embeddings_model:
            raise RuntimeError("No embedding model")
        emb = self.embeddings_model.encode(text, convert_to_tensor=False)
        return emb.tolist() if hasattr(emb, "tolist") else list(emb)

    def create_query_text(self, input_data: Dict) -> str:
        syllabus = ", ".join(input_data.get("syllabus", []))
        pattern = input_data.get("exam_pattern", {})
        difficulty = input_data.get("difficulty_preference", "medium")
        weightage = input_data.get("weightage", {})
        return f"Syllabus: {syllabus}. Pattern: {pattern.get('mcqs',0)} MCQ, {pattern.get('short_questions',0)} short, {pattern.get('long_questions',0)} long. Difficulty: {difficulty}. Weightage: {json.dumps(weightage)}"

    def store_prediction(self, input_hash: str, input_data: Dict, output: Dict):
        if not self.collection or not self.embeddings_model:
            return
        try:
            query_text = self.create_query_text(input_data)
            emb = self.embed_text(query_text)
            self.collection.add(
                embeddings=[emb],
                documents=[query_text],
                metadatas=[{
                    "input_hash": input_hash,
                    "output": json.dumps(output),
                    "timestamp": datetime.now().isoformat()
                }],
                ids=[input_hash]
            )
            print(f"✓ Stored prediction ({input_hash[:8]}...)")
        except Exception as e:
            print(f"✗ Store failed: {e}")

    def search_similar(self, input_data: Dict, threshold: float = 0.3) -> Optional[Dict]:
        if not self.collection or not self.embeddings_model:
            return None
        try:
            query_text = self.create_query_text(input_data)
            emb = self.embed_text(query_text)
            res = self.collection.query(query_embeddings=[emb], n_results=1)
            distances = res.get("distances", [[]])
            metadatas = res.get("metadatas", [[]])
            if distances and distances[0] and distances[0][0] < threshold:
                meta = metadatas[0][0]
                return {
                    "output": json.loads(meta["output"]),
                    "original_hash": meta.get("input_hash"),
                    "timestamp": meta.get("timestamp"),
                    "distance": distances[0][0]
                }
            return None
        except Exception as e:
            print(f"✗ Search failed: {e}")
            return None

# --------------- PatternAnalyzer ---------------
class PatternAnalyzer:
    def analyze(self, input_data: Dict) -> Dict:
        past = input_data.get("past_papers", [])
        weightage_map = input_data.get("weightage", {})
        parsed = []
        for paper in past:
            for q in paper.get("questions", []):
                if isinstance(q, dict):
                    parsed.append({
                        "topic": normalize_topic(q.get("topic", "Unknown")),
                        "type": q.get("type", "short_question"),
                        "difficulty": q.get("difficulty", "medium"),
                        "semester": q.get("semester", "Unknown"),
                        "text": q.get("text", "")
                    })
                else:
                    text = str(q)
                    tp = "Unknown"
                    words = re.findall(r"[A-Z][a-zA-Z]{2,}(?:\s+[A-Z][a-zA-Z]{2,})*", text)
                    if words:
                            tp = normalize_topic(words[0])
                            if tp.lower() in ["what", "describe", "explain", "define"]:
                                tp = "Unknown"

                    t = "mcq" if re.search(r"\b(mcq|multiple choice)\b", text, re.I) else \
                        "short_question" if len(text.split()) <= 30 else "long_question"
                    diff = "hard" if re.search(r"\b(hard|prove|derive)\b", text, re.I) else \
                        "easy" if re.search(r"\b(simple|easy|define)\b", text, re.I) else "medium"
                    parsed.append({"topic": tp, "type": t, "difficulty": diff, "semester": "Unknown", "text": text})

        topic_freq = Counter(p["topic"] for p in parsed)
        qtype_dist = Counter(p["type"] for p in parsed)
        difficulty_trend = Counter(p["difficulty"] for p in parsed)
        difficulty_per_topic = defaultdict(Counter)
        for p in parsed:
            difficulty_per_topic[p["topic"]][p["difficulty"]] += 1

        topic_weightage_score = {}
        for topic, freq in topic_freq.items():
            diff_score = (difficulty_per_topic[topic]["hard"] * 3 +
                         difficulty_per_topic[topic]["medium"] * 2 +
                         difficulty_per_topic[topic]["easy"] * 1)
            external = weightage_map.get(topic, 0)
            topic_weightage_score[topic] = freq * 2 + diff_score + external

        return {
            "total_past_questions": len(parsed),
            "topic_frequency": dict(topic_freq),
            "difficulty_trend": dict(difficulty_trend),
            "question_type_distribution": dict(qtype_dist),
            "hot_topics": [t for t, _ in topic_freq.most_common(10)],
            "difficulty_per_topic": {k: dict(v) for k, v in difficulty_per_topic.items()},
            "topic_weightage_score": dict(sorted(topic_weightage_score.items(), key=lambda x: x[1], reverse=True))
        }

# --------------- RAGRetriever ---------------
class RAGRetriever:
    def __init__(self, vm: VectorMemory):
        self.vm = vm

    def retrieve_relevant_section(self, syllabus: List[str], topic: str, weight: float = 1.0) -> Dict:
        topic_norm = normalize_topic(topic)
        if not self.vm or not self.vm.embeddings_model:
            best = None
            score = 0.0
            for sec in syllabus:
                s = sec.lower()
                if topic_norm.lower() in s:
                    return {"section": sec, "score": 0.9}
                overlap = len(set(topic_norm.split()) & set(s.split()))
                sc = overlap / max(1, len(topic_norm.split()))
                if sc > score:
                    best, score = sec, sc
            return {"section": best or (syllabus[0] if syllabus else None), "score": score}

        try:
            import math
            t_emb = self.vm.embed_text(topic_norm)
            best = None
            best_score = -1.0
            for sec in syllabus:
                sec_emb = self.vm.embed_text(sec)
                dot = sum(a * b for a, b in zip(t_emb, sec_emb))
                na, nb = math.sqrt(sum(a * a for a in t_emb)), math.sqrt(sum(b * b for b in sec_emb))
                sim = dot / (na * nb + 1e-9) * (1 + 0.01 * weight)
                if sim > best_score:
                    best_score, best = sim, sec
            return {"section": best, "score": max(0.0, min(1.0, best_score))}
        except Exception:
            return {"section": syllabus[0] if syllabus else None, "score": 0.0}

# --------------- QuestionGenerator ---------------
class QuestionGenerator:
    def __init__(self, vm: VectorMemory):
        self.vm = vm
        self.rag = RAGRetriever(vm) if vm else None
        self.llm = self._build_llm()

    def _build_llm(self):
        if LLM_PROVIDER == "gemini" and GEMINI_API_KEY:
            try:
                class GeminiChat:
                    def __init__(self, model_name="models/gemini-2.0-flash-exp"):
                        self.model_name = model_name
                        self.model = genai.GenerativeModel(model_name)

                    def invoke(self, prompt: str) -> Any:
                        try:
                            response = self.model.generate_content(
                                prompt,
                                generation_config=genai.types.GenerationConfig(
                                    temperature=0.6,
                                    max_output_tokens=400
                                )
                            )
                            # Create a simple object that mimics LangChain's response
                            class Response:
                                def __init__(self, text):
                                    self.content = text
                            return Response(response.text)
                        except Exception as e:
                            print(f"⚠ LLM generation failed: {e}")
                            return None

                print("✓ Gemini LLM initialized successfully")
                return GeminiChat(model_name=LLM_MODEL)

            except Exception as e:
                print(f"⚠ Gemini native init failed: {e}")

        # ---------- existing grok / openai / anthropic ----------
        if LLM_PROVIDER == "grok" and GROK_API_KEY:
            try:
                return ChatOpenAI(api_key=GROK_API_KEY, model=LLM_MODEL, base_url=LLM_BASE_URL, temperature=0.7)
            except Exception as e:
                print(f"⚠ Grok init failed: {e}")
        elif LLM_PROVIDER == "openai" and OPENAI_API_KEY:
            try:
                return ChatOpenAI(api_key=OPENAI_API_KEY, model=LLM_MODEL, temperature=0.7)
            except Exception as e:
                print(f"⚠ OpenAI init failed: {e}")
        elif LLM_PROVIDER == "anthropic" and ANTHROPIC_API_KEY:
            try:
                return ChatAnthropic(api_key=ANTHROPIC_API_KEY, model=LLM_MODEL, temperature=0.7)
            except Exception as e:
                print(f"⚠ Anthropic init failed: {e}")
        return None

    def _generate_realistic_mcq_with_llm(self, topic: str, difficulty: str, context: str) -> Optional[Dict]:
        if not self.llm:
            return None
        prompt = f"""Generate a realistic multiple-choice question for an academic exam.
Topic: {topic}
Difficulty: {difficulty}
Context: {context[:500]}
Return ONLY valid JSON:
{{
    "question_text": "The complete question here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_option": 0
}}"""
        try:
            response = self.llm.invoke(prompt)
            if not response:
                return None
            txt = response.content.strip()
            txt = re.sub(r'^```json\s*', '', txt)
            txt = re.sub(r'^```\s*', '', txt)
            txt = re.sub(r'\s*```$', '', txt)
            data = json.loads(txt)
            if isinstance(data, dict) and len(data.get("options", [])) == 4 and 0 <= data.get("correct_option", -1) < 4:
                return data
        except Exception as e:
            print(f"⚠ LLM MCQ failed: {e}")
        return None

    def _generate_realistic_question_with_llm(self, topic: str, difficulty: str, q_type: str, context: str) -> Optional[str]:
        if not self.llm:
            return None

        # Clean topic
        topic_clean = re.sub(r"^(Explain|Describe|Define)\s+", "", topic, flags=re.I).strip()

        type_guide = {
            "short_question": "a short-answer question (2-5 marks)",
            "long_question": "a comprehensive question (8-15 marks)"
        }

        prompt = f"""
    Generate a realistic {difficulty} {type_guide.get(q_type, 'question')} about "{topic_clean}".
    The question must be clear, self-contained, and suitable for assessment.
    Do NOT start the question with 'Explain', 'Describe', or 'Define'.
    The question must end with a question mark.
    Include context where appropriate: {context[:500]}
    Return ONLY the question text.
    """

        try:
            response = self.llm.invoke(prompt)
            if not response or not hasattr(response, "content"):
                return None

            question = response.content.strip()

            # Remove codeblock markdown if any
            question = re.sub(r'^```(?:json)?\s*', '', question)
            question = re.sub(r'\s*```$', '', question)

            # Fallback if too short or generic
            if len(question) < 15 or any(word in question.lower() for word in ["explain", "describe", "define"]):
                return f"What is {topic_clean}?"

            # Ensure it ends with '?'
            if not question.endswith('?'):
                question = question.rstrip('.') + '?'

            return question

        except Exception as e:
            print(f"⚠ LLM question generation failed: {e}")
            return f"What is {topic_clean}?"
    def _create_mcq_fallback(self, topic: str, difficulty: str, context: str) -> Dict:
        """Generate realistic MCQ with context-aware options."""
        
        context_keywords = []
        if context and len(context) > 10:
            context_keywords = re.findall(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b', context)[:2]
        
        stems = {
            "easy": [
                f"What is the primary purpose of {topic}?",
                f"Which statement best describes {topic}?",
                f"What is the main characteristic of {topic}?",
                f"Which of the following is an example of {topic}?"
            ],
            "medium": [
                f"How does {topic} relate to real-world applications?",
                f"Which approach best applies principles of {topic}?",
                f"In what scenario would {topic} be most applicable?",
                f"Which of the following correctly explains {topic}?"
            ],
            "hard": [
                f"Given a complex system involving {topic}, what is the critical factor?",
                f"How would you differentiate between correct and incorrect uses of {topic}?",
                f"What are the key limitations of {topic} in advanced scenarios?",
                f"Which framework best integrates {topic} with broader concepts?"
            ]
        }
        
        correct_answers = {
            "easy": [
                f"To provide systematic understanding of {topic}",
                f"It represents a fundamental principle of {topic}",
                f"It ensures proper implementation of {topic}",
                f"It demonstrates core applications of {topic}"
            ],
            "medium": [
                f"By integrating theory with practical {topic} considerations",
                f"Through systematic analysis of {topic} principles",
                f"When aligned with established {topic} methodologies",
                f"By synthesizing multiple aspects of {topic}"
            ],
            "hard": [
                f"Understanding boundary conditions and exceptions in {topic}",
                f"Integration with complementary frameworks and {topic} theory",
                f"Critical evaluation of assumptions underlying {topic}",
                f"Advanced synthesis of {topic} principles with empirical validation"
            ]
        }
        
        distractors = {
            "easy": [
                f"It is rarely applied in practice",
                f"It contradicts standard {topic} methods",
                f"It focuses only on theoretical aspects",
                f"It is considered outdated"
            ],
            "medium": [
                f"By avoiding standard {topic} principles",
                f"Through trial-and-error rather than methodology",
                f"When sacrificing {topic} accuracy for efficiency",
                f"By ignoring contextual factors"
            ],
            "hard": [
                f"Oversimplifying {topic} into linear models",
                f"Misapplying concepts outside their validity scope",
                f"Conflating correlation with causation in {topic}",
                f"Ignoring empirical evidence for pure theory"
            ]
        }
        
        difficulty_level = difficulty.lower() if difficulty.lower() in ["easy", "medium", "hard"] else "medium"
        
        stem = random.choice(stems.get(difficulty_level, stems["medium"]))
        correct = random.choice(correct_answers.get(difficulty_level, correct_answers["medium"]))
        
        distractor_pool = distractors.get(difficulty_level, distractors["medium"])
        selected_distractors = random.sample(distractor_pool, min(3, len(distractor_pool)))
        
        options = [correct] + selected_distractors
        random.shuffle(options)
        correct_index = options.index(correct)
        
        return {
            "question_text": stem,
            "options": options,
            "correct_option": correct_index
        }

    def _create_mcq(self, topic: str, difficulty: str, syllabus: List[str], weight: int) -> Dict:
        """Create MCQ with LLM first, fallback to improved template generator."""
        context, rag_score = "", 0.0
        
        if self.rag and syllabus:
            res = self.rag.retrieve_relevant_section(syllabus, topic, weight)
            context, rag_score = res.get("section", ""), res.get("score", 0.0)
        
        llm = self._generate_realistic_mcq_with_llm(topic, difficulty, context)
        if llm:
            return {
                **llm,
                "topic": topic,
                "difficulty_level": difficulty,
                "question_type": "mcq",
                "probability_score": 0.95,
                "rag_used": True,
                "rag_score": rag_score
            }
        
        fb = self._create_mcq_fallback(topic, difficulty, context)
        
        return {
            **fb,
            "topic": topic,
            "difficulty_level": difficulty,
            "question_type": "mcq",
            "probability_score": 0.70 + min(0.25, 0.01 * weight + 0.2 * rag_score),
            "rag_used": bool(context),
            "rag_score": rag_score
        }

    def _create_short_question(self, topic: str, difficulty: str, syllabus: List[str]) -> Dict:
        context, rag_score = "", 0.0
        if self.rag and syllabus:
            res = self.rag.retrieve_relevant_section(syllabus, topic, 1.0)
            context, rag_score = res.get("section", ""), res.get("score", 0.0)
        llm = self._generate_realistic_question_with_llm(topic, difficulty, "short_question", context)
        if llm:
            return {"topic": topic, "question_text": llm, "difficulty_level": difficulty,
                    "question_type": "short_question", "probability_score": 0.90,
                    "rag_used": True, "rag_score": rag_score}
        templates = {
            "easy": [f"Define {topic} and explain its basic principle."],
            "medium": [f"Explain how {topic} is applied in practical scenarios."],
            "hard": [f"Prove the fundamental theorem related to {topic} with detailed steps."]
        }
        txt = random.choice(templates.get(difficulty, templates["medium"]))
        return {"topic": topic, "question_text": txt, "difficulty_level": difficulty,
                "question_type": "short_question", "probability_score": 0.75,
                "rag_used": bool(context), "rag_score": rag_score}

    def _create_long_question(self, topic: str, difficulty: str, syllabus: List[str]) -> Dict:
        context, rag_score = "", 0.0
        if self.rag and syllabus:
            res = self.rag.retrieve_relevant_section(syllabus, topic, 1.0)
            context, rag_score = res.get("section", ""), res.get("score", 0.0)
        llm = self._generate_realistic_question_with_llm(topic, difficulty, "long_question", context)
        if llm:
            return {"topic": topic, "question_text": llm, "difficulty_level": difficulty,
                    "question_type": "long_question", "probability_score": 0.88,
                    "rag_used": True, "rag_score": rag_score}
        templates = {
            "easy": [f"Discuss {topic} in detail, covering its definition, types, and basic applications."],
            "medium": [f"Analyze a comprehensive case study involving {topic}. Include problem formulation, methodology, solution steps, and interpretation of results."],
            "hard": [f"Design and solve an advanced problem involving {topic} that requires synthesis of multiple concepts. Include theoretical justification, detailed calculations, and critical analysis of results."]
        }
        txt = random.choice(templates.get(difficulty, templates["medium"]))
        return {"topic": topic, "question_text": txt, "difficulty_level": difficulty,
                "question_type": "long_question", "probability_score": 0.70,
                "rag_used": bool(context), "rag_score": rag_score}

    def generate(self, input_data: Dict, pattern_analysis: Dict) -> List[Dict]:
        syllabus = input_data.get("syllabus", [])
        exam_pattern = input_data.get("exam_pattern", {})
        difficulty = input_data.get("difficulty_preference", "medium")
        weightage = input_data.get("weightage", {})
        hot = pattern_analysis.get("hot_topics", []) if pattern_analysis else []
        topics_sorted = list(syllabus) + [t for t in hot if t not in syllabus] or ["General"]
        questions = []
        idx = 0
        for _ in range(exam_pattern.get("mcqs", 0)):
            topic = topics_sorted[idx % len(topics_sorted)]
            questions.append(self._create_mcq(topic, difficulty, syllabus, weightage.get(topic, 0)))
            idx += 1
        for _ in range(exam_pattern.get("short_questions", 0)):
            topic = topics_sorted[idx % len(topics_sorted)]
            questions.append(self._create_short_question(topic, difficulty, syllabus))
            idx += 1
        for _ in range(exam_pattern.get("long_questions", 0)):
            topic = topics_sorted[idx % len(topics_sorted)]
            questions.append(self._create_long_question(topic, difficulty, syllabus))
            idx += 1
        # Simple balance validator
        required = {"mcq": exam_pattern.get("mcqs", 0), "short_question": exam_pattern.get("short_questions", 0), "long_question": exam_pattern.get("long_questions", 0)}
        counts = {"mcq": 0, "short_question": 0, "long_question": 0}
        out = []
        for q in questions:
            t = q.get("question_type")
            if counts.get(t, 0) < required.get(t, 0):
                out.append(q)
                counts[t] += 1
        topics = list({q["topic"] for q in questions}) or ["General"]
        i = 0
        while counts["mcq"] < required["mcq"]:
            out.append(self._create_mcq(topics[i % len(topics)], "medium", [], 1))
            counts["mcq"] += 1
            i += 1
        while counts["short_question"] < required["short_question"]:
            out.append(self._create_short_question(topics[i % len(topics)], "medium", []))
            counts["short_question"] += 1
            i += 1
        while counts["long_question"] < required["long_question"]:
            out.append(self._create_long_question(topics[i % len(topics)], "medium", []))
            counts["long_question"] += 1
            i += 1
        return out

# --------------- LangGraph Nodes ---------------
vm = VectorMemory()
pattern_analyzer = PatternAnalyzer()
question_generator = QuestionGenerator(vm=vm)

def node_sanitize(state: GraphState) -> GraphState:
    data = state["input_data"]
    data["syllabus"] = [normalize_topic(s) for s in data.get("syllabus", [])]
    return {**state, "input_hash": safe_hash(data), "input_data": data}

def node_check_memory(state: GraphState) -> GraphState:
    if not vm:
        return state
    hit = vm.search_similar(state["input_data"])
    if hit and hit.get("original_hash") == state["input_hash"]:
        out = hit["output"]
        out["from_memory"] = True
        out["memory_hash"] = hit.get("original_hash", "")[:8]
        return {**state, "memory_result": hit, "output": out}
    return {**state, "memory_result": None}

def node_analyze_patterns(state: GraphState) -> GraphState:
    analysis = pattern_analyzer.analyze(state["input_data"])
    return {**state, "pattern_analysis": analysis}

def node_generate_questions(state: GraphState) -> GraphState:
    questions = question_generator.generate(state["input_data"], state["pattern_analysis"])
    include = state["input_data"].get("include_answers", False) or INCLUDE_ANSWERS
    if not include:
        for q in questions:
            q.pop("correct_option", None)
    output = {
        "predicted_questions": questions,
        "from_memory": False,
        "memory_hash": state["input_hash"][:8]
    }
    return {**state, "generated_questions": questions, "output": output}

def node_store_memory(state: GraphState) -> GraphState:
    if vm and not state.get("memory_result"):
        vm.store_prediction(state["input_hash"], state["input_data"], state["output"])
    return state

# --------------- Build Graph ---------------
workflow = StateGraph(GraphState)

workflow.add_node("sanitize", node_sanitize)
workflow.add_node("check_memory", node_check_memory)
workflow.add_node("analyze_patterns", node_analyze_patterns)
workflow.add_node("generate_questions", node_generate_questions)
workflow.add_node("store_memory", node_store_memory)

workflow.set_entry_point("sanitize")
workflow.add_edge("sanitize", "check_memory")

def decide_path(state: GraphState):
    if state.get("memory_result"):
        return "store_memory"
    return "analyze_patterns"

workflow.add_conditional_edges("check_memory", decide_path, {
    "analyze_patterns": "analyze_patterns",
    "store_memory": "store_memory"
})
workflow.add_edge("analyze_patterns", "generate_questions")
workflow.add_edge("generate_questions", "store_memory")
workflow.add_edge("store_memory", END)

graph = workflow.compile()

# --------------- FastAPI App ---------------
app = FastAPI(title="Question Anticipator Agent – LangGraph", version="3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/predict-questions", response_model=AgentOutput)
async def predict_questions(input_data: InputData):
    start = time.time()
    try:
        state = graph.invoke({
            "input_data": input_data.model_dump(),
            "input_hash": "",
            "memory_result": None,
            "pattern_analysis": None,
            "generated_questions": [],
            "output": {},
            "timestamp": datetime.now().isoformat()
        })
        out = state["output"]
        out["processing_time"] = time.time() - start
        return AgentOutput(**out)
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e), "timestamp": datetime.now().isoformat()})

@app.get("/health")
async def health():
    try:
        memory_count = vm.collection.count() if vm and vm.collection else 0
    except Exception:
        memory_count = 0
    return {
        "status": "healthy",
        "agent_name": "question_anticipator_agent",
        "version": "3.0",
        "memory_entries": memory_count,
        "embeddings_available": bool(vm and vm.embeddings_model),
        "llm_available": bool(question_generator.llm),
        "timestamp": datetime.now().isoformat()
    }


# --------------- Supervisor /process Endpoint ---------------
class CompletionReport(BaseModel):
    """Response model for supervisor communication."""
    message_id: str = ""
    sender: str = ""
    recipient: str = ""
    related_message_id: str = ""
    status: str = ""
    results: dict = {}


@app.post("/process", response_model=CompletionReport)
async def process_task(request: Request):
    """
    Main processing endpoint for supervisor TaskEnvelope format.
    Handles structured format from supervisor/orchestrator.
    """
    import uuid as _uuid
    start = time.time()
    
    try:
        body = await request.json()
        
        # Extract parameters from TaskEnvelope or direct format
        task_params = {}
        message_id = ""
        sender = "supervisor"
        
        if "task" in body and hasattr(body.get("task"), "get"):
            task_params = body["task"].get("parameters", {})
            message_id = body.get("message_id", "")
            sender = body.get("sender", "supervisor")
        elif "task" in body and isinstance(body["task"], dict):
            task_params = body["task"].get("parameters", {})
            message_id = body.get("message_id", "")
            sender = body.get("sender", "supervisor")
        else:
            task_params = body
        
        # Handle structured format from orchestrator
        if "agent_name" in task_params and "intent" in task_params and "payload" in task_params:
            payload = task_params["payload"]
        else:
            payload = task_params
        
        # Build InputData from payload
        input_data = _build_input_data_from_payload(payload)
        
        # Invoke the graph
        state = graph.invoke({
            "input_data": input_data.model_dump(),
            "input_hash": "",
            "memory_result": None,
            "pattern_analysis": None,
            "generated_questions": [],
            "output": {},
            "timestamp": datetime.now().isoformat()
        })
        
        out = state["output"]
        out["processing_time"] = time.time() - start
        
        # Build human-readable response
        response_message = _build_response_message(out)
        
        return CompletionReport(
            message_id=str(_uuid.uuid4()),
            sender="question_anticipator_agent",
            recipient=sender,
            related_message_id=message_id,
            status="SUCCESS",
            results={
                "response": response_message,
                "prediction_data": out
            }
        )
        
    except Exception as e:
        import uuid as _uuid
        import traceback
        print(f"Error in /process: {e}")
        traceback.print_exc()
        return CompletionReport(
            message_id=str(_uuid.uuid4()),
            sender="question_anticipator_agent",
            recipient="supervisor",
            related_message_id="",
            status="ERROR",
            results={"error": str(e)}
        )


def _build_input_data_from_payload(payload: Dict) -> InputData:
    """Convert supervisor payload to InputData format."""
    
    # Extract syllabus - can be a list or a string
    syllabus = payload.get("syllabus", [])
    if isinstance(syllabus, str):
        syllabus = [s.strip() for s in syllabus.split(",") if s.strip()]
    
    # If no syllabus provided, use a default topic-based one
    if not syllabus:
        topic = payload.get("topic") or payload.get("subject") or "General"
        syllabus = [f"Topics related to {topic}"]
    
    # Extract past papers
    past_papers_data = payload.get("past_papers", [])
    past_papers = []
    for pp in past_papers_data:
        if isinstance(pp, dict):
            past_papers.append(PastPaper(
                year=pp.get("year", "Unknown"),
                questions=pp.get("questions", [])
            ))
    
    # If no past papers, create empty list
    if not past_papers:
        past_papers = []
    
    # Extract exam pattern
    pattern_data = payload.get("exam_pattern", {})
    exam_pattern = ExamPattern(
        mcqs=int(pattern_data.get("mcqs", 10)),
        short_questions=int(pattern_data.get("short_questions", 5)),
        long_questions=int(pattern_data.get("long_questions", 3))
    )
    
    # Extract other fields
    weightage = payload.get("weightage", {})
    difficulty_preference = payload.get("difficulty_preference", payload.get("difficulty", "medium"))
    include_answers = payload.get("include_answers", False)
    
    return InputData(
        syllabus=syllabus,
        past_papers=past_papers,
        exam_pattern=exam_pattern,
        weightage=weightage,
        difficulty_preference=difficulty_preference,
        include_answers=include_answers
    )


def _build_response_message(output: Dict) -> str:
    """Build a human-readable response message from the prediction output."""
    questions = output.get("predicted_questions", [])
    processing_time = output.get("processing_time", 0)
    from_memory = output.get("from_memory", False)
    
    message = "📝 **Predicted Exam Questions**\n\n"
    
    if from_memory:
        message += "_Note: These predictions were retrieved from previous analysis._\n\n"
    
    # Group questions by type
    mcqs = [q for q in questions if q.get("question_type") == "mcq"]
    short_qs = [q for q in questions if q.get("question_type") == "short_question"]
    long_qs = [q for q in questions if q.get("question_type") == "long_question"]
    
    if mcqs:
        message += "**Multiple Choice Questions:**\n"
        for i, q in enumerate(mcqs[:5], 1):
            message += f"{i}. [{q.get('topic', 'General')}] {q.get('question_text', 'N/A')}\n"
            if q.get("options"):
                for j, opt in enumerate(q["options"]):
                    marker = "✓" if j == q.get("correct_option") else " "
                    message += f"   {chr(65+j)}. {opt} {marker}\n"
            message += f"   _Probability: {q.get('probability_score', 0)*100:.0f}%_\n\n"
    
    if short_qs:
        message += "**Short Answer Questions:**\n"
        for i, q in enumerate(short_qs[:5], 1):
            message += f"{i}. [{q.get('topic', 'General')}] {q.get('question_text', 'N/A')}\n"
            message += f"   _Difficulty: {q.get('difficulty_level', 'medium')} | Probability: {q.get('probability_score', 0)*100:.0f}%_\n\n"
    
    if long_qs:
        message += "**Long Answer Questions:**\n"
        for i, q in enumerate(long_qs[:3], 1):
            message += f"{i}. [{q.get('topic', 'General')}] {q.get('question_text', 'N/A')}\n"
            message += f"   _Difficulty: {q.get('difficulty_level', 'medium')} | Probability: {q.get('probability_score', 0)*100:.0f}%_\n\n"
    
    message += f"\n_Generated {len(questions)} predictions in {processing_time:.2f}s_"
    
    return message

# --------------- Entry ---------------
if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("Question Anticipator Agent – LangGraph Edition")
    print("=" * 60)
    print(f"LLM Provider: {LLM_PROVIDER}")
    print(f"LLM Model: {LLM_MODEL}")
    print(f"LLM Enabled: {bool(question_generator.llm)}")
    print(f"Embeddings Available: {bool(vm and vm.embeddings_model)}")
    print(f"Memory Path: {CHROMA_DB_PATH}")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)