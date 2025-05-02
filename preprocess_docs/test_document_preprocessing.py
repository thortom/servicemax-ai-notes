# document_processor.py
import os
import getpass
from typing import List, Dict, Optional
from pathlib import Path
import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import time

from langchain_unstructured import UnstructuredLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.evaluation import load_evaluator
from langchain.embeddings.base import Embeddings
from unstructured.partition.pdf import partition_pdf

@dataclass
class SplitterConfig:
    """Configuration for the text splitter."""
    chunk_size: int = 2000
    chunk_overlap: int = 200
    is_separator_regex: bool = False
    keep_separator: bool = True
    strip_whitespace: bool = True
    add_start_index: bool = True

class DocumentProcessor:
    def __init__(
        self,
        embedding_model: Optional[Embeddings] = None,
        splitter_config: Optional[SplitterConfig] = None,
        persist_directory: str = "./chroma_db",
    ):
        """Initialize with larger default chunk sizes."""
        self._setup_environment()
        self.embedding_model = embedding_model or OpenAIEmbeddings()
        # Increase default chunk size significantly
        self.splitter_config = splitter_config or SplitterConfig(
            chunk_size=2000,  # Increased from 500
            chunk_overlap=200  # Increased from 50
        )
        self.persist_directory = persist_directory
        self.logger = self._setup_logger()
        
    def _setup_environment(self):
        """Set up required environment variables."""
        if "UNSTRUCTURED_API_KEY" not in os.environ:
            os.environ["UNSTRUCTURED_API_KEY"] = getpass.getpass(
                "Enter your Unstructured API key: "
            )

    def _setup_logger(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def _load_document(self, file_path: str) -> List[Document]:
        """Load a single document with improved chunking."""
        try:
            self.logger.info(f"Loading document: {file_path}")
            
            # Use partition_pdf directly for more control
            elements = partition_pdf(
                filename=file_path,
                strategy="ocr_only",  # Use hi_res for better extraction
                combine_text_under_whitespace=True,  # Combine text blocks
                extract_images_in_pdf=False,  # Skip images for faster processing
                infer_table_structure=True,  # Better table handling
                max_partition=None,  # Don't limit partition size
            )
            
            # Combine elements into meaningful chunks
            docs = []
            current_page = None
            current_text = []
            
            for element in elements:
                # Get page number safely
                if hasattr(element, "metadata"):
                    metadata = element.metadata.__dict__ if hasattr(element.metadata, '__dict__') else {}
                    page_num = metadata.get('page_number', current_page)
                    
                    # Start new document on page change
                    if page_num != current_page:
                        if current_text:
                            # Create basic metadata
                            doc_metadata = {
                                'source': file_path,
                                'page_number': current_page if current_page is not None else 1,
                                'filetype': 'application/pdf'
                            }
                            
                            docs.append(Document(
                                page_content="\n".join(current_text),
                                metadata=doc_metadata
                            ))

                            print(f"docs[-1]: {docs[-1]}")
                            current_text = []
                        
                        current_page = page_num
                    
                    # Add text to current chunk if it exists
                    if hasattr(element, "text") and element.text:
                        current_text.append(element.text.strip())
            
            # Add the last document if there's remaining text
            if current_text:
                doc_metadata = {
                    'source': file_path,
                    'page_number': current_page if current_page is not None else 1,
                    'filetype': 'application/pdf'
                }
                docs.append(Document(
                    page_content="\n".join(current_text),
                    metadata=doc_metadata
                ))
            
            # Ensure we have at least one document
            if not docs:
                self.logger.warning(f"No text content extracted from {file_path}")
                # Create a minimal document to prevent downstream errors
                docs = [Document(
                    page_content="No content extracted",
                    metadata={'source': file_path, 'page_number': 1, 'filetype': 'application/pdf'}
                )]
            
            self.logger.info(f"Loaded {len(docs)} initial chunks from {file_path}")
            # Log first document content for debugging
            if docs:
                self.logger.info(f"First document content preview ({len(docs[0].page_content)} chars):")
                self.logger.info(docs[0].page_content[:500] + "..." if len(docs[0].page_content) > 500 else docs[0].page_content)
            
            return docs
            
        except Exception as e:
            self.logger.error(f"Error loading document {file_path}: {str(e)}")
            # Return a minimal document to prevent downstream errors
            return [Document(
                page_content="Error loading document",
                metadata={'source': file_path, 'page_number': 1, 'filetype': 'application/pdf'}
            )]

    def load_documents(self, file_paths: List[str]) -> List[Document]:
        """Load multiple documents in parallel."""
        if not file_paths:
            raise ValueError("No files provided")

        # Validate file paths
        for file_path in file_paths:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

        # Load documents in parallel
        start_time = time.time()
        loaded_docs = []
        
        # Process each file individually due to UnstructuredLoader's design
        for file_path in file_paths:
            docs = self._load_document(file_path)
            loaded_docs.extend(docs)
        
        processing_time = time.time() - start_time
        self.logger.info(f"Loaded {len(loaded_docs)} documents in {processing_time:.2f} seconds")
        
        # Log some sample metadata
        if loaded_docs:
            self.logger.info("Sample document metadata:")
            self.logger.info(loaded_docs[0].metadata)
        
        return loaded_docs

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents with improved chunking strategy."""
        try:
            splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                chunk_size=self.splitter_config.chunk_size,
                chunk_overlap=self.splitter_config.chunk_overlap,
                separators=["\n\n", "\n", ". ", " ", ""],  # More natural splits
                keep_separator=True,
                strip_whitespace=self.splitter_config.strip_whitespace,
                add_start_index=True
            )
            
            splits = splitter.split_documents(documents)
            
            # Log some statistics about the splits
            if splits:
                lengths = [len(s.page_content) for s in splits]
                avg_length = sum(lengths) / len(lengths)
                self.logger.info(f"""Split statistics:
                    Total splits: {len(splits)}
                    Average length: {avg_length:.0f} characters
                    Max length: {max(lengths)} characters
                    Min length: {min(lengths)} characters
                """)
                
                # Log a sample split
                self.logger.info("Sample split content:")
                self.logger.info(f"Length: {len(splits[0].page_content)} characters")
                self.logger.info("Content preview:\n" + splits[0].page_content[:500] + "...")
            
            return splits
            
        except Exception as e:
            self.logger.error(f"Error splitting documents: {str(e)}")
            raise

    def _filter_metadata(self, documents: List[Document]) -> List[Document]:
        """Filter complex metadata from documents."""
        def _clean_metadata(metadata: Dict) -> Dict:
            """Clean complex metadata structures."""
            cleaned = {}
            for key, value in metadata.items():
                # Keep only simple data types
                if isinstance(value, (str, int, float, bool)):
                    cleaned[key] = value
                # Convert lists/tuples of simple types to strings
                elif isinstance(value, (list, tuple)):
                    try:
                        cleaned[key] = str(value)
                    except:
                        continue
                # Convert dicts to string representation
                elif isinstance(value, dict):
                    try:
                        cleaned[key] = str(value)
                    except:
                        continue
            return cleaned

        filtered_docs = []
        for doc in documents:
            # Create a new document with cleaned metadata
            filtered_doc = Document(
                page_content=doc.page_content,
                metadata=_clean_metadata(doc.metadata)
            )
            filtered_docs.append(filtered_doc)
        
        # Log sample of filtered metadata
        if filtered_docs:
            self.logger.info("Sample original metadata:")
            self.logger.info(documents[0].metadata)
            self.logger.info("Sample filtered metadata:")
            self.logger.info(filtered_docs[0].metadata)
        
        return filtered_docs

    def create_vectorstore(
        self, 
        documents: List[Document], 
        collection_name: str
    ) -> Chroma:
        """Create and persist vector store from documents."""
        try:
            # Filter complex metadata before creating vectorstore
            filtered_docs = self._filter_metadata(documents)
            
            vectorstore = Chroma.from_documents(
                documents=filtered_docs,
                embedding=self.embedding_model,
                collection_name=collection_name,
                persist_directory=self.persist_directory
            )
            
            self.logger.info(f"Created vector store with {len(filtered_docs)} documents")
            return vectorstore
            
        except Exception as e:
            self.logger.error(f"Error creating vector store: {str(e)}")
            raise

    def evaluate_retrieval(
        self, 
        vectorstore: Chroma, 
        eval_questions: List[str],
        k: int = 3,
        show_full_content: bool = True
    ) -> Dict:
        """
        Evaluate the retrieval performance using multiple metrics.
        
        Args:
            vectorstore: The Chroma vector store
            eval_questions: List of evaluation questions
            k: Number of documents to retrieve
            show_full_content: Whether to include full document content in results
        """
        from langchain.evaluation import load_evaluator
        import numpy as np
        
        retriever = vectorstore.as_retriever(search_kwargs={"k": k})
        results = []
        
        # Create evaluators
        string_distance_evaluator = load_evaluator("string_distance")
        embedding_distance_evaluator = load_evaluator(
            "embedding_distance",
            embeddings=self.embedding_model
        )
        
        for question in eval_questions:
            retrieved_docs = retriever.invoke(question)
            
            doc_scores = []
            for doc in retrieved_docs:
                # String distance score
                string_eval = string_distance_evaluator.evaluate_strings(
                    prediction=doc.page_content,
                    reference=question
                )
                string_score = 1 - (string_eval["score"] / max(len(question), len(doc.page_content)))
                
                # Embedding distance score
                embedding_eval = embedding_distance_evaluator.evaluate_strings(
                    prediction=doc.page_content,
                    reference=question
                )
                embedding_score = 1 - embedding_eval["score"]
                
                # Combine scores
                combined_score = (
                    string_score * 0.3 +
                    embedding_score * 0.7
                )
                
                doc_scores.append({
                    "combined_score": combined_score,
                    "string_score": string_score,
                    "embedding_score": embedding_score,
                    "content_preview": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                    "full_content": doc.page_content,
                    "metadata": doc.metadata  # Include document metadata
                })
            
            doc_scores.sort(key=lambda x: x["combined_score"], reverse=True)
            
            avg_score = np.mean([s["combined_score"] for s in doc_scores]) if doc_scores else 0
            max_score = max((s["combined_score"] for s in doc_scores), default=0)
            
            results.append({
                "question": question,
                "num_docs_retrieved": len(retrieved_docs),
                "avg_score": avg_score,
                "max_score": max_score,
                "top_docs": doc_scores[:k]  # Keep all retrieved docs up to k
            })
        
        avg_retrieval_score = np.mean([r["avg_score"] for r in results])
        max_retrieval_score = max((r["max_score"] for r in results), default=0)
        
        return {
            "detailed_results": results,
            "aggregate_metrics": {
                "average_score": float(avg_retrieval_score),
                "max_score": float(max_retrieval_score),
                "total_questions": len(eval_questions)
            },
            "config": {
                "k": k,
                "show_full_content": show_full_content
            }
        }
    
    def process_documents(
        self, 
        file_paths: List[str], 
        collection_name: str
    ) -> Chroma:
        """Process documents end-to-end."""
        try:
            # Load documents
            documents = self.load_documents(file_paths)
            
            # # Split documents
            # splits = self.split_documents(documents)
            
            # Create vector store with filtered metadata
            vectorstore = self.create_vectorstore(documents, collection_name)
            
            return vectorstore
            
        except Exception as e:
            self.logger.error(f"Error in document processing: {str(e)}")
            raise

def display_evaluation_results(evaluation_results: Dict, show_full_content: bool = True):
    """
    Display evaluation results in a structured format.
    
    Args:
        evaluation_results: The evaluation results dictionary
        show_full_content: Whether to show full document content
    """
    print("\nRetrieval Evaluation Results:")
    print("=" * 80)
    print(f"Average Score: {evaluation_results['aggregate_metrics']['average_score']:.3f}")
    print(f"Max Score: {evaluation_results['aggregate_metrics']['max_score']:.3f}")
    print(f"Total Questions: {evaluation_results['aggregate_metrics']['total_questions']}")
    
    print("\nDetailed Results by Question:")
    print("=" * 80)
    
    for result in evaluation_results['detailed_results']:
        print(f"\nQuestion: {result['question']}")
        print(f"Number of documents retrieved: {result['num_docs_retrieved']}")
        print(f"Average Score: {result['avg_score']:.3f}")
        print(f"Max Score: {result['max_score']:.3f}")
        
        print("\nRetrieved Documents:")
        for i, doc in enumerate(result['top_docs'], 1):
            print(f"\n{i}. Relevance Scores:")
            print(f"   Combined Score: {doc['combined_score']:.3f}")
            print(f"   String Similarity: {doc['string_score']:.3f}")
            print(f"   Semantic Similarity: {doc['embedding_score']:.3f}")
            
            if 'metadata' in doc:
                print("\n   Document Metadata:")
                for key, value in doc['metadata'].items():
                    print(f"   - {key}: {value}")
            
            print("\n   Content:")
            if show_full_content:
                print("   " + doc['full_content'].replace('\n', '\n   '))
            else:
                print("   " + doc['content_preview'])
            
            print("-" * 80)

def main():
    try:
        # Configure the processor with larger chunk sizes
        splitter_config = SplitterConfig(
            chunk_size=2000,     # Larger chunks for better context
            chunk_overlap=200,   # Increased overlap to maintain continuity
            strip_whitespace=True,
            keep_separator=True,
            add_start_index=True
        )
        
        processor = DocumentProcessor(
            splitter_config=splitter_config,
            persist_directory="./my_vectorstore"
        )
        
        # Your PDF files
        file_paths = [
            r"C:\Users\thor.tomasarson\OneDrive - Marel\Documents\Work\MarelChatAI\MS2750_FilletingMachine\MS2750 Filleting machine_HM_v2.00_ENG.pdf",
            r"C:\Users\thor.tomasarson\OneDrive - Marel\Documents\Work\MarelChatAI\MS2750_FilletingMachine\MS2750 Filleting machine_SM_v2.00_ENG.pdf"
        ]
        
        # Process documents
        vectorstore = processor.process_documents(file_paths, "manual-collection")
        
        # Example evaluation questions
        eval_questions = [
            "What are the daily maintenance tasks for the filleting machine?",
            "How do I adjust the belt tension on the outfeed conveyor?",
            "What cleaning procedures should be followed after processing salmon?",
            "How do I troubleshoot issues with fish sticking to the outfeed belt?",
            "What are the safety procedures for cleaning the cutting blades?",
        ]
        
        # Evaluate retrieval
        evaluation_results = processor.evaluate_retrieval(
            vectorstore, 
            eval_questions,
            k=3,
            show_full_content=True
        )
        
        # Display results
        display_evaluation_results(evaluation_results, show_full_content=True)
        
        return vectorstore, evaluation_results

    except Exception as e:
        print(f"ERROR: {str(e)}")
        raise

if __name__ == "__main__":
    vectorstore, results = main()