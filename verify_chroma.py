# Author: urumb
from src.utils.memory import AuditMemory
import time

def verify_persistence():
    print("--- Verifying ChromaDB Persistence ---")
    memory = AuditMemory()
    
    # Test Data
    test_code = "def test(): pass"
    test_finding = "Test finding for persistence verification."
    
    # Save
    print("Saving test audit...")
    memory.save_audit(test_code, test_finding, tags=["test"])
    
    # Wait a moment
    time.sleep(1)
    
    # Verify Retrieval
    print("Retrieving...")
    results = memory.retrieve_similar(test_code, n_results=1)
    
    if results:
        print("✅ SUCCESS: Retrieved saved audit.")
        print(results[0])
    else:
        print("❌ FAILURE: Could not retrieve saved audit.")

if __name__ == "__main__":
    verify_persistence()
