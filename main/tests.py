from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import Post, Comment, Message, UserProfile
from django.urls import reverse

class PostModelTest(TestCase):
    """Тесты модели Post"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.post = Post.objects.create(
            author=self.user,
            title='Тестовый пост',
            content='Тестовый контент'
        )
    
    def test_post_creation(self):
        """Тест создания поста"""
        self.assertEqual(self.post.title, 'Тестовый пост')
        self.assertEqual(self.post.content, 'Тестовый контент')
        self.assertEqual(self.post.author, self.user)
    
    def test_post_likes_count(self):
        """Тест подсчёта лайков"""
        user2 = User.objects.create_user(username='user2', password='pass123')
        self.post.likes.add(user2)
        self.assertEqual(self.post.likes.count(), 1)
        
        self.post.likes.remove(user2)
        self.assertEqual(self.post.likes.count(), 0)
    
    def test_post_str(self):
        """Тест строкового представления"""
        self.assertEqual(str(self.post), 'Тестовый пост')


class CommentModelTest(TestCase):
    """Тесты модели Comment"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.post = Post.objects.create(
            author=self.user,
            title='Тест',
            content='Тест'
        )
        self.comment = Comment.objects.create(
            post=self.post,
            author=self.user,
            content='Тестовый комментарий'
        )
    
    def test_comment_creation(self):
        """Тест создания комментария"""
        self.assertEqual(self.comment.content, 'Тестовый комментарий')
        self.assertEqual(self.comment.author, self.user)
        self.assertEqual(self.comment.post, self.post)
    
    def test_comment_likes(self):
        """Тест лайков комментария"""
        user2 = User.objects.create_user(username='user2', password='pass123')
        self.comment.likes.add(user2)
        self.assertEqual(self.comment.likes.count(), 1)
    
    def test_comment_reply(self):
        """Тест ответа на комментарий"""
        reply = Comment.objects.create(
            post=self.post,
            author=self.user,
            content='Ответ',
            parent=self.comment
        )
        self.assertEqual(reply.parent, self.comment)
        self.assertIn(reply, self.comment.replies.all())
    
    def test_soft_delete(self):
        """Тест мягкого удаления"""
        self.comment.is_deleted = True
        self.comment.save()
        self.assertTrue(self.comment.is_deleted)


class MessageModelTest(TestCase):
    """Тесты модели Message"""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            password='pass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            password='pass123'
        )
        self.message = Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content='Привет!'
        )
    
    def test_message_creation(self):
        """Тест создания сообщения"""
        self.assertEqual(self.message.content, 'Привет!')
        self.assertEqual(self.message.sender, self.user1)
        self.assertEqual(self.message.receiver, self.user2)
    
    def test_message_read_status(self):
        """Тест статуса прочтения"""
        self.assertFalse(self.message.is_read)
        self.message.is_read = True
        self.message.save()
        self.assertTrue(self.message.is_read)


class PostViewTest(TestCase):
    """Тесты представлений постов"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.post = Post.objects.create(
            author=self.user,
            title='Тест',
            content='Тест'
        )
    
    def test_index_view(self):
        """Тест главной страницы"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Тест')
    
    def test_post_detail_view(self):
        """Тест страницы поста"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('post_detail', args=[self.post.id]))
        self.assertEqual(response.status_code, 200)
    
    def test_create_post_view(self):
        """Тест создания поста"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('create_post'), {
            'title': 'Новый пост',
            'content': 'Контент'
        })
        self.assertEqual(response.status_code, 302)  # Редирект
        self.assertTrue(Post.objects.filter(title='Новый пост').exists())


class CommentViewTest(TestCase):
    """Тесты представлений комментариев"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.post = Post.objects.create(
            author=self.user,
            title='Тест',
            content='Тест'
        )
    
    def test_add_comment(self):
        """Тест добавления комментария"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('add_comment', args=[self.post.id]),
            {'content': 'Новый коммент'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Comment.objects.filter(content='Новый коммент').exists())
    
    def test_delete_comment(self):
        """Тест удаления комментария"""
        comment = Comment.objects.create(
            post=self.post,
            author=self.user,
            content='Удали меня'
        )
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('delete_comment', args=[comment.id])
        )
        self.assertEqual(response.status_code, 302)
        comment.refresh_from_db()
        self.assertTrue(comment.is_deleted)


class LikeViewTest(TestCase):
    """Тесты лайков"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.post = Post.objects.create(
            author=self.user,
            title='Тест',
            content='Тест'
        )
    
    def test_like_post(self):
        """Тест лайка поста"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('like_post', args=[self.post.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['liked'])
    
    def test_unlike_post(self):
        """Тест снятия лайка"""
        self.post.likes.add(self.user)
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('like_post', args=[self.post.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        data = response.json()
        self.assertFalse(data['liked'])