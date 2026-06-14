from django.urls import path
from . import views

urlpatterns = [
    # ==================== Главная ====================
    path('', views.index, name='index'),
    
    # ==================== Аутентификация ====================
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # ==================== Профиль ====================
    # ВАЖНО: edit/ должен идти ДО <str:username>/
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/<str:username>/', views.profile_view, name='profile'),
    
    # ==================== Посты ====================
    path('post/create/', views.create_post, name='create_post'),
    path('post/<int:post_id>/', views.post_detail, name='post_detail'),
    path('post/<int:post_id>/edit/', views.edit_post, name='edit_post'),
    path('post/<int:post_id>/delete/', views.delete_post, name='delete_post'),
    path('post/<int:post_id>/like/', views.like_post, name='like_post'),
    path('post/<int:post_id>/like/', views.like_post, name='like_post'),
    path('comment/<int:comment_id>/like/', views.like_comment, name='like_comment'),
    
    # ==================== Комментарии ====================
    path('post/<int:post_id>/comment/', views.add_comment, name='add_comment'),
    path('comment/<int:comment_id>/like/', views.like_comment, name='like_comment'),
    path('comment/<int:comment_id>/edit/', views.edit_comment, name='edit_comment'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),

    # ==================== Друзья ====================
    path('friends/', views.friends_list, name='friends_list'),
    path('friends/search/', views.search_users, name='search_users'),
    path('friends/<str:username>/add/', views.send_friend_request, name='send_friend_request'),
    path('friends/accept/<int:request_id>/', views.accept_friend_request, name='accept_friend_request'),
    path('friends/decline/<int:request_id>/', views.decline_friend_request, name='decline_friend_request'),
    path('friends/<str:username>/unfriend/', views.unfriend, name='unfriend'),
    path('friends/cancel/<int:request_id>/', views.cancel_friend_request, name='cancel_friend_request'),
    path('friends/requests-count/', views.friend_requests_count, name='friend_requests_count'),
    
    # ==================== Сообщения (Чаты) ====================
    path('chat/', views.chat_list, name='chat_list'),
    path('chat/updates/', views.chat_sidebar_updates, name='chat_sidebar_updates'),
    path('chat/<str:username>/', views.chat_view, name='chat'),
    path('chat/<str:username>/send/', views.send_message, name='send_message'),
    path('chat/<str:username>/updates/', views.chat_updates, name='chat_updates'),
    
    # ==================== Сообщения (редактирование/удаление) ====================
    path('message/<int:message_id>/edit/', views.edit_message, name='edit_message'),
    path('message/<int:message_id>/delete/', views.delete_message, name='delete_message'),
    path('message/<int:message_id>/react/', views.react_to_message, name='react_to_message'),
    
    # ==================== Уведомления ====================
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/count/', views.notifications_count, name='notifications_count'),
    path('notifications/<int:notif_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    
    # ==================== Чаты - счетчик непрочитанных ====================
    path('chats/unread-count/', views.unread_chats_count, name='unread_chats_count'),
    
    # ==================== Жалобы ====================
    path('report/user/<str:username>/', views.report_user, name='report_user'),
    
    # ==================== Тема ====================
    path('set-theme/', views.set_theme, name='set_theme'),
]