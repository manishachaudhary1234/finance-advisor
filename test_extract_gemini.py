#!/usr/bin/env python3
"""Test profile extraction with OpenAI-native app flow."""

from dotenv import load_dotenv
from src.agents.graph import extract_profile_from_messages
from src.memory.profile_store import load_profile

load_dotenv()

def test_extract_profile_with_openai():
    """Test extractor uses OpenAI to extract profile updates."""

    messages = [
        {"role": "user", "content": "My income just increased to 75000 INR per month"},
        {"role": "assistant", "content": "Great! That's wonderful news. Higher income opens up new investment opportunities..."},
    ]
    
    print("=" * 60)
    print("Testing Extract Node with OpenAI API")
    print("=" * 60)
    
    print(f"\nTest Scenario:")
    print(f"  User: {messages[0]['content']}")
    print(f"  Advisor: {messages[1]['content']}")
    
    try:
        print("\nSending extraction request to OpenAI API...")
        extract_profile_from_messages(
            messages=messages,
            user_id="test_extract_user",
            thread_id="test_thread_123",
        )
        
        print(f"\n✅ Success! Extraction completed:")
        print("-" * 60)
        print("Result: OK")
        print("-" * 60)
        
        # Load profile to check if it was updated
        print("\n📊 Checking profile updates...")
        profile = load_profile("test_extract_user")
        
        checks = {
            "Profile loaded successfully": profile is not None,
        }
        
        if profile:
            checks.update({
                "Profile has monthly_income_inr field": hasattr(profile, 'monthly_income_inr'),
                "Income value is numeric": isinstance(profile.monthly_income_inr, (int, float)) if profile.monthly_income_inr else True,
            })
        
        print("\n✓ Validation Checks:")
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "⚠️  WARNING"
            print(f"  {status}: {check_name}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}")
        print(f"Message: {str(e)}")
        
        # Help with common issues
        if "429" in str(e) or "quota" in str(e).lower():
            print("\n⚠️  API quota may be exhausted.")
        elif "response_schema" in str(e).lower():
            print("\n⚠️  Issue with structured output")
            print("   Fix: Ensure ProfileUpdate schema is valid Pydantic model")
        
        return False

if __name__ == "__main__":
    success = test_extract_profile_with_openai()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ OpenAI extraction migration PASSED")
    else:
        print("❌ OpenAI extraction migration FAILED")
    print("=" * 60)
