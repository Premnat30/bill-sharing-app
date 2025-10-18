# ai_service.py
import os
import requests
import json
import time
from flask import current_app

class AIChatService:
    def __init__(self):
        self.api_key = os.environ.get('OPENAI_API_KEY')
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.is_enabled = bool(self.api_key)
        
        print(f"🤖 AI Service Initialized: {'✅ OpenAI Enabled' if self.is_enabled else '🔄 Using Fallback Mode'}")
        if not self.is_enabled:
            print("   💡 Tip: Set OPENAI_API_KEY environment variable for enhanced AI responses")
        
    def get_bill_sharing_context(self):
        """Return context about the bill sharing app for the AI"""
        return """You are BillShare AI Assistant, a helpful AI for a bill sharing application.

Key Features to Help With:
• Bill Management: Add bills manually or upload images with OCR
• Expense Splitting: Split bills among friends with automatic tax/service charge calculations  
• Friend Management: Add friends with WhatsApp numbers for easy sharing
• WhatsApp Integration: Send personalized messages directly from the app
• Expense Tracking: View spending history and patterns

Common User Questions:
- "How to add a bill?" → Use 'Add Bill' (manual) or 'Upload Bill Image' (OCR)
- "How to split a bill?" → Go to 'Share Bill', select bill & friends, assign items
- "How to add friends?" → Use 'Friends' section with name & WhatsApp number
- "How does WhatsApp sharing work?" → Sends personalized messages with individual shares
- "How to track spending?" → View 'Bills' section and dashboard analytics

Be friendly, specific, and focus on practical bill-sharing guidance. Provide step-by-step instructions when possible."""

    def generate_response(self, user_message, user_bill_context=None):
        """Generate AI response for user message with enhanced error handling"""
        
        # Use fallback if no API key
        if not self.is_enabled:
            return self.enhanced_fallback_response(user_message)
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Prepare conversation context
            system_message = self.get_bill_sharing_context()
            
            if user_bill_context:
                system_message += f"\n\nAdditional Context: {user_bill_context}"
            
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                "max_tokens": 400,
                "temperature": 0.7,
                "top_p": 0.9
            }
            
            start_time = time.time()
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=15)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content'].strip()
                print(f"✅ AI Response generated in {response_time:.2f}s")
                return ai_response
            else:
                error_msg = f"API Error {response.status_code}: {response.text}"
                print(f"❌ {error_msg}")
                return self.enhanced_fallback_response(user_message)
                
        except requests.exceptions.Timeout:
            print("⏰ AI API timeout - using fallback")
            return self.enhanced_fallback_response(user_message)
        except requests.exceptions.ConnectionError:
            print("🔌 AI API connection error - using fallback")
            return self.enhanced_fallback_response(user_message)
        except Exception as e:
            print(f"🚨 AI API unexpected error: {e}")
            return self.enhanced_fallback_response(user_message)

    def enhanced_fallback_response(self, user_message):
        """Enhanced fallback responses with better categorization"""
        user_message_lower = user_message.lower()
        
        # Enhanced response mapping
        response_map = {
            'bill_management': {
                'triggers': ['bill', 'invoice', 'receipt', 'restaurant', 'food', 'dinner', 'lunch'],
                'add': "📝 **Adding Bills:**\n• **Manual Entry:** Go to 'Add Bill' → Enter restaurant, date, amounts\n• **Image Upload:** Use 'Upload Bill Image' → AI extracts details automatically\n• Required: Restaurant name, base amount, tax, total amount",
                'split': "👥 **Splitting Bills:**\n1. Go to 'Share Bill'\n2. Select a bill and friends\n3. Assign food items to each person\n4. App automatically calculates tax + service charge shares\n5. Send WhatsApp messages directly",
                'view': "📊 **Viewing Bills:**\n• All bills are in 'Bills' section\n• See restaurant, date, amounts, totals\n• Filter and sort your bill history",
                'default': "💰 **Bill Help:** I can assist with adding bills (manual/image), splitting with friends, tracking expenses, and WhatsApp sharing. What specific bill task do you need help with?"
            },
            'friend_management': {
                'triggers': ['friend', 'contact', 'person', 'group', 'people'],
                'default': "👫 **Friend Management:**\n• **Add Friends:** Go to 'Friends' → Add name & WhatsApp number\n• **Manage:** Edit or remove friends anytime\n• **Usage:** Select friends when splitting bills for easy sharing"
            },
            'whatsapp': {
                'triggers': ['whatsapp', 'message', 'send', 'share', 'notify'],
                'default': "📱 **WhatsApp Sharing:**\n• After splitting a bill, send personalized messages directly from the app\n• Each friend receives their specific share amount\n• Messages include food items, tax, service charge, and total\n• One-click sending to all friends"
            },
            'tracking': {
                'triggers': ['track', 'history', 'spending', 'expense', 'report', 'analytics'],
                'default': "📈 **Expense Tracking:**\n• **Dashboard:** View total spending, bill count, friend statistics\n• **Bills Section:** See all historical bills with details\n• **Trends:** Monitor your spending patterns over time"
            },
            'general_help': {
                'triggers': ['help', 'how', 'what', 'can i', 'guide', 'tutorial'],
                'default': "❓ **Quick Guide:**\n• **Bills:** Add manually or upload images\n• **Friends:** Manage contacts for easy splitting\n• **Sharing:** Split bills and send WhatsApp messages\n• **Tracking:** Monitor your spending history\n\nWhat would you like to do today?"
            }
        }

        # Check for specific actions first
        if any(word in user_message_lower for word in response_map['bill_management']['triggers']):
            if 'add' in user_message_lower or 'create' in user_message_lower or 'new' in user_message_lower:
                return response_map['bill_management']['add']
            elif 'split' in user_message_lower or 'divide' in user_message_lower or 'share' in user_message_lower:
                return response_map['bill_management']['split']
            elif 'view' in user_message_lower or 'see' in user_message_lower or 'list' in user_message_lower:
                return response_map['bill_management']['view']
            else:
                return response_map['bill_management']['default']
        
        elif any(word in user_message_lower for word in response_map['friend_management']['triggers']):
            return response_map['friend_management']['default']
        
        elif any(word in user_message_lower for word in response_map['whatsapp']['triggers']):
            return response_map['whatsapp']['default']
        
        elif any(word in user_message_lower for word in response_map['tracking']['triggers']):
            return response_map['tracking']['default']
        
        elif any(word in user_message_lower for word in response_map['general_help']['triggers']):
            return response_map['general_help']['default']
        
        else:
            return "🤖 **Hello! I'm your BillShare Assistant!**\n\nI can help you with:\n• 💰 Adding and managing bills\n• 👥 Splitting expenses with friends\n• 📱 WhatsApp message sharing\n• 📈 Expense tracking and reports\n\nWhat would you like to know about bill sharing?"

    def get_service_status(self):
        """Return current AI service status"""
        return {
            'enabled': self.is_enabled,
            'mode': 'openai' if self.is_enabled else 'fallback',
            'message': 'Enhanced AI responses available' if self.is_enabled else 'Using smart fallback responses'
        }

# Create global instance with error handling
try:
    ai_service = AIChatService()
    print(f"🎯 AI Service Ready: {ai_service.get_service_status()}")
except Exception as e:
    print(f"❌ Failed to initialize AI Service: {e}")
    # Create a basic fallback instance
    class FallbackAIService:
        def generate_response(self, message, context=None):
            return "I'm here to help with bill sharing! Currently in basic mode. Ask me about adding bills, splitting expenses, or managing friends."
    
    ai_service = FallbackAIService()
