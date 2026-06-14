import json
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from .models import Message, MessageImage

User = get_user_model()

def make_group_name(user_id, other_id):
    first, second = sorted([user_id, other_id])
    return f'chat_{first}_{second}'

class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.other_username = self.scope['url_route']['kwargs'].get('username')
        self.other_user = await sync_to_async(User.objects.filter(username=self.other_username).first)()
        
        if not self.other_user:
            await self.close()
            return

        self.room_group_name = make_group_name(self.user.id, self.other_user.id)
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        message_type = content.get('type')
        
        if message_type == 'typing':
            is_typing = bool(content.get('is_typing'))
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_message',
                    'username': self.user.username,
                    'is_typing': is_typing,
                }
            )
            return

        if message_type == 'message':
            text = (content.get('content') or '').strip()
            if not text:
                return

            reply_to_id = content.get('reply_to')
            message = await self.create_message(text, reply_to_id)
            payload = await self.serialize_message(message)
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': payload,
                }
            )

    async def chat_message(self, event):
        await self.send_json({
            'type': 'message',
            'message': event['message'],
        })

    async def typing_message(self, event):
        if event['username'] == self.user.username:
            return
        await self.send_json({
            'type': 'typing',
            'username': event['username'],
            'is_typing': event['is_typing'],
        })

    @sync_to_async
    def create_message(self, content, reply_to_id):
        message = Message(sender=self.user, receiver=self.other_user, content=content)
        if reply_to_id:
            reply = Message.objects.filter(id=reply_to_id).first()
            if reply:
                message.reply_to = reply
        message.save()
        return message

    @sync_to_async
    def serialize_message(self, message):
        return {
            'id': message.id,
            'content': message.content,
            'sender': message.sender.username,
            'is_sent': message.sender_id == self.user.id,
            'created_at': message.created_at.strftime('%H:%M'),
            'edited': message.edited,
            'reply_to': { 
                'sender': message.reply_to.sender.username,
                'text': message.reply_to.content[:120],
            } if message.reply_to else None,
            'images': [attachment.image.url for attachment in message.images.all()],
        }
