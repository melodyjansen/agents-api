"""
Processing file input for (query-guided) text extraction and summarization so that 
they can be used by the LLM without exceeding token limits
"""

import os
from typing import Dict, List
import pandas as pd
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from nltk.tokenize import sent_tokenize
import docx
import PyPDF2
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class FileProcessor:
    def __init__(self, llm=None):
        self.llm = llm
        self.max_tokens = 8000
        self.token_char_ratio = 0.3 
        
        # Sumy summarizers
        self.lsa_summarizer = LsaSummarizer()
        self.lexrank_summarizer = LexRankSummarizer()
        
        # Download required NLTK data
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
    
    def process_files_for_task(self, file_paths: List[str], task: str = "", task_type: str = "general") -> Dict:
        """Main entry point"""
        try:
            # Extract text from all files
            all_texts = []
            file_info = []
            
            for file_path in file_paths:
                try:
                    text, info = self._extract_text_from_file(file_path)
                    if text and text.strip():
                        all_texts.append(text)
                        file_info.append(info)
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    continue
            
            if not all_texts:
                return {"success": False, "error": "No readable content found"}
            
            # Combine all text
            combined_text = "\n\n".join([
                f"=== {info['filename']} ===\n{text}" 
                for text, info in zip(all_texts, file_info)
            ])
            
            # Choose summarization approach based on task 
            if task and task.strip():
                print(f"Doing query-focused extractive summarization for: {task}...")
                summary = self._query_focused_extractive_summarization(combined_text, task)
            else:
                print("Doing general extractive summarization...")
                summary = self._general_extractive_summarization(combined_text)

            print(f"Generated summary length: {len(summary)} chars")
            
            return {
                "success": True,
                "approach": "extractive_summarization",
                "processed_content": summary,
                "file_info": file_info,
                "task": task,
                "task_type": task_type
            }
            
        except Exception as e:
            return {"success": False, "error": f"Processing failed: {str(e)}"}
    
    def _query_focused_extractive_summarization(self, text: str, query: str) -> str:
        """Extractive summarization with query focus, using tf-idf and sentence importance"""
        try:
            print(f"Processing text of length {len(text)} chars for query: '{query}'")
            
            # Split into sentences using NLTK
            sentences = sent_tokenize(text)
            print(f"Found {len(sentences)} sentences")
            
            # Clean sentences and filter out very short ones
            clean_sentences = []
            for sentence in sentences:
                cleaned = sentence.strip()
                if len(cleaned) > 20 and not self._is_header_or_metadata(cleaned):
                    clean_sentences.append(cleaned)
            
            print(f"After filtering: {len(clean_sentences)} valid sentences")
            
            if len(clean_sentences) < 5:
                return text # Not enough content to summarize?
            
            # Create TF-IDF vectors for sentences + query
            all_text = clean_sentences + [query]
            
            vectorizer = TfidfVectorizer(
                stop_words='english',
                max_features=1000,
                ngram_range=(1, 2)  # Include bigrams for better matching
            )
            
            tfidf_matrix = vectorizer.fit_transform(all_text)
            
            # Calculate similarity to query (last item in matrix)
            query_vector = tfidf_matrix[-1:]
            sentence_vectors = tfidf_matrix[:-1]
            
            # Cosine similarity with query
            similarities = cosine_similarity(sentence_vectors, query_vector).flatten()
            
            # Also calculate sentence importance (sum of TF-IDF scores)
            sentence_importance = np.array(sentence_vectors.sum(axis=1)).flatten()
            
            # Combine query relevance and general importance
            # 70% query relevance, 30% general importance
            combined_scores = 0.7 * similarities + 0.3 * (sentence_importance / sentence_importance.max())
            
            # Get top sentences
            sentence_scores = list(zip(clean_sentences, combined_scores, range(len(clean_sentences))))
            sentence_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Select sentences with diversity (avoid too many similar sentences)
            selected_sentences = []
            total_chars = 0
            target_chars = int(self.max_tokens / self.token_char_ratio)
            
            print(f"Target characters: {target_chars}")
            
            for sentence, score, idx in sentence_scores:
                if total_chars + len(sentence) <= target_chars:
                    # Check if this sentence is too similar to already selected ones
                    if not self._is_too_similar(sentence, selected_sentences):
                        selected_sentences.append((sentence, score, idx))
                        total_chars += len(sentence)
                        
                        # Stop if we have enough content
                        if len(selected_sentences) >= 40 or total_chars >= target_chars * 0.85:
                            break
            
            print(f"Selected {len(selected_sentences)} sentences, {total_chars} chars")
            
            # Sort selected sentences by original order for better flow
            selected_sentences.sort(key=lambda x: x[2])
            
            # Format the summary
            summary_parts = [f"SUMMARY FOCUSED ON: {query}\n"]
            
            for sentence, score, idx in selected_sentences:
                summary_parts.append(sentence)
            
            final_summary = " ".join(summary_parts)
            print(f"Final summary length: {len(final_summary)} chars")
            return final_summary
            
        except Exception as e:
            print(f"Query-focused extractive summarization failed: {e}")
            # Fallback to simple keyword-based extraction
            print("Falling back to simple keyword extraction...")
            return self._simple_keyword_extraction(text, query)
    
    def _general_extractive_summarization(self, text: str) -> str:
        """General extractive summarization using Sumy with longer output"""
        try:
            parser = PlaintextParser.from_string(text, Tokenizer("english"))
            total_sentences = len(parser.document.sentences)
            
            # Calculate number of sentences for longer summary (aim for ~40% of original)
            target_sentences = max(20, min(100, int(total_sentences * 0.4)))
            
            print(f"Total sentences: {total_sentences}, targeting: {target_sentences}")
            
            # Try LSA first (usually gives better coherent summaries)
            try:
                summary_sentences = self.lsa_summarizer(parser.document, sentences_count=target_sentences)
                method = "LSA"
            except Exception as e:
                print(f"LSA failed: {e}, trying LexRank...")
                summary_sentences = self.lexrank_summarizer(parser.document, sentences_count=target_sentences)
                method = "LexRank"
            
            summary = " ".join([str(sentence) for sentence in summary_sentences])
            
            print(f"Generated {method} summary: {len(summary)} chars, {len(summary_sentences)} sentences")
            
            return summary
            
        except Exception as e:
            print(f"Sumy summarization failed: {e}")
            # Last resort: intelligent truncation
            return self._intelligent_truncation(text)
    
    def _is_header_or_metadata(self, sentence: str) -> bool:
        """Filter out headers, metadata, page numbers, etc."""
        sentence_lower = sentence.lower()
        
        # Skip obvious metadata
        skip_patterns = [
            'page ', 'vol.', 'pp.', 'doi:', 'isbn:', 'issn:',
            'references', 'bibliography', 'appendix',
            'figure ', 'table ', 'fig.', 'tab.',
            'copyright', '©', 'all rights reserved'
        ]
        
        for pattern in skip_patterns:
            if pattern in sentence_lower:
                return True
        
        # Skip if mostly numbers/symbols
        alpha_chars = sum(1 for c in sentence if c.isalpha())
        if alpha_chars < len(sentence) * 0.5:
            return True
            
        return False
    
    def _is_too_similar(self, new_sentence: str, selected_sentences: List, threshold: float = 0.7) -> bool:
        """Check if sentence is too similar to already selected ones"""
        if not selected_sentences:
            return False
        
        new_words = set(new_sentence.lower().split())
        
        for selected_sentence, _, _ in selected_sentences[-5:]:  # Check last 5 sentences
            selected_words = set(selected_sentence.lower().split())
            
            if len(new_words) > 0 and len(selected_words) > 0:
                intersection = len(new_words.intersection(selected_words))
                union = len(new_words.union(selected_words))
                jaccard_similarity = intersection / union if union > 0 else 0
                
                if jaccard_similarity > threshold:
                    return True
        
        return False
    
    def _simple_keyword_extraction(self, text: str, query: str) -> str:
        """Fallback: simple keyword-based sentence extraction"""
        sentences = text.split('. ')
        query_words = set(query.lower().split())
        
        scored_sentences = []
        for sentence in sentences:
            if len(sentence) > 30:
                sentence_words = set(sentence.lower().split())
                overlap = len(query_words.intersection(sentence_words))
                score = overlap / len(query_words) if query_words else 0
                scored_sentences.append((score, sentence))
        
        # Sort by score and take top sentences
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        
        selected_sentences = []
        total_length = 0
        target_length = int(self.max_tokens / self.token_char_ratio)
        
        for score, sentence in scored_sentences:
            if total_length + len(sentence) < target_length and score > 0:
                selected_sentences.append(sentence)
                total_length += len(sentence)
            elif len(selected_sentences) >= 30:  # Minimum number of sentences
                break
        
        return f"SUMMARY FOCUSED ON: {query}\n\n" + ". ".join(selected_sentences)
    
    def _intelligent_truncation(self, text: str) -> str:
        """Smart truncation that tries to keep complete sentences"""
        target_chars = int(self.max_tokens / self.token_char_ratio)
        
        if len(text) <= target_chars:
            return text
        
        # Find the last complete sentence within the limit
        truncated = text[:target_chars]
        last_period = truncated.rfind('.')
        
        if last_period > target_chars * 0.8:  # If we found a period reasonably close to the end
            return text[:last_period + 1]
        else:
            return truncated + "..."
    
    def _chunk_text(self, text: str, max_length: int) -> List[str]:
        """Simple text chunking"""
        chunks = []
        for i in range(0, len(text), max_length):
            chunks.append(text[i:i + max_length])
        return chunks
    
    def _extract_text_from_file(self, file_path: str):
        """Extract text from various file types"""
        filename = os.path.basename(file_path)
        file_ext = os.path.splitext(filename)[1].lower()
        
        info = {
            "filename": filename,
            "extension": file_ext,
            "size": os.path.getsize(file_path)
        }
        
        if file_ext == '.txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read(), info
        elif file_ext == '.docx':
            doc = docx.Document(file_path)
            text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            return text, info
        elif file_ext == '.pdf':
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ''
                for page in reader.pages:
                    text += page.extract_text() + '\n'
                return text, info
        elif file_ext == '.csv':
            df = pd.read_csv(file_path)
            text = f"CSV Data from {filename}:\n"
            text += f"Columns: {', '.join(df.columns)}\n"
            text += df.to_string(max_rows=100)
            return text, info
        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
            text = f"Excel Data from {filename}:\n"
            text += f"Columns: {', '.join(df.columns)}\n"
            text += df.to_string(max_rows=100)
            return text, info
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read(), info
