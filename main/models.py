from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# ✅ СНАЧАЛА POST
class Post(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='posts/', blank=True, null=True)
    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True)  # ← ManyToMany для лайков
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title

class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='posts/')
    uploaded_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['uploaded_at']
    
    def __str__(self):
        return f'Image for post {self.post.id}'

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False) 
    likes = models.ManyToManyField(User, related_name='liked_comments', blank=True)  # ← ManyToMany для лайков
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f'Comment by {self.author.username} on {self.post.title}'

# Потом остальные модели
class CommentImage(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='comments/')
    uploaded_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f'Image for comment by {self.comment.author.username}'

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='reply_messages')
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    edited = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    is_delivered = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        if self.content:
            return self.content[:50]
        if self.images.exists():
            return '[Фото]'
        return 'Сообщение'

class MessageImage(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='messages/')
    uploaded_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f'Image for message {self.message.id}'

class MessageReaction(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=20, default='like')
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('message', 'user')
    
    def __str__(self):
        return f'{self.user.username} reacted to message {self.message.id}'

class Report(models.Model):
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_made')
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_received')
    reason = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    is_resolved = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Report by {self.reporter.username}'

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    interests = models.CharField(max_length=200, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    theme = models.CharField(max_length=20, default='light', choices=[('light', 'Light'), ('dark', 'Dark')])
    last_seen = models.DateTimeField(auto_now=True)
    
    def is_online(self):
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() < self.last_seen + timedelta(minutes=5)
    
    def __str__(self):
        return f'{self.user.username} profile'

class Friendship(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_DECLINED = 'declined'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Ожидает'),
        (STATUS_ACCEPTED, 'Принята'),
        (STATUS_DECLINED, 'Отклонена'),
    ]
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friend_requests_sent')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friend_requests_received')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(default=timezone.now)
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('requester', 'receiver')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.requester} -> {self.receiver} ({self.status})"
    
    def accept(self):
        self.status = self.STATUS_ACCEPTED
        self.accepted_at = timezone.now()
        self.save()

class Community(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_communities')
    avatar = models.ImageField(upload_to='communities/', blank=True, null=True)
    members = models.ManyToManyField(User, related_name='user_communities')
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def can_edit(self, user):
        return self.creator == user

class CommunityPost(models.Model):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='posts')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to='community_posts/', blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title

class Notification(models.Model):
    TYPE_FRIEND_REQUEST = 'friend_request'
    TYPE_FRIEND_ACCEPTED = 'friend_accepted'
    TYPE_COMMUNITY_INVITE = 'community_invite'
    TYPE_COMMUNITY_POST = 'community_post'
    TYPE_MESSAGE = 'message'
    TYPE_COMMENT = 'comment'
    TYPE_LIKE = 'like'
    TYPE_CHOICES = [
        (TYPE_FRIEND_REQUEST, 'Friend Request'),
        (TYPE_FRIEND_ACCEPTED, 'Friend Accepted'),
        (TYPE_COMMUNITY_INVITE, 'Community Invite'),
        (TYPE_COMMUNITY_POST, 'Community Post'),
        (TYPE_MESSAGE, 'New Message'),
        (TYPE_COMMENT, 'New Comment'),
        (TYPE_LIKE, 'New Like'),
    ]
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notif_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications_sent', null=True, blank=True)
    content_type = models.CharField(max_length=50, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    text = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.notif_type} for {self.recipient.username}'

class GroupChat(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_group_chats')
    members = models.ManyToManyField(User, related_name='group_chats')
    avatar = models.ImageField(upload_to='group_chats/', blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.name
    
    def can_edit(self, user):
        return self.creator == user

class GroupMessage(models.Model):
    group_chat = models.ForeignKey(GroupChat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_messages')
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    edited = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f'{self.sender.username} in {self.group_chat.name}'

class GroupMessageImage(models.Model):
    message = models.ForeignKey(GroupMessage, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='group_messages/')
    uploaded_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f'Image for group message {self.message.id}'

class GroupInvite(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_DECLINED = 'declined'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_DECLINED, 'Declined'),
    ]
    group_chat = models.ForeignKey(GroupChat, on_delete=models.CASCADE, related_name='invites')
    inviter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_invites_sent')
    invitee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_invites_received')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('group_chat', 'invitee')
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Invite from {self.inviter.username} to {self.group_chat.name}'