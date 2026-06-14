from django.utils.dateparse import parse_datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import datetime
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from .censor import censor_text, contains_bad_words
from django.http import JsonResponse
from .models import (
    Post, PostImage, Comment, CommentImage,
    Friendship, Message, MessageImage, Notification, UserProfile, Report
)
from .forms import CustomUserCreationForm, PostForm, CommentForm, MessageForm, ReportForm, UserProfileForm
import logging

from .models import Notification

logger = logging.getLogger(__name__)

# ==================== Auth Views ====================

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('index')
    else:
        form = CustomUserCreationForm()
    return render(request, 'main/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            next_page = request.GET.get('next', 'index')
            return redirect(next_page)
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    return render(request, 'main/login.html')

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

# ==================== Index ====================

@login_required
def index(request):
    posts = Post.objects.all().order_by('-created_at')
    return render(request, 'main/index.html', {'posts': posts})

# ==================== Posts ====================


@login_required
def create_post(request):
    """Создание нового поста"""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        images = request.FILES.getlist('images')
        
        if not title and not content and not images:
            messages.error(request, 'Добавьте заголовок, текст или фото')
            return redirect('create_post')
        
        # Цензура
        from .censor import censor_text
        content = censor_text(content)
        title = censor_text(title)
        
        post = Post.objects.create(
            author=request.user,
            title=title,
            content=content
        )
        
        for image in images:
            PostImage.objects.create(post=post, image=image)
        
        messages.success(request, 'Пост опубликован!')
        return redirect('index')
    
    return render(request, 'main/create_post.html')

@login_required
def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    comments = post.comments.filter(parent__isnull=True).order_by('-created_at')
    
    if request.method == 'POST' and request.user.is_authenticated:
        form = CommentForm(request.POST, request.FILES)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            parent_id = request.POST.get('parent_id')
            if parent_id:
                parent = get_object_or_404(Comment, id=parent_id, post=post)
                comment.parent = parent
            comment.save()
            images = request.FILES.getlist('images')
            for img in images:
                CommentImage.objects.create(comment=comment, image=img)
            messages.success(request, 'Комментарий добавлен!')
            return redirect(reverse('post_detail', args=[post_id]) + '#comments')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
            return redirect(reverse('post_detail', args=[post_id]) + '#comments')
    else:
        form = CommentForm()
    
    return render(request, 'main/post_detail.html', {'post': post, 'comments': comments, 'form': form})

@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user:
        messages.error(request, 'Это не ваш пост')
        return redirect('post_detail', post_id=post_id)
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save()
            new_images = request.FILES.getlist('images')
            for img in new_images:
                PostImage.objects.create(post=post, image=img)
            remove_ids = request.POST.getlist('remove_image_ids')
            if remove_ids:
                PostImage.objects.filter(id__in=remove_ids, post=post).delete()
            messages.success(request, 'Пост обновлён')
            return redirect('post_detail', post_id=post_id)
    else:
        form = PostForm(instance=post)
    
    existing_images = post.images.all()
    return render(request, 'main/edit_post.html', {
        'form': form,
        'post': post,
        'existing_images': existing_images,
    })

@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user:
        messages.error(request, 'У вас нет прав для удаления этого поста')
        return redirect('post_detail', post_id=post_id)
    
    # Удаляем все изображения поста
    post.images.all().delete()
    post.delete()
    
    messages.success(request, 'Пост удалён')
    return redirect('index')

# ==================== Likes ====================

@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True
    return JsonResponse({'success': True, 'liked': liked, 'count': post.likes.count()})

@login_required
def like_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if request.user in comment.likes.all():
        comment.likes.remove(request.user)
        liked = False
    else:
        comment.likes.add(request.user)
        liked = True
    return JsonResponse({'success': True, 'liked': liked, 'count': comment.likes.count()})

# ==================== Comments ====================

@login_required
def add_comment(request, post_id):
    """Добавление комментария"""
    post = get_object_or_404(Post, id=post_id)
    
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        images = request.FILES.getlist('images')
        parent_id = request.POST.get('parent_id')
        
        if not content and not images:
            messages.error(request, 'Добавьте текст или прикрепите фото')
            return redirect('post_detail', post_id=post_id)
        
        from .censor import censor_text
        content = censor_text(content)
        
        parent = None
        if parent_id:
            try:
                parent = Comment.objects.get(id=parent_id)
            except Comment.DoesNotExist:
                pass
        
        comment = Comment.objects.create(
            post=post,
            author=request.user,
            content=content,
            parent=parent
        )
        
        if images:
            for image in images:
                CommentImage.objects.create(comment=comment, image=image)
        
        if comment.author != post.author:
            Notification.objects.create(
                recipient=post.author,
                actor=request.user,
                notif_type='comment',
                text=f'{request.user.username} прокомментировал ваш пост'
            )
        
        if parent and parent.author != request.user:
            Notification.objects.create(
                recipient=parent.author,
                actor=request.user,  
                notif_type='comment_reply',
                text=f'{request.user.username} ответил на ваш комментарий'
            )
        
        messages.success(request, 'Комментарий добавлен!')
    
    return redirect('post_detail', post_id=post_id)

@login_required
def like_comment(request, comment_id):
    """Лайк комментария"""
    comment = get_object_or_404(Comment, id=comment_id)
    
    if request.user in comment.likes.all():
        comment.likes.remove(request.user)
        liked = False
    else:
        comment.likes.add(request.user)
        liked = True
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'liked': liked,
            'count': comment.likes.count()
        })
    
    return redirect('post_detail', post_id=comment.post.id)

@login_required
def delete_comment(request, comment_id):
    """Мягкое удаление комментария с сохранением структуры"""
    comment = get_object_or_404(Comment, id=comment_id, author=request.user)
    
    if request.method == 'POST':
        # Переподчиняем все ответы этого комментария его родителю
        replies = comment.replies.all()
        for reply in replies:
            reply.parent = comment.parent  # Ответы становятся ответами на родителя удалённого
            reply.save()
        
        # Мягкое удаление
        comment.is_deleted = True
        comment.content = ''
        comment.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        messages.success(request, 'Комментарий удален')
    
    return redirect('post_detail', post_id=comment.post.id)

@login_required
def edit_comment(request, comment_id):
    """Редактирование комментария"""
    comment = get_object_or_404(Comment, id=comment_id, author=request.user)
    
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        images = request.FILES.getlist('images')
        
        if content or images:
            # Цензура
            from .censor import censor_text
            comment.content = censor_text(content)
            comment.edited = True
            comment.save()
            
            # Добавляем новые картинки
            if images:
                for image in images:
                    CommentImage.objects.create(comment=comment, image=image)
            
            messages.success(request, 'Комментарий отредактирован')
    
    return redirect('post_detail', post_id=comment.post.id)

@login_required
def delete_comment(request, comment_id):
    """Мягкое удаление комментария"""
    comment = get_object_or_404(Comment, id=comment_id, author=request.user)
    
    if request.method == 'POST':
        # Просто помечаем как удалённый, НЕ переподчиняем ответы
        comment.is_deleted = True
        comment.content = ''
        comment.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        messages.success(request, 'Комментарий удален')
    
    return redirect('post_detail', post_id=comment.post.id)

@login_required
def delete_comment_image(request, image_id):
    """Удалить отдельное фото из комментария"""
    image = get_object_or_404(CommentImage, id=image_id)
    
    if image.comment.author != request.user:
        messages.error(request, 'Только автор может удалять фото')
        return redirect('post_detail', post_id=image.comment.post_id)
    
    image.delete()
    messages.success(request, 'Фото удалено')
    return redirect('post_detail', post_id=image.comment.post_id)

@login_required
def unread_chats_count(request):
    """Возвращает количество чатов с непрочитанными СООБЩЕНИЯМИ"""
    from main.models import Message
    
    # Считаем ТОЛЬКО непрочитанные СООБЩЕНИЯ (не уведомления!)
    chats_with_unread = Message.objects.filter(
        receiver=request.user,
        is_read=False
    ).values('sender').distinct().count()
    
    return JsonResponse({'count': chats_with_unread})

# ==================== Chat ====================
@login_required
def chat_list(request):
    """Список диалогов — все люди с которыми ты общался, по актуальности"""
    # Получаем всех уникальных собеседников
    user_messages = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    )
    
    # Группируем по собеседникам и находим последнее сообщение
    conversations = []
    seen_users = set()
    
    for msg in user_messages.order_by('-created_at'):
        other_user = msg.receiver if msg.sender == request.user else msg.sender
        
        if other_user.id not in seen_users:
            seen_users.add(other_user.id)
            
            # Считаем непрочитанные
            unread_count = Message.objects.filter(
                sender=other_user,
                receiver=request.user,
                is_read=False
            ).count()
            
            # Последнее сообщение с этим пользователем
            last_msg = Message.objects.filter(
                Q(sender=request.user, receiver=other_user) |
                Q(sender=other_user, receiver=request.user)
            ).order_by('-created_at').first()
            
            conversations.append({
                'user': other_user,
                'last_message': last_msg.content if last_msg else '',
                'last_message_time': last_msg.created_at if last_msg else None,
                'unread_count': unread_count,
            })
    
    return render(request, 'main/chat.html', {
        'conversations': conversations,
    })


@login_required
def chat_view(request, username):
    """Открыть диалог с пользователем"""
    other_user = get_object_or_404(User, username=username)
    
    if other_user == request.user:
        return redirect('index')
    
    # Помечаем все сообщения как прочитанные И доставленные
    Message.objects.filter(
        sender=other_user,
        receiver=request.user,
        is_read=False
    ).update(is_read=True, is_delivered=True)
    
    # Все сообщения между пользователями
    messages_query = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).order_by('created_at')
    
    messages_list = list(messages_query)
    last_message_id = messages_list[-1].id if messages_list else 0
    
    # Список диалогов для сайдбара С ПОСЛЕДНИМ СООБЩЕНИЕМ
    user_messages = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    )
    
    conversations = []
    seen_users = set()
    for msg in user_messages.order_by('-created_at'):
        chat_user = msg.receiver if msg.sender == request.user else msg.sender
        if chat_user.id not in seen_users:
            seen_users.add(chat_user.id)
            unread = Message.objects.filter(
                sender=chat_user,
                receiver=request.user,
                is_read=False
            ).count()
            
            # Последнее сообщение с этим пользователем
            last_msg = Message.objects.filter(
                Q(sender=request.user, receiver=chat_user) |
                Q(sender=chat_user, receiver=request.user)
            ).order_by('-created_at').first()
            
            conversations.append({
                'user': chat_user,
                'unread_count': unread,
                'last_message': last_msg.content if last_msg else '',
                'last_message_time': last_msg.created_at if last_msg else None,
                'last_message_sender': last_msg.sender if last_msg else None,
            })
    
    return render(request, 'main/chat.html', {
        'current_chat': other_user,
        'chat_messages': messages_list,
        'conversations': conversations,
        'last_message_id': last_message_id
    })

@login_required
def chat_updates(request, username):
    """AJAX endpoint для получения новых и изменённых сообщений"""
    other_user = get_object_or_404(User, username=username)
    last_id = int(request.GET.get('last_id', 0))
    last_updated_str = request.GET.get('last_updated', '')
    
    # Парсим дату
    last_updated = None
    if last_updated_str:
        try:
            last_updated = parse_datetime(last_updated_str)
            if last_updated and timezone.is_naive(last_updated):
                last_updated = timezone.make_aware(last_updated)
        except (ValueError, TypeError):
            last_updated = timezone.make_aware(datetime(1970, 1, 1))
    
    if not last_updated:
        last_updated = timezone.make_aware(datetime(1970, 1, 1))
    
    # НОВЫЕ сообщения (id > last_id)
    new_messages = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user),
        id__gt=last_id
    ).order_by('created_at')
    
    # ОБНОВЛЁННЫЕ сообщения (updated_at > last_updated И id <= last_id)
    updated_messages = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user),
        updated_at__gt=last_updated,
        id__lte=last_id
    ).order_by('updated_at')
    
    messages_data = []
    
    # Новые сообщения
    for msg in new_messages:
        image_urls = [img.image.url for img in msg.images.all()]
        
        messages_data.append({
            'type': 'new',
            'id': msg.id,
            'sender': msg.sender.username,
            'sender_id': msg.sender.id,
            'content': msg.content if msg.content != 'удалено' else '',
            'created_at': msg.created_at.strftime('%H:%M'),
            'is_sent': msg.sender == request.user,
            'edited': msg.edited,
            'is_deleted': msg.content == 'удалено',
            'is_read': msg.is_read,
            'is_delivered': msg.is_delivered,
            'images': image_urls,
        })
    
    # Обновлённые сообщения
    for msg in updated_messages:
        image_urls = [img.image.url for img in msg.images.all()]
        
        messages_data.append({
            'type': 'updated',
            'id': msg.id,
            'content': msg.content if msg.content != 'удалено' else '',
            'edited': msg.edited,
            'is_deleted': msg.content == 'удалено',
            'is_read': msg.is_read,
            'is_delivered': msg.is_delivered,
            'is_sent': msg.sender == request.user,
            'images': image_urls,
        })
    
    # Помечаем как прочитанные
    Message.objects.filter(
        sender=other_user,
        receiver=request.user,
        is_read=False
    ).update(is_read=True, is_delivered=True)
    
    last_msg = new_messages.last()
    
    return JsonResponse({
        'messages': messages_data,
        'last_id': last_msg.id if last_msg else last_id,
        'last_updated': timezone.localtime(timezone.now()).isoformat(),
    })

@login_required
def send_message(request, username):
    """Отправка сообщения в чат"""
    other_user = get_object_or_404(User, username=username)
    
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        images = request.FILES.getlist('images')
        
        if not content and not images:
            return JsonResponse({'error': 'Введите текст или прикрепите фото'}, status=400)
        
        # Цензура
        from .censor import censor_text
        content = censor_text(content)
        
        message = Message.objects.create(
            sender=request.user,
            receiver=other_user,
            content=content,
            is_read=False,
            is_delivered=False
        )
        
        if images:
            for image in images:
                MessageImage.objects.create(message=message, image=image)
        
        # Уведомление
        try:
            Notification.objects.create(
                recipient=other_user,
                actor=request.user,
                notif_type='message',
                text=f'{request.user.username} отправил вам сообщение'
            )
        except:
            pass
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'content': message.content,
                'created_at': message.created_at.strftime('%H:%M'),
                'is_sent': True,
            }
        })
    
    return JsonResponse({'error': 'Invalid method'}, status=405)

@login_required
def chat_sidebar_updates(request):
    """AJAX endpoint для обновления списка диалогов"""
    user_messages = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    )
    
    conversations = []
    seen_users = set()
    
    for msg in user_messages.order_by('-created_at'):
        chat_user = msg.receiver if msg.sender == request.user else msg.sender
        if chat_user.id not in seen_users:
            seen_users.add(chat_user.id)
            unread = Message.objects.filter(
                sender=chat_user,
                receiver=request.user,
                is_read=False
            ).count()
            
            last_msg = Message.objects.filter(
                Q(sender=request.user, receiver=chat_user) |
                Q(sender=chat_user, receiver=request.user)
            ).order_by('-created_at').first()
            
            avatar_url = ''
            if hasattr(chat_user, 'profile') and chat_user.profile.avatar:
                try:
                    avatar_url = chat_user.profile.avatar.url
                except:
                    avatar_url = ''
            
            is_online = False
            if hasattr(chat_user, 'profile'):
                is_online = bool(chat_user.profile.is_online)
            
            conversations.append({
                'username': chat_user.username,
                'avatar_url': avatar_url,
                'is_online': is_online,
                'unread_count': unread,
                'last_message': last_msg.content if last_msg else '',
                'last_message_time': last_msg.created_at.strftime('%H:%M') if last_msg else '',
                'last_message_sender': last_msg.sender.username if last_msg else '',
            })
    
    return JsonResponse({'conversations': conversations})

@login_required
def edit_message(request, message_id):
    """Редактирование сообщения"""
    message = get_object_or_404(Message, id=message_id, sender=request.user)
    
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        images = request.FILES.getlist('images')
        remove_images = request.POST.getlist('remove_images')
        
        from .censor import censor_text
        content = censor_text(content)
        
        message.content = content
        message.edited = True
        message.save()
        
        # Удаляем старые картинки если нужно
        if remove_images:
            for img_url in remove_images:
                try:
                    img = MessageImage.objects.get(message=message, image=img_url)
                    img.delete()
                except:
                    pass
        
        # Добавляем новые картинки
        if images:
            for image in images:
                MessageImage.objects.create(message=message, image=image)
        
        image_urls = [img.image.url for img in message.images.all()]
        
        return JsonResponse({
            'success': True,
            'content': message.content,
            'images': image_urls,
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def delete_message(request, message_id):
    """Удалить сообщение (вместе с фото)"""
    message = get_object_or_404(Message, id=message_id)
    
    if message.sender != request.user:
        return JsonResponse({'success': False, 'error': 'Нет прав'})
    
    # Сначала удаляем все фото
    message.images.all().delete()
    
    # Затем помечаем сообщение как удалённое
    message.content = 'удалено'
    message.edited = True
    message.save()
    
    return JsonResponse({'success': True})

@login_required
def react_to_message(request, message_id):
    """AJAX endpoint для реакций на сообщения"""
    message = get_object_or_404(Message, id=message_id)
    
    if request.method == 'POST':
        reaction = request.POST.get('reaction', '')
        # Здесь можно добавить логику реакций
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})

# ==================== Group Chat ====================

@login_required
def group_chats_list(request):
    group_chats = request.user.group_chats.all().order_by('-updated_at')
    pending_invites = request.user.group_invites_received.filter(status='pending')
    return render(request, 'main/group_chats_list.html', {
        'group_chats': group_chats,
        'pending_invites': pending_invites
    })

@login_required
def create_group_chat(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        if not name:
            messages.error(request, 'Название группового чата обязательно')
            return redirect('group_chats_list')
        group = GroupChat.objects.create(name=name, description=description, creator=request.user)
        group.members.add(request.user)
        messages.success(request, 'Групповой чат создан')
        return redirect('group_chat_detail', chat_id=group.id)
    return render(request, 'main/create_group_chat.html')

@login_required
def group_chat_detail(request, chat_id):
    group = get_object_or_404(GroupChat, id=chat_id)
    if request.user not in group.members.all():
        messages.error(request, 'Вы не член этого чата')
        return redirect('group_chats_list')
    messages_list = group.messages.all()[:50]
    pending_invites = group.invites.filter(status='pending')
    last_msg = group.messages.order_by('-id').first()
    return render(request, 'main/group_chat_detail.html', {
        'group': group,
        'messages': messages_list,
        'pending_invites': pending_invites,
        'last_message_id': last_msg.id if last_msg else 0
    })

@login_required
def send_group_message(request, chat_id):
    group = get_object_or_404(GroupChat, id=chat_id)
    if request.user not in group.members.all():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        images = request.FILES.getlist('images')
        if not content and not images:
            return JsonResponse({'error': 'Сообщение не может быть пусто'}, status=400)
        msg = GroupMessage.objects.create(group_chat=group, sender=request.user, content=content)
        image_urls = []
        for img in images:
            msg_img = GroupMessageImage.objects.create(message=msg, image=img)
            image_urls.append(msg_img.image.url)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message_id': msg.id,
                'message': {
                    'id': msg.id,
                    'sender_id': msg.sender_id,
                    'sender_username': msg.sender.username,
                    'content': msg.content,
                    'created_at': msg.created_at.isoformat(),
                    'images': image_urls
                }
            })
        return redirect('group_chat_detail', chat_id=chat_id)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def group_chat_updates(request, chat_id):
    try:
        group = get_object_or_404(GroupChat, id=chat_id)
        if request.user not in group.members.all():
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        since_id = int(request.GET.get('since_id', 0))
        messages_query = group.messages.filter(id__gt=since_id).order_by('created_at')
        messages_list = []
        for msg in messages_query:
            images = [img.image.url for img in msg.images.all()]
            messages_list.append({
                'id': msg.id,
                'sender_id': msg.sender_id,
                'sender_username': msg.sender.username,
                'content': msg.content,
                'created_at': msg.created_at.isoformat(),
                'is_sent': msg.sender == request.user,
                'images': images
            })
        return JsonResponse({
            'messages': messages_list,
            'last_message_id': messages_list[-1]['id'] if messages_list else since_id
        })
    except Exception as e:
        import traceback
        print(f"Group chat updates error: {e}")
        print(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def invite_to_group(request, chat_id):
    group = get_object_or_404(GroupChat, id=chat_id)
    if group.creator != request.user:
        messages.error(request, 'Только создатель может приглашать')
        return redirect('group_chat_detail', chat_id=chat_id)
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        user_to_invite = get_object_or_404(User, username=username)
        if user_to_invite in group.members.all():
            messages.error(request, 'Пользователь уже в чате')
        else:
            invite, created = GroupInvite.objects.get_or_create(
                group_chat=group,
                invitee=user_to_invite,
                defaults={'inviter': request.user}
            )
            if not created and invite.status != 'pending':
                invite.status = 'pending'
                invite.inviter = request.user
                invite.save()
            messages.success(request, f'Приглашение отправлено {username}')
    return redirect('group_chat_detail', chat_id=chat_id)

@login_required
def accept_group_invite(request, invite_id):
    invite = get_object_or_404(GroupInvite, id=invite_id, invitee=request.user)
    invite.group_chat.members.add(request.user)
    invite.status = 'accepted'
    invite.save()
    messages.success(request, f'Вы присоединились к {invite.group_chat.name}')
    return redirect('group_chat_detail', chat_id=invite.group_chat.id)

@login_required
def decline_group_invite(request, invite_id):
    invite = get_object_or_404(GroupInvite, id=invite_id, invitee=request.user)
    group_name = invite.group_chat.name
    invite.status = 'declined'
    invite.save()
    messages.success(request, f'Вы отклонили приглашение в {group_name}')
    return redirect('group_chats_list')

@login_required
def delete_group_message(request, message_id):
    message = get_object_or_404(GroupMessage, id=message_id)
    chat_id = message.group_chat.id
    if message.sender != request.user and message.group_chat.creator != request.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    message.images.all().delete()
    message.delete()
    return JsonResponse({'success': True})

@login_required
def edit_group_message(request, message_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    message = get_object_or_404(GroupMessage, id=message_id)
    if message.sender != request.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'error': 'Content required'}, status=400)
    message.content = content
    message.edited = True
    message.save()
    return JsonResponse({
        'success': True,
        'message': {
            'id': message.id,
            'content': message.content,
            'edited': message.edited,
            'updated_at': message.updated_at.isoformat()
        }
    })

@login_required
def leave_group_chat(request, chat_id):
    group = get_object_or_404(GroupChat, id=chat_id)
    if request.user == group.creator:
        messages.error(request, 'Создатель не может покидать чат')
        return redirect('group_chat_detail', chat_id=chat_id)
    group.members.remove(request.user)
    messages.success(request, f'Вы покинули {group.name}')
    return redirect('group_chats_list')

# ==================== Profile ====================

def profile_view(request, username):
    user = get_object_or_404(User, username=username)
    posts = user.posts.all().order_by('-created_at')
    is_owner = request.user == user
    
    friendship_status = None
    is_friend = False
    friendship = None
    
    if request.user.is_authenticated and not is_owner:
        friendship = Friendship.objects.filter(
            (Q(requester=request.user, receiver=user) | Q(requester=user, receiver=request.user)),
            status=Friendship.STATUS_ACCEPTED
        ).first()
        if friendship:
            is_friend = True
        else:
            sent_request = Friendship.objects.filter(
                requester=request.user, receiver=user, status=Friendship.STATUS_PENDING
            ).first()
            received_request = Friendship.objects.filter(
                requester=user, receiver=request.user, status=Friendship.STATUS_PENDING
            ).first()
            if sent_request:
                friendship_status = 'pending_sent'
                friendship = sent_request
            elif received_request:
                friendship_status = 'pending_received'
                friendship = received_request
    
    return render(request, 'main/profile.html', {
        'profile_user': user,
        'posts': posts,
        'is_owner': is_owner,
        'friendship_status': friendship_status,
        'is_friend': is_friend,
        'friendship': friendship
    })

@login_required
def edit_profile(request):
    """Редактирование профиля"""
    if request.method == 'POST':
        # Получаем данные из формы
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        bio = request.POST.get('bio', '').strip()
        interests = request.POST.get('interests', '').strip()
        
        # Обновляем пользователя
        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        
        # Обновляем профиль
        profile = user.profile
        profile.bio = bio
        profile.interests = interests
        
        # Обработка аватара
        if 'avatar' in request.FILES:
            # Удаляем старый аватар если есть
            if profile.avatar:
                profile.avatar.delete()
            profile.avatar = request.FILES['avatar']
        
        profile.save()
        
        messages.success(request, 'Профиль успешно обновлён!')
        return redirect('profile', username=user.username)
    
    # GET запрос - показываем форму
    return render(request, 'main/edit_profile.html', {
        'user': request.user,
        'user_theme': request.COOKIES.get('theme', 'light'),
    })

@login_required
def set_theme(request):
    if request.method == 'POST':
        theme = request.POST.get('theme', 'dark')
        profile = request.user.profile
        profile.theme = theme
        profile.save()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'})

# ==================== Report ====================

@login_required
def report_user(request, username):
    reported_user = get_object_or_404(User, username=username)
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.reported_user = reported_user
            report.save()
            messages.success(request, 'Жалоба отправлена')
            return redirect('profile', username=username)
        else:
            messages.error(request, 'Ошибка в форме')
    else:
        form = ReportForm()
    return render(request, 'main/report.html', {'form': form, 'reported_user': reported_user})

# ==================== Friends ====================

@login_required
def friends_list(request):
    """Страница друзей"""
    # Мои друзья
    friendships = Friendship.objects.filter(
        (Q(requester=request.user) & Q(status=Friendship.STATUS_ACCEPTED)) |
        (Q(receiver=request.user) & Q(status=Friendship.STATUS_ACCEPTED))
    )
    
    friends = []
    for f in friendships:
        friend = f.receiver if f.requester == request.user else f.requester
        friends.append(friend)
    
    # Входящие заявки (кто хочет добавить меня)
    pending_requests = Friendship.objects.filter(
        receiver=request.user,
        status=Friendship.STATUS_PENDING
    ).select_related('requester')
    
    # Исходящие заявки (кого я хочу добавить)
    sent_requests = Friendship.objects.filter(
        requester=request.user,
        status=Friendship.STATUS_PENDING
    ).select_related('receiver')
    
    context = {
        'friends': friends,
        'friends_count': len(friends),
        'pending_requests': pending_requests,
        'pending_requests_count': pending_requests.count(),
        'sent_requests': sent_requests,
        'sent_requests_count': sent_requests.count(),
    }
    
    return render(request, 'main/friends_list.html', context)

@login_required
def send_friend_request(request, username):
    """Отправить заявку в друзья"""
    other_user = get_object_or_404(User, username=username)
    
    if other_user == request.user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Нельзя добавить себя в друзья'}, status=400)
        messages.error(request, 'Нельзя добавить себя в друзья')
        return redirect('profile', username=username)
    
    # Проверяем существующую заявку
    existing = Friendship.objects.filter(
        Q(requester=request.user, receiver=other_user) |
        Q(requester=other_user, receiver=request.user)
    ).first()
    
    if existing:
        if existing.status == Friendship.STATUS_ACCEPTED:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Вы уже друзья'}, status=400)
            messages.info(request, 'Вы уже друзья')
        elif existing.status == Friendship.STATUS_PENDING:
            if existing.requester == request.user:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': 'Заявка уже отправлена'}, status=400)
                messages.info(request, 'Заявка уже отправлена')
            else:
                # Принимаем встречную заявку
                existing.status = Friendship.STATUS_ACCEPTED
                existing.accepted_at = timezone.now()
                existing.save()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'status': 'accepted'})
                messages.success(request, f'Вы теперь друзья с {other_user.username}!')
        elif existing.status == Friendship.STATUS_DECLINED:
            # Если заявка была отклонена - удаляем и создаём новую
            existing.delete()
            Friendship.objects.create(
                requester=request.user,
                receiver=other_user,
                status=Friendship.STATUS_PENDING
            )
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'status': 'pending'})
            messages.success(request, f'Заявка отправлена пользователю {other_user.username}')
        return redirect('profile', username=username)
    
    # Создаём новую заявку
    Friendship.objects.create(
        requester=request.user,
        receiver=other_user,
        status=Friendship.STATUS_PENDING
    )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'status': 'pending'})
    
    messages.success(request, f'Заявка отправлена пользователю {other_user.username}')
    return redirect('profile', username=username)

@login_required
def friend_requests_count(request):
    """Возвращает количество входящих и исходящих заявок"""
    from .models import Friendship
    
    pending_count = Friendship.objects.filter(
        receiver=request.user,
        status=Friendship.STATUS_PENDING
    ).count()
    
    sent_count = Friendship.objects.filter(
        requester=request.user,
        status=Friendship.STATUS_PENDING
    ).count()
    
    return JsonResponse({
        'pending_count': pending_count,
        'sent_count': sent_count,
        'total': pending_count + sent_count
    })

@login_required
def accept_friend_request(request, request_id):
    """Принять заявку в друзья"""
    friendship = get_object_or_404(Friendship, id=request_id, receiver=request.user, status=Friendship.STATUS_PENDING)
    friendship.status = Friendship.STATUS_ACCEPTED
    friendship.accepted_at = timezone.now()
    friendship.save()
    messages.success(request, f'Вы теперь друзья с {friendship.requester.username}!')
    return redirect('friends_list')


@login_required
def decline_friend_request(request, request_id):
    """Отклонить заявку в друзья"""
    friendship = get_object_or_404(Friendship, id=request_id, receiver=request.user, status=Friendship.STATUS_PENDING)
    friendship.status = Friendship.STATUS_DECLINED
    friendship.save()
    messages.info(request, 'Заявка отклонена')
    return redirect('friends_list')


@login_required
def unfriend(request, username):
    """Удалить из друзей"""
    other_user = get_object_or_404(User, username=username)
    
    friendship = Friendship.objects.filter(
        Q(requester=request.user, receiver=other_user) |
        Q(requester=other_user, receiver=request.user),
        status=Friendship.STATUS_ACCEPTED
    ).first()
    
    if friendship:
        friendship.delete()
        messages.success(request, f'{other_user.username} удалён из друзей')
    else:
        messages.error(request, 'Вы не друзья')
    
    return redirect('friends_list')

@login_required
def cancel_friend_request(request, request_id):
    """Отменить исходящую заявку в друзья"""
    friendship = get_object_or_404(
        Friendship, 
        id=request_id, 
        requester=request.user, 
        status=Friendship.STATUS_PENDING
    )
    friendship.delete()
    messages.success(request, 'Заявка отменена')
    return redirect('friends_list')

@login_required
def friend_requests_count(request):
    """Возвращает количество входящих и исходящих заявок"""
    from .models import Friendship
    
    pending_count = Friendship.objects.filter(
        receiver=request.user,
        status=Friendship.STATUS_PENDING
    ).count()
    
    sent_count = Friendship.objects.filter(
        requester=request.user,
        status=Friendship.STATUS_PENDING
    ).count()
    
    return JsonResponse({
        'pending_count': pending_count,
        'sent_count': sent_count,
        'total': pending_count + sent_count
    })

@login_required
def search_users(request):
    """AJAX поиск пользователей"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Only GET allowed'}, status=405)
    
    query = request.GET.get('q', '').strip()
    
    if len(query) < 1:
        return JsonResponse({'users': []})
    
    try:
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).exclude(id=request.user.id)[:20]
        
        users_data = []
        for user in users:
            try:
                profile = user.profile
                avatar_url = ''
                
                if profile:
                    if profile.avatar:
                        try:
                            avatar_url = str(profile.avatar.url)
                        except:
                            avatar_url = ''
                    
                    # Проверяем is_online как метод или свойство
                    if hasattr(profile, 'is_online'):
                        if callable(profile.is_online):
                            is_online = profile.is_online()
                        else:
                            is_online = profile.is_online
                    else:
                        is_online = False
                else:
                    is_online = False
                
                # Проверяем статус дружбы
                friendship = Friendship.objects.filter(
                    Q(requester=request.user, receiver=user) |
                    Q(requester=user, receiver=request.user)
                ).first()
                
                if friendship:
                    if friendship.status == 'accepted':
                        status = 'friend'
                    elif friendship.status == 'pending':
                        if friendship.requester == request.user:
                            status = 'pending_sent'
                        else:
                            status = 'pending_received'
                    else:
                        status = 'none'
                else:
                    status = 'none'
                
                users_data.append({
                    'id': int(user.id),
                    'username': str(user.username),
                    'first_name': str(user.first_name or ''),
                    'last_name': str(user.last_name or ''),
                    'avatar_url': str(avatar_url),
                    'is_online': bool(is_online),
                    'status': str(status),
                })
                
            except Exception as e:
                print(f"Error processing user {user.username}: {e}")
                users_data.append({
                    'id': int(user.id),
                    'username': str(user.username),
                    'first_name': str(user.first_name or ''),
                    'last_name': str(user.last_name or ''),
                    'avatar_url': '',
                    'is_online': False,
                    'status': 'none',
                })
        
        return JsonResponse({'users': users_data})
        
    except Exception as e:
        print(f"ERROR in search_users: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

# ==================== Communities ====================

@login_required
def communities_list(request):
    user_communities = request.user.user_communities.all()
    all_communities = Community.objects.exclude(members=request.user)
    return render(request, 'main/groups_list.html', {
        'user_groups': user_communities,
        'all_groups': all_communities
    })

@login_required
def create_community(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        if not name:
            messages.error(request, 'Название сообщества обязательно')
            return redirect('communities_list')
        community = Community.objects.create(name=name, description=description, creator=request.user)
        community.members.add(request.user)
        messages.success(request, 'Сообщество создано')
        return redirect('community_detail', community_id=community.id)
    return render(request, 'main/create_group.html')

@login_required
def community_detail(request, community_id):
    community = get_object_or_404(Community, id=community_id)
    is_member = community.members.filter(id=request.user.id).exists()
    can_edit = community.can_edit(request.user)
    posts = community.posts.all()[:20]
    return render(request, 'main/group_detail.html', {
        'group': community,
        'is_member': is_member,
        'can_edit': can_edit,
        'posts': posts,
    })

@login_required
def join_community(request, community_id):
    community = get_object_or_404(Community, id=community_id)
    if not community.members.filter(id=request.user.id).exists():
        community.members.add(request.user)
        Notification.objects.create(
            recipient=community.creator,
            notif_type=Notification.TYPE_COMMUNITY_INVITE,
            actor=request.user,
            text=f'{request.user.username} вступил в ваше сообщество {community.name}'
        )
        messages.success(request, 'Вы вступили в сообщество')
    return redirect('community_detail', community_id=community.id)

@login_required
def leave_community(request, community_id):
    community = get_object_or_404(Community, id=community_id)
    if community.members.filter(id=request.user.id).exists():
        if community.creator == request.user:
            messages.error(request, 'Создатель не может покинуть сообщество')
        else:
            community.members.remove(request.user)
            messages.success(request, 'Вы покинули сообщество')
    return redirect('communities_list')

@login_required
def edit_community(request, community_id):
    community = get_object_or_404(Community, id=community_id)
    if not community.can_edit(request.user):
        messages.error(request, 'Только создатель может редактировать')
        return redirect('community_detail', community_id=community.id)
    if request.method == 'POST':
        community.name = request.POST.get('name', '').strip()
        community.description = request.POST.get('description', '').strip()
        if not community.name:
            messages.error(request, 'Название обязательно')
        else:
            community.save()
            if request.FILES.get('avatar'):
                community.avatar = request.FILES['avatar']
                community.save()
            messages.success(request, 'Сообщество обновлено')
            return redirect('community_detail', community_id=community.id)
    return render(request, 'main/edit_community.html', {'group': community})

@login_required
def community_post_detail(request, post_id):
    post = get_object_or_404(CommunityPost, id=post_id)
    return render(request, 'main/community_post_detail.html', {
        'post': post,
        'community': post.community
    })

@login_required
def like_community_post(request, post_id):
    post = get_object_or_404(CommunityPost, id=post_id)
    return redirect('community_post_detail', post_id=post_id)

@login_required
def create_community_post(request, community_id):
    community = get_object_or_404(Community, id=community_id)
    if not community.members.filter(id=request.user.id).exists():
        messages.error(request, 'Только участники могут публиковать')
        return redirect('community_detail', community_id=community.id)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        if not title and not content:
            messages.error(request, 'Добавьте текст или заголовок')
        else:
            post = CommunityPost.objects.create(
                community=community,
                author=request.user,
                title=title,
                content=content,
            )
            if request.FILES.get('image'):
                post.image = request.FILES['image']
                post.save()
            for member in community.members.all():
                if member != request.user:
                    Notification.objects.create(
                        recipient=member,
                        notif_type=Notification.TYPE_COMMUNITY_POST,
                        actor=request.user,
                        text=f'{request.user.username} опубликовал в сообществе {community.name}'
                    )
            messages.success(request, 'Пост опубликован')
            return redirect('community_detail', community_id=community.id)
    return render(request, 'main/create_community_post.html', {'community': community})

# ==================== Notifications ====================

@login_required
def notifications_list(request):
    notifications = request.user.notifications.all()[:50]
    
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    
    return render(request, 'main/notifications.html', {'notifications': notifications})


@login_required
def mark_notification_read(request, notif_id):
    notif = get_object_or_404(Notification, id=notif_id, recipient=request.user)
    notif.is_read = True
    notif.save()
    return redirect('notifications_list')

@login_required
def notifications_count(request):
    """Возвращает количество непрочитанных УВЕДОМЛЕНИЙ"""
    from main.models import Notification
    
    # Считаем ТОЛЬКО уведомления (не сообщения!)
    count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    return JsonResponse({'count': count})