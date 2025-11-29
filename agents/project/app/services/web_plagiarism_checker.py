"""
Web-based plagiarism checker
Searches the internet for submitted text to detect plagiarism
"""

import logging
from typing import List, Tuple, Optional
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

class WebPlagiarismChecker:
    """Checks for plagiarism by searching the web"""
    
    def __init__(self, max_results: int = 20):
        """
        Initialize the web plagiarism checker
        
        Args:
            max_results: Maximum number of search results to check per query
        """
        self.max_results = max_results
    
    def search_web(self, query: str, include_wikipedia: bool = True) -> List[dict]:
        """
        Search the web for a query using DuckDuckGo
        
        Args:
            query: Search query
            include_wikipedia: Whether to specifically search Wikipedia
            
        Returns:
            List of search results with title, body, and href
        """
        results = []
        try:
            with DDGS() as ddgs:
                # Regular search
                search_results = list(ddgs.text(query, max_results=self.max_results))
                results.extend(search_results)
                
                # Also search specifically on Wikipedia if query is substantial
                if include_wikipedia and len(query) > 20:
                    try:
                        # Search with "site:wikipedia.org" to find Wikipedia pages
                        wiki_query = f"{query} site:wikipedia.org"
                        wiki_results = list(ddgs.text(wiki_query, max_results=5))
                        results.extend(wiki_results)
                        logger.info(f"Found {len(wiki_results)} Wikipedia results for query")
                    except Exception as e:
                        logger.debug(f"Wikipedia-specific search failed: {e}")
                
                return results
        except Exception as e:
            logger.warning(f"Web search failed: {e}")
            return []
    
    def check_sentence_online(self, sentence: str, similarity_detector) -> Tuple[float, Optional[dict]]:
        """
        Check if a sentence exists online by searching the entire internet
        
        Args:
            sentence: Sentence to check
            similarity_detector: SimilarityDetector instance
            
        Returns:
            Tuple of (similarity_score, best_match_source)
        """
        try:
            # Multiple search strategies to cover the whole internet
            search_queries = []
            
            # 1. Exact phrase search with quotes (most precise)
            if len(sentence) > 20:  # Only for longer sentences
                search_queries.append(f'"{sentence}"')
            
            # 2. Key phrase search (first 100 chars if sentence is long)
            if len(sentence) > 100:
                key_phrase = sentence[:100].strip()
                search_queries.append(f'"{key_phrase}"')
                search_queries.append(key_phrase)
            else:
                search_queries.append(sentence)
            
            # 3. Search without quotes for variations
            search_queries.append(sentence)
            
            max_similarity = 0.0
            best_match = None
            all_results_checked = set()  # Avoid checking same URL twice
            
            for query in search_queries:
                try:
                    search_results = self.search_web(query)
                    
                    # Compare with search results
                    for result in search_results:
                        url = result.get('href', '')
                        if url in all_results_checked:
                            continue
                        all_results_checked.add(url)
                        
                        body = result.get('body', '')
                        title = result.get('title', '')
                        
                        # Combine title and body for better matching
                        full_text = f"{title} {body}".strip()
                        
                        if not full_text:
                            continue
                        
                        # Compare the sentence with the search result
                        similarity = similarity_detector.compute_similarity(sentence, full_text)
                        
                        # Also check if sentence is contained in the result (exact match indicator)
                        sentence_lower = sentence.lower().strip()
                        body_lower = body.lower()
                        title_lower = title.lower()
                        full_text_lower = full_text.lower()
                        
                        # Check if URL is from Wikipedia or other common sources
                        url_lower = url.lower()
                        if 'wikipedia.org' in url_lower or 'wikipedia' in url_lower:
                            # Wikipedia content - boost similarity significantly
                            similarity = max(similarity, 0.92)
                            logger.warning(f"⚠️ Wikipedia source detected: {url}")
                        
                        # If exact match found, boost similarity significantly
                        if sentence_lower in full_text_lower:
                            similarity = max(similarity, 0.95)  # High similarity for exact matches
                            logger.warning(f"⚠️ Exact match found for sentence in: {url}")
                        
                        # Check for significant overlap (70% of words match - more sensitive)
                        sentence_words = set(sentence_lower.split())
                        text_words = set(full_text_lower.split())
                        if len(sentence_words) > 0:
                            word_overlap = len(sentence_words.intersection(text_words)) / len(sentence_words)
                            if word_overlap > 0.7:  # Lowered from 0.8 to 0.7
                                similarity = max(similarity, 0.88)
                                logger.info(f"High word overlap ({word_overlap:.2f}) detected in: {url}")
                        
                        # Check if key phrases match (for Wikipedia-style content)
                        # Extract key phrases (remove citations like [4], [5], etc.)
                        sentence_clean = sentence_lower
                        import re
                        sentence_clean = re.sub(r'\[\d+\]', '', sentence_clean)  # Remove citations
                        if len(sentence_clean) > 20:
                            # Check if cleaned sentence appears in result
                            if sentence_clean in full_text_lower:
                                similarity = max(similarity, 0.93)
                                logger.warning(f"⚠️ Cleaned sentence match found in: {url}")
                        
                        if similarity > max_similarity:
                            max_similarity = similarity
                            if similarity >= similarity_detector.threshold:
                                best_match = {
                                    'url': url,
                                    'title': title,
                                    'snippet': body[:300] + '...' if len(body) > 300 else body,
                                    'similarity': similarity
                                }
                except Exception as e:
                    logger.warning(f"Error in search query '{query}': {e}")
                    continue
            
            # Log for debugging
            if max_similarity > 0.5:
                status = 'PLAGIARIZED' if max_similarity >= similarity_detector.threshold else 'CLEAN'
                logger.info(f"Sentence similarity: {max_similarity:.2f} - {status} (checked {len(all_results_checked)} unique URLs)")
            
            return max_similarity, best_match
            
        except Exception as e:
            logger.warning(f"Error checking sentence online: {e}")
            return 0.0, None
    
    def check_text_online(self, text: str, similarity_detector) -> Tuple[float, List[dict]]:
        """
        Check if text exists online by searching the entire internet with multiple strategies
        
        Args:
            text: Text to check
            similarity_detector: SimilarityDetector instance for comparing results
            
        Returns:
            Tuple of (max_similarity_score, matching_sources)
        """
        # Multiple search strategies to cover the whole internet
        search_queries = []
        
        # 1. Search for first 200 characters (key phrase)
        if len(text) > 200:
            search_queries.append(f'"{text[:200]}"')
            search_queries.append(text[:200])
        else:
            search_queries.append(f'"{text}"')
            search_queries.append(text)
        
        # 2. Search for middle section if text is long
        if len(text) > 400:
            mid_start = len(text) // 3
            mid_section = text[mid_start:mid_start + 200]
            search_queries.append(f'"{mid_section}"')
        
        # 3. Search for last section if text is long
        if len(text) > 400:
            last_section = text[-200:]
            search_queries.append(f'"{last_section}"')
        
        max_similarity = 0.0
        matching_sources = []
        all_results_checked = set()
        
        for query in search_queries:
            try:
                search_results = self.search_web(query)
                
                # Compare with search results
                for result in search_results:
                    url = result.get('href', '')
                    if url in all_results_checked:
                        continue
                    all_results_checked.add(url)
                    
                    body = result.get('body', '')
                    title = result.get('title', '')
                    full_text = f"{title} {body}".strip()
                    
                    if not full_text:
                        continue
                    
                    similarity = similarity_detector.compute_similarity(text, full_text)
                    
                    # Check for exact text match
                    text_lower = text.lower().strip()
                    full_text_lower = full_text.lower()
                    if text_lower in full_text_lower:
                        similarity = max(similarity, 0.95)
                    
                    if similarity > max_similarity:
                        max_similarity = similarity
                    
                    if similarity >= similarity_detector.threshold:
                        matching_sources.append({
                            'url': url,
                            'title': title,
                            'snippet': body[:300] + '...' if len(body) > 300 else body,
                            'similarity': similarity
                        })
            except Exception as e:
                logger.warning(f"Error in text search query: {e}")
                continue
        
        logger.info(f"Text search complete: checked {len(all_results_checked)} unique URLs, max similarity: {max_similarity:.2f}")
        return max_similarity, matching_sources
