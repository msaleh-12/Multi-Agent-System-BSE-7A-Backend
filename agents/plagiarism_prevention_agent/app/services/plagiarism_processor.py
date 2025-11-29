"""
Orchestration module that combines similarity detection and rephrasing
"""

import logging
from typing import List, Tuple
from datetime import datetime
from app.services.similarity_detector import SimilarityDetector
from app.services.rephrasing_engine import RephrasingEngine
from app.services.web_plagiarism_checker import WebPlagiarismChecker
from app.models.schemas import RephrasedSentence, PlagiarismSource

logger = logging.getLogger(__name__)

class PlagiarismProcessor:
    """Main processor that orchestrates similarity detection and rephrasing"""
    
    def __init__(
        self,
        similarity_model: str = "all-MiniLM-L6-v2",
        rephrasing_model: str = "Vamsi/T5_Paraphrase_Paws",
        similarity_threshold: float = 0.80
    ):
        """
        Initialize the plagiarism processor
        
        Args:
            similarity_model: Model name for similarity detection
            rephrasing_model: Model name for rephrasing
            similarity_threshold: Threshold for plagiarism detection
        """
        logger.info("Initializing PlagiarismProcessor...")
        # Lower threshold for better plagiarism detection (0.65 instead of 0.80)
        # This helps catch more cases of copied content including Wikipedia
        self.similarity_detector = SimilarityDetector(
            model_name=similarity_model,
            threshold=0.65  # Lower threshold for better detection of Wikipedia and other sources
        )
        self.rephrasing_engine = RephrasingEngine(model_name=rephrasing_model)
        self.web_checker = WebPlagiarismChecker(max_results=10)  # Check more results for better detection
        logger.info("PlagiarismProcessor initialized successfully")
    
    def process_text(
        self,
        student_text: str,
        comparison_sources: List[str] = None,
        preserve_meaning: bool = True,
        improve_originality: bool = True,
        check_online: bool = True
    ) -> Tuple[List[RephrasedSentence], float, bool, str]:
        """
        Process text: detect plagiarism online and rephrase if needed
        
        Args:
            student_text: Text submitted by student
            comparison_sources: List of reference texts to compare against
            preserve_meaning: Whether to preserve original meaning
            improve_originality: Whether to improve originality
            check_online: Whether to check for plagiarism online
            
        Returns:
            Tuple of (rephrased_sentences, pledge_percentage, is_plagiarized, feedback)
        """
        logger.info("Processing text for plagiarism detection and rephrasing")
        logger.info("Searching the ENTIRE INTERNET for plagiarism...")
        
        # Initialize variables
        plagiarism_detected = False
        overall_similarity = 0.0
        
        # Step 0: First check the entire text as a whole (for long copied passages)
        # This searches the entire internet for the full text
        if check_online and len(student_text) > 100:
            try:
                logger.info("Checking entire text against the internet...")
                overall_similarity, overall_matches = self.web_checker.check_text_online(
                    student_text, self.similarity_detector
                )
                if overall_similarity >= self.similarity_detector.threshold:
                    logger.warning(f"⚠️ HIGH SIMILARITY DETECTED for entire text: {overall_similarity:.2f}")
                    plagiarism_detected = True
                    logger.warning(f"Found {len(overall_matches)} matching sources online")
            except Exception as e:
                logger.warning(f"Error checking entire text online: {e}")
        
        # Step 1: Split text into sentences
        # Ensure NLTK data is available
        import nltk
        try:
            nltk.data.find('tokenizers/punkt_tab')
        except LookupError:
            try:
                nltk.download('punkt_tab', quiet=True)
            except:
                try:
                    nltk.data.find('tokenizers/punkt')
                except LookupError:
                    nltk.download('punkt', quiet=True)
        
        from nltk.tokenize import sent_tokenize
        sentences = sent_tokenize(student_text)
        
        logger.info(f"Checking {len(sentences)} sentences against the entire internet...")
        
        rephrased_sentences = []
        total_similarity = overall_similarity  # Start with overall text similarity
        sentence_count = 0
        plagiarized_sentences = 0
        
        # Step 2: Check each sentence for plagiarism online
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:  # Skip very short sentences
                continue
            
            # Check for plagiarism online - search the ENTIRE INTERNET
            similarity_score = 0.0
            plagiarism_source = None
            is_sentence_plagiarized = False
            
            if check_online:
                try:
                    # Search the entire internet for this sentence
                    similarity_score, match = self.web_checker.check_sentence_online(
                        sentence, self.similarity_detector
                    )
                    
                    # Use the higher of sentence-level or overall text similarity
                    similarity_score = max(similarity_score, overall_similarity * 0.9)
                    
                    # If similarity is high but below threshold, still consider it suspicious
                    # This catches Wikipedia content that might have slight variations
                    if similarity_score >= 0.60 and similarity_score < self.similarity_detector.threshold:
                        logger.warning(f"⚠️ High similarity ({similarity_score:.2f}) detected but below threshold - marking as suspicious")
                        # Mark as plagiarized if similarity is very high (0.60-0.65 range)
                        if similarity_score >= 0.60:
                            is_sentence_plagiarized = True
                            plagiarism_detected = True
                            plagiarized_sentences += 1
                            if match:
                                plagiarism_source = PlagiarismSource(
                                    url=match['url'],
                                    title=match['title'],
                                    snippet=match['snippet'],
                                    similarity=match['similarity']
                                )
                    
                    if match and similarity_score >= self.similarity_detector.threshold:
                        is_sentence_plagiarized = True
                        plagiarism_detected = True
                        plagiarized_sentences += 1
                        plagiarism_source = PlagiarismSource(
                            url=match['url'],
                            title=match['title'],
                            snippet=match['snippet'],
                            similarity=match['similarity']
                        )
                        logger.warning(f"⚠️ PLAGIARISM DETECTED in sentence: {sentence[:50]}... (similarity: {similarity_score:.2f})")
                    elif similarity_score > 0.6:  # Log high similarity even if below threshold
                        logger.info(f"High similarity ({similarity_score:.2f}) but below threshold for: {sentence[:50]}...")
                except Exception as e:
                    logger.warning(f"Error checking sentence online: {e}")
                    # Fallback: use overall similarity if available
                    similarity_score = overall_similarity if overall_similarity > 0 else 0.3
            
            # Rephrase if plagiarism detected OR if improve_originality is enabled
            # According to requirements: always rephrase to improve originality when plagiarism found
            if is_sentence_plagiarized or improve_originality:
                rephrased = self.rephrasing_engine.rephrase_sentence(sentence)
            else:
                rephrased = sentence
            
            # Create rephrased sentence object
            rephrased_sent = RephrasedSentence(
                original_sentence=sentence,
                rephrased_sentence=rephrased,
                similarity_score=similarity_score,
                is_plagiarized=is_sentence_plagiarized,
                plagiarism_source=plagiarism_source
            )
            
            rephrased_sentences.append(rephrased_sent)
            total_similarity += similarity_score
            sentence_count += 1
        
        # Calculate pledge percentage (originality score)
        if sentence_count > 0:
            avg_similarity = total_similarity / sentence_count
            pledge_percentage = max(0.0, min(100.0, (1.0 - avg_similarity) * 100))
        else:
            pledge_percentage = 100.0
        
        # Determine overall plagiarism status
        # If any sentence is plagiarized, mark the whole text as plagiarized
        # Also check if average similarity is high (indicating copied content)
        avg_similarity = total_similarity / sentence_count if sentence_count > 0 else 0.0
        
        # More aggressive detection: if average similarity is high, it's likely plagiarized
        # Wikipedia content typically has high similarity scores across sentences
        is_plagiarized = (
            plagiarism_detected or 
            (avg_similarity >= 0.65) or  # Lowered from 0.70
            (pledge_percentage < 60) or   # Lowered from 50
            (overall_similarity >= 0.65)  # Check overall text similarity too
        )
        
        logger.info(f"Plagiarism analysis - Detected: {plagiarism_detected}, Avg similarity: {avg_similarity:.2f}, Overall: {overall_similarity:.2f}, Pledge: {pledge_percentage:.2f}%")
        
        # Generate feedback based on plagiarism detection
        if plagiarism_detected:
            feedback = f"⚠️ PLAGIARISM DETECTED: {plagiarized_sentences} sentence(s) were found online. The text has been rephrased to remove plagiarism while preserving the original meaning. Please review the rephrased version below."
        elif pledge_percentage >= 80:
            feedback = "✅ No plagiarism detected. Your text shows high levels of originality."
        elif pledge_percentage >= 60:
            feedback = "✅ No plagiarism detected. Your text shows good originality."
        elif pledge_percentage >= 40:
            feedback = "⚠️ Low originality detected. The text has been rephrased to improve authenticity."
        else:
            feedback = "⚠️ Very low originality detected. The text has been rephrased to improve authenticity."
        
        logger.info(f"Processing complete. Pledge percentage: {pledge_percentage:.2f}%, Plagiarism: {plagiarism_detected}")
        
        return rephrased_sentences, pledge_percentage, is_plagiarized, feedback

