from django import template
from django.contrib.auth.models import User

register = template.Library()

@register.filter
def user_liked(post, user):
    if not user.is_authenticated: return False
    return post.likes.filter(id=user.id).exists()

@register.filter
def user_liked_comment(comment, user):
    if not user.is_authenticated: return False
    return comment.likes.filter(id=user.id).exists()

@register.filter
def is_liked_by(post, user):
    """Проверяет лайкнул ли пользователь пост (альтернатива)"""
    if not user.is_authenticated:
        return False
    return post.likes.filter(user=user).exists()

@register.filter
def is_comment_liked_by(comment, user):
    """Проверяет лайкнул ли пользователь комментарий"""
    if not user.is_authenticated:
        return False
    return comment.likes.filter(user=user).exists()

@register.filter
def get_user_profile(user):
    """Получает профиль пользователя"""
    try:
        return user.profile
    except:
        return None

@register.filter
def multiply(value, arg):
    """Умножение"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0