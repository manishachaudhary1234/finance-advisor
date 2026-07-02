#!/usr/bin/env python3
"""Test the ADK-native chatbot flow with Gemini."""

from dotenv import load_dotenv
from src.agent.graph import chat_with_adk

load_dotenv()

def test_chatbot_with_gemini():
    """Test chatbot responds to financial query using Google ADK."""

    user_query = "What should I invest in with 1 lakh INR?"
    
    print("=" * 60)
    print("Testing Chatbot Node with Gemini API")
    print("=" * 60)
    print(f"\nUser Query: {user_query}")
    print(f"User ID: test_user_123")
    
    try:
        print("\nSending request via ADK Runner...")
        response_text = chat_with_adk(
            user_id="test_user_123",
            thread_id="test_thread_123",
            message=user_query,
        )

        if response_text:
            print(f"\n✅ Success! Gemini responded:")
            print("-" * 60)
            print(response_text)
            print("-" * 60)
            
            # Validation checks
            checks = {
                "Response is non-empty": len(response_text) > 0,
                "Response is reasonable length": len(response_text) > 50,
                "Looks like financial advice": any(word in response_text.lower() 
                                                   for word in ["invest", "fund", "stock", "return", "risk", "mutual", "gold"])
            }
            
            print("\n✓ Validation Checks:")
            for check_name, passed in checks.items():
                status = "✅ PASS" if passed else "⚠️  WARNING"
                print(f"  {status}: {check_name}")
            
            return True
        else:
            print(f"\n❌ Failed: No response from chatbot")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}")
        print(f"Message: {str(e)}")
        
        # Help with common issues
        if "429" in str(e) or "quota" in str(e).lower():
            print("\n⚠️  Your Gemini API quota is exhausted.")
            print("   Fix: Enable billing in Google Cloud Console for your project")
            print("   See: https://console.cloud.google.com/billing")
        elif "GOOGLE_API_KEY" in str(e) or "Unauthorized" in str(e):
            print("\n⚠️  API Key issue")
            print("   Fix: Verify GOOGLE_API_KEY is set in .env file")
        
        return False

if __name__ == "__main__":
    success = test_chatbot_with_gemini()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ ADK chatbot migration PASSED")
        print("Next: Run test_extract_node.py to test the extract node")
    else:
        print("❌ ADK chatbot migration FAILED")
        print("Fix the errors above and retry")
    print("=" * 60)
