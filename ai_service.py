# ai_service.py
import os

class AIChatService:
    def __init__(self):
        self.api_key = os.environ.get('OPENAI_API_KEY')
        print(f"🤖 AI Service: {'Enhanced Mode' if self.api_key else 'Basic Mode'}")
        
    def generate_response(self, user_message, user_bill_context=None):
        # Simple rule-based responses that work without OpenAI
        user_message_lower = user_message.lower()
        
        # Bill-related questions
        if any(word in user_message_lower for word in ['bill', 'invoice', 'receipt']):
            if 'add' in user_message_lower or 'create' in user_message_lower:
                return "📝 To add a bill: Go to 'Add Bill' for manual entry or 'Upload Bill Image' for automatic OCR extraction."
            elif 'split' in user_message_lower or 'share' in user_message_lower:
                return "👥 To split a bill: Go to 'Share Bill', select a bill and friends, then assign food items. The app automatically calculates shares."
            elif 'view' in user_message_lower or 'see' in user_message_lower:
                return "📊 View all your bills in the 'Bills' section. You can see restaurant details, amounts, and dates."
            else:
                return "💰 I can help with bills! You can add bills manually or via image upload, split them with friends, and track your spending history."
        
        # Friend-related questions
        elif any(word in user_message_lower for word in ['friend', 'contact', 'person']):
            if 'add' in user_message_lower:
                return "👫 To add a friend: Go to 'Friends' → Click 'Add Friend' → Enter name and WhatsApp number."
            else:
                return "👥 Manage friends in the 'Friends' section. Add friends to easily split bills with them later."
        
        # WhatsApp sharing
        elif any(word in user_message_lower for word in ['whatsapp', 'message', 'send']):
            return "📱 WhatsApp sharing: After splitting a bill, you can send personalized messages directly from the app to each friend with their share amount."
        
        # Expense tracking
        elif any(word in user_message_lower for word in ['track', 'spending', 'expense', 'history']):
            return "📈 Track expenses in the 'Dashboard'. View total spending, bill count, and recent bills with analytics."
        
        # General help
        elif any(word in user_message_lower for word in ['help', 'how', 'what', 'can i']):
            return "❓ I can help you with:\n• Adding and managing bills\n• Splitting expenses with friends\n• WhatsApp message sharing\n• Expense tracking\n\nWhat would you like to know?"
        
        # Default response
        else:
            return "🤖 Hello! I'm your BillShare assistant! I can help with bill management, expense splitting, friend management, and WhatsApp sharing. What would you like to know?"

# Create global instance
ai_service = AIChatService()
