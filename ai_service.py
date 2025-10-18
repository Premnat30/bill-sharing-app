# ai_service.py
import os
import requests
import json
from flask import current_app

class AIChatService:
    def __init__(self):
        self.api_key = os.environ.get('OPENAI_API_KEY')
        self.base_url = "https://api.openai.com/v1/chat/completions"
        
    def get_bill_sharing_context(self):
        """Return context about the bill sharing app for the AI"""
        return """
        You are BillShare AI Assistant, a helpful AI for a bill sharing application. 
        
        About BillShare:
        - Helps users split restaurant bills with friends
        - Users can upload bill images with OCR extraction
        - Supports WhatsApp sharing for bill splits
        - Tracks expenses and friend groups
        
        Key Features:
        1. Add bills manually or via image upload
        2. Split bills among friends with tax and service charge calculations
        3. Send WhatsApp messages to friends with their share amounts
        4. Track spending history and friend lists
        
        Common Questions:
        - How to add a bill? Use "Add Bill" or "Upload Bill Image"
        - How to split bills? Go to "Share Bill" and select friends
        - How to add friends? Use "Friends" section
        - How WhatsApp sharing works? It sends personalized messages with amounts
        
        Be friendly, helpful, and specific about bill sharing. If users ask about bills, 
        expenses, or sharing, provide detailed guidance based on the app's features.
        """
    
    def generate_response(self, user_message, user_bill_context=None):
        """Generate AI response for user message"""
        
        # If no API key, use a fallback response system
        if not self.api_key:
            return self.fallback_response(user_message)
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Prepare conversation context
            system_message = self.get_bill_sharing_context()
            
            if user_bill_context:
                system_message += f"\n\nUser's Bill Context: {user_bill_context}"
            
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                "max_tokens": 500,
                "temperature": 0.7
            }
            
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                return self.fallback_response(user_message)
                
        except Exception as e:
            print(f"AI API Error: {e}")
            return self.fallback_response(user_message)
    
    def fallback_response(self, user_message):
        """Fallback responses when AI service is unavailable"""
        user_message_lower = user_message.lower()
        
        # Bill-related questions
        if any(word in user_message_lower for word in ['bill', 'invoice', 'receipt']):
            if 'add' in user_message_lower or 'create' in user_message_lower:
                return "To add a bill, go to 'Add Bill' for manual entry or 'Upload Bill Image' to use our AI extraction. You'll need the restaurant name, date, and amounts."
            elif 'split' in user_message_lower or 'share' in user_message_lower:
                return "To split a bill, go to 'Share Bill', select a bill and friends, then assign food items. The app automatically calculates tax and service charge shares."
            else:
                return "I can help with bills! You can add bills manually, upload images, split them with friends, or track your spending history."
        
        # Friend-related questions
        elif any(word in user_message_lower for word in ['friend', 'contact', 'person']):
            return "Manage friends in the 'Friends' section. Add friends with their name and WhatsApp number to easily split bills with them later."
        
        # WhatsApp sharing
        elif 'whatsapp' in user_message_lower or 'message' in user_message_lower:
            return "After splitting a bill, you can send WhatsApp messages directly from the app. Each friend receives a personalized message with their share amount."
        
        # General help
        elif any(word in user_message_lower for word in ['help', 'how', 'what', 'can i']):
            return "I can help you with: adding bills, splitting expenses, managing friends, WhatsApp sharing, and tracking your spending. What would you like to know?"
        
        # Default response
        else:
            return "I'm here to help with bill sharing! You can ask me about adding bills, splitting expenses with friends, WhatsApp sharing, or managing your expenses."

# Create global instance
ai_service = AIChatService()
