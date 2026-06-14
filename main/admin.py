from django.contrib import admin
from .models import (
    Post, PostImage, Comment, CommentImage,
    Message, MessageImage, MessageReaction,
    Report, UserProfile, Friendship,
    Community, CommunityPost, Notification,
    GroupChat, GroupMessage, GroupMessageImage, GroupInvite
)

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_at')
    search_fields = ('title', 'author__username')

@admin.register(PostImage)
class PostImageAdmin(admin.ModelAdmin):
    list_display = ('post', 'uploaded_at')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'content', 'created_at', 'parent')
    search_fields = ('author__username', 'content')

@admin.register(CommentImage)
class CommentImageAdmin(admin.ModelAdmin):
    list_display = ('comment', 'uploaded_at')

# УДАЛИ ЭТО:
# @admin.register(CommentLike)
# class CommentLikeAdmin(admin.ModelAdmin):
#     list_display = ('comment', 'user', 'created_at')

# УДАЛИ ЭТО:
# @admin.register(Like)
# class LikeAdmin(admin.ModelAdmin):
#     list_display = ('post', 'user', 'created_at')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'content', 'created_at', 'is_read', 'is_delivered')
    list_filter = ('is_read', 'is_delivered')

@admin.register(MessageImage)
class MessageImageAdmin(admin.ModelAdmin):
    list_display = ('message', 'uploaded_at')

@admin.register(MessageReaction)
class MessageReactionAdmin(admin.ModelAdmin):
    list_display = ('message', 'user', 'reaction_type', 'created_at')

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'reported_user', 'reason', 'created_at', 'is_resolved')
    list_filter = ('is_resolved',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio', 'theme', 'last_seen')

@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ('requester', 'receiver', 'status', 'created_at', 'accepted_at')
    list_filter = ('status',)

@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'created_at')

@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'community', 'author', 'created_at')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'notif_type', 'actor', 'text', 'is_read', 'created_at')
    list_filter = ('is_read', 'notif_type')

@admin.register(GroupChat)
class GroupChatAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'created_at')

@admin.register(GroupMessage)
class GroupMessageAdmin(admin.ModelAdmin):
    list_display = ('group_chat', 'sender', 'content', 'created_at')

@admin.register(GroupMessageImage)
class GroupMessageImageAdmin(admin.ModelAdmin):
    list_display = ('message', 'uploaded_at')

@admin.register(GroupInvite)
class GroupInviteAdmin(admin.ModelAdmin):
    list_display = ('group_chat', 'inviter', 'invitee', 'status', 'created_at')
    list_filter = ('status',)