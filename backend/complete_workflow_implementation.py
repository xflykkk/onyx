#!/usr/bin/env python3
"""
Complete workflow implementation and enhancement
"""

import sys
import os
import time
import json
import requests
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qiniu import Auth, put_data
from onyx.configs.app_configs import (
    QINIU_ACCESS_KEY,
    QINIU_SECRET_KEY,
    QINIU_DEFAULT_BUCKET,
    QINIU_BUCKET_DOMAIN,
    QINIU_REGION
)


class DocumentUploadWorkflow:
    """Complete document upload workflow implementation"""
    
    def __init__(self, base_url: str = "http://localhost:8888"):
        self.base_url = base_url
        self.auth = Auth(QINIU_ACCESS_KEY, QINIU_SECRET_KEY)
        
    def upload_file_to_qiniu(self, file_path: str, content: str) -> bool:
        """Upload file to Qiniu OSS"""
        try:
            token = self.auth.upload_token(QINIU_DEFAULT_BUCKET)
            ret, info = put_data(token, file_path, content.encode('utf-8'))
            
            if info.status_code == 200:
                print(f"✅ File uploaded to Qiniu: {file_path}")
                return True
            else:
                print(f"❌ Failed to upload file: {info.error}")
                return False
                
        except Exception as e:
            print(f"❌ Upload error: {e}")
            return False
    
    def create_connector_via_api(
        self, 
        folder_name: str, 
        file_count: int = 1,
        crawl_url: Optional[str] = None,
        retry_count: int = 3,
        delay_seconds: int = 2
    ) -> Dict[str, Any]:
        """Create connector via upload-path API with retry logic"""
        
        oss_url = f"https://{QINIU_BUCKET_DOMAIN}/{folder_name}/"
        
        payload = {
            "doc_folder_name": folder_name,
            "doc_folder_oss_url": oss_url,
            "file_count": file_count
        }
        
        if crawl_url:
            payload["crawl_url"] = crawl_url
        
        for attempt in range(retry_count):
            try:
                print(f"📤 Attempt {attempt + 1}/{retry_count}: Calling upload-path API")
                
                response = requests.post(
                    f"{self.base_url}/doc/file/upload-path",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                result = response.json()
                
                if result.get("success", False):
                    print(f"✅ Connector created successfully")
                    return result
                else:
                    print(f"⚠️  Attempt {attempt + 1} failed: {result.get('message', 'Unknown error')}")
                    
                    if attempt < retry_count - 1:
                        print(f"⏳ Waiting {delay_seconds} seconds before retry...")
                        time.sleep(delay_seconds)
                    
            except Exception as e:
                print(f"❌ API call error: {e}")
                if attempt < retry_count - 1:
                    time.sleep(delay_seconds)
        
        print(f"❌ All {retry_count} attempts failed")
        return {"success": False, "message": "Max retries exceeded"}
    
    def check_processing_status(
        self, 
        folder_name: str, 
        max_wait_time: int = 60,
        check_interval: int = 5
    ) -> Dict[str, Any]:
        """Check processing status with polling"""
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                response = requests.get(
                    f"{self.base_url}/doc/file/status",
                    params={"doc_folder_name": folder_name}
                )
                
                result = response.json()
                status = result.get("status", "unknown")
                
                print(f"📊 Status: {status} - {result.get('desc', 'No description')}")
                
                if status == "60":  # Success
                    print("✅ Processing completed successfully")
                    return result
                elif status == "61":  # Failed
                    print("❌ Processing failed")
                    return result
                elif status == "10":  # Processing
                    print(f"⏳ Still processing... (waiting {check_interval}s)")
                    time.sleep(check_interval)
                else:  # Waiting or unknown
                    print(f"⏳ Waiting for processing to start... (waiting {check_interval}s)")
                    time.sleep(check_interval)
                    
            except Exception as e:
                print(f"❌ Status check error: {e}")
                time.sleep(check_interval)
        
        print(f"⏰ Timeout after {max_wait_time} seconds")
        return {"status": "timeout", "desc": "Processing timeout"}
    
    def run_complete_workflow(
        self, 
        folder_name: str, 
        file_name: str = "test_document.txt",
        crawl_url: Optional[str] = None
    ) -> bool:
        """Run complete upload workflow"""
        
        print("🚀 Starting Complete Upload Workflow")
        print("=" * 60)
        
        # Step 1: Create test content
        test_content = f"""Test Document for Upload Workflow

Folder: {folder_name}
File: {file_name}
Time: {time.strftime('%Y-%m-%d %H:%M:%S')}

Content:
- This is a test document for validating the upload workflow
- It contains sample text for indexing
- The document should be processed and indexed
- Status should change from 00 -> 10 -> 60

Workflow Steps:
1. Upload file to Qiniu OSS
2. Call POST /doc/file/upload-path to create connector
3. Wait for indexing to complete
4. Verify final status

End of test document.
"""
        
        # Step 2: Upload file to Qiniu
        print("\n📋 Step 1: Upload file to Qiniu OSS")
        file_path = f"{folder_name}/{file_name}"
        
        if not self.upload_file_to_qiniu(file_path, test_content):
            print("❌ Failed to upload file, aborting workflow")
            return False
        
        # Step 3: Wait a moment for file to be available
        print("\n⏳ Waiting 3 seconds for file to be available...")
        time.sleep(3)
        
        # Step 4: Create connector
        print("\n📋 Step 2: Create connector via API")
        connector_result = self.create_connector_via_api(
            folder_name=folder_name,
            file_count=1,
            crawl_url=crawl_url,
            retry_count=3,
            delay_seconds=5
        )
        
        if not connector_result.get("success", False):
            print("❌ Failed to create connector, aborting workflow")
            return False
        
        # Step 5: Monitor processing status
        print("\n📋 Step 3: Monitor processing status")
        final_status = self.check_processing_status(
            folder_name=folder_name,
            max_wait_time=120,
            check_interval=10
        )
        
        # Step 6: Summary
        print("\n📋 Step 4: Workflow Summary")
        print("=" * 40)
        print(f"File Path: {file_path}")
        print(f"Connector ID: {connector_result.get('connector_id', 'None')}")
        print(f"CC Pair ID: {connector_result.get('cc_pair_id', 'None')}")
        print(f"Final Status: {final_status.get('status', 'unknown')}")
        print(f"Description: {final_status.get('desc', 'No description')}")
        
        success = final_status.get("status") == "60"
        print(f"\n🎯 Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
        
        return success


def main():
    """Main function to run workflow tests"""
    
    workflow = DocumentUploadWorkflow()
    
    # Test 1: Basic workflow
    print("🧪 Test 1: Basic Upload Workflow")
    folder_name = f"crawl_results/test_workflow_{int(time.time())}"
    success = workflow.run_complete_workflow(
        folder_name=folder_name,
        file_name="test_document.txt",
        crawl_url="https://example.com/test"
    )
    
    if success:
        print("\n✅ Workflow test completed successfully!")
    else:
        print("\n❌ Workflow test failed!")
    
    # Test 2: Validate the workflow explanation
    print("\n" + "=" * 80)
    print("📚 Workflow Explanation Validation")
    print("=" * 80)
    
    print("""
✅ CORRECT WORKFLOW PROCESS:

1. 📁 File Upload to Qiniu OSS
   - External process uploads files to Qiniu cloud storage
   - Files are stored with folder prefix (e.g., crawl_results/task_id/)
   - This can be done via web interface, API, or automated scripts

2. 📤 POST /doc/file/upload-path API Call
   - Notifies the system about new files in a folder
   - Creates a Connector in the database
   - Creates credentials for Qiniu access
   - Creates a ConnectorCredentialPair (CC Pair)
   - Triggers the indexing pipeline

3. ⏳ Indexing Process (Async)
   - Celery background tasks process the files
   - Files are downloaded from Qiniu
   - Text content is extracted and chunked
   - Embeddings are generated
   - Content is stored in Vespa search index

4. 📊 GET /doc/file/status API Call
   - Checks the processing status
   - Returns status codes:
     * 00: Waiting/Not Found (no connector created)
     * 10: Processing (indexing in progress)
     * 60: Success (indexing completed)
     * 61: Failed (indexing failed)

5. 🔍 Search/Chat Integration
   - Indexed documents become searchable
   - Can be used in chat responses
   - Retrievable through document search APIs

❌ COMMON ISSUES:
- Calling status API before upload-path API (returns 00)
- Files not actually uploaded to Qiniu (API returns "No files found")
- Bucket configuration mismatch
- Insufficient permissions for Qiniu access
- Async indexing not completing (stuck at status 10)

💡 IMPROVEMENTS NEEDED:
- Better error handling and retry logic
- Webhook notifications for indexing completion
- Async status updates via WebSocket
- Better validation of OSS URLs and credentials
- Monitoring and alerting for failed indexing
""")


if __name__ == "__main__":
    main()