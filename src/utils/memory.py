# Author: urumb
import chromadb
from chromadb.config import Settings
import uuid
from typing import List
from ..config import Config

class AuditMemory:
    def __init__(self):
        # Initialize Chroma Client with persistence
        self.client = chromadb.PersistentClient(path=Config.CHROMA_PERSIST_DIRECTORY)
        self.collection = self.client.get_or_create_collection(name="code_audits")

    def save_audit(self, code_snippet: str, finding: str, tags: List[str] = None):
        """
        Saves a code snippet and its finding to the database.
        """
        self.collection.add(
            documents=[code_snippet],
            metadatas=[{"finding": finding, "tags": ",".join(tags or [])}],
            ids=[str(uuid.uuid4())]
        )

    def retrieve_similar(self, code_snippet: str, n_results: int = 3) -> List[str]:
        """
        Retrieves similar code snippets and their past findings.
        """
        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[code_snippet],
            n_results=n_results
        )
        
        # Format results: "Code: ... \n Finding: ..."
        formatted_results = []
        if results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                meta = results['metadatas'][0][i]
                formatted_results.append(f"Similar Code:\n{doc}\n\nPast Finding:\n{meta['finding']}")
                
        return formatted_results
