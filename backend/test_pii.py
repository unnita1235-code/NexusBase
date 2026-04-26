import asyncio
from app.ingestion.pii_scrubber import scrub_text
from app.shared.audit_logger import log_pii_detection, DB_PATH
import sqlite3

def test_scrubber():
    raw_text = """
    Hello John,
    Your new account is ready.
    Email: john.doe@example.com
    SSN: 123-45-6789
    Also, please use this AWS access key: AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
    Regards,
    Admin
    """
    
    masked_text, counts = scrub_text(raw_text)
    
    print("--- MASKED TEXT ---")
    print(masked_text)
    print("--- COUNTS ---")
    print(counts)
    
    log_pii_detection("test_document.txt", counts)
    
    # Read from sqlite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pii_audit_log ORDER BY id DESC LIMIT 3")
    rows = cursor.fetchall()
    
    print("--- SQLITE AUDIT LOG ---")
    for row in rows:
        print(row)
        
if __name__ == "__main__":
    test_scrubber()
