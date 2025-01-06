import logging
import requests
from openai import OpenAI
from django.conf import settings
from ..utils import PromptManager

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.prompt_manager = PromptManager()

    def generate_email(self, transcription: str) -> dict:
        """Generate email content using GPT"""
        try:
            email_prompt = self.prompt_manager.load_prompt('email_prompt.txt')
            response = self.prompt_manager.ask_chatgpt(
                self.openai_client, 
                f"""
                {email_prompt}
                Conversation: {transcription}
                Please generate a professional email based on this conversation.
                Format the response as JSON with "to", "subject", and "body" fields.
                """
            )
            return json.loads(response)
        except Exception as e:
            logger.error(f"Error generating email: {str(e)}")
            raise

    def send_email(self, email_data: dict) -> bool:
        """Send email using Microsoft Graph API"""
        try:
            # Get Outlook access token
            token_url = f'https://login.microsoftonline.com/{settings.MS_TENANT_ID}/oauth2/v2.0/token'
            token_data = {
                'grant_type': 'client_credentials',
                'client_id': settings.MS_CLIENT_ID,
                'client_secret': settings.MS_CLIENT_SECRET,
                'scope': 'https://outlook.office.com/mail.send'
            }
            
            token_response = requests.post(token_url, data=token_data)
            access_token = token_response.json()['access_token']
            
            # Send email
            email_url = 'https://outlook.office.com/api/v2.0/me/sendmail'
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            email_body = {
                'Message': {
                    'Subject': email_data.get('subject', 'Meeting Follow-up'),
                    'Body': {
                        'ContentType': 'HTML',
                        'Content': email_data.get('body', '')
                    },
                    'ToRecipients': [
                        {'EmailAddress': {'Address': email_data.get('to', '')}}
                    ]
                },
                'SaveToSentItems': True
            }
            
            result = requests.post(email_url, headers=headers, json=email_body)
            return result.status_code == 202
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            raise 