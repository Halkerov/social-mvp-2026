from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Post, Comment, Message, Report, UserProfile, CommentImage, PostImage, MessageImage

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True, label='Имя', max_length=30)
    last_name = forms.CharField(required=True, label='Фамилия', max_length=150)
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Заголовок поста'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Текст поста'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get('content')
        images = self.files.getlist('images')
        
        if not content and not images:
            raise forms.ValidationError("Добавьте текст или изображения")
        
        return cleaned_data

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Напишите комментарий...'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get('content')
        images = self.files.getlist('images')
        
        if not content and not images:
            raise forms.ValidationError("Добавьте текст или изображения")
        
        return cleaned_data

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Введите сообщение...',
                'style': 'resize: none;',
                'required': False,
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get('content')
        images = self.files.getlist('images')
        
        if not content and not images:
            raise forms.ValidationError("Введите текст или выберите изображение")
        
        return cleaned_data

class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Причина жалобы'}),
        }

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['bio', 'interests', 'avatar', 'theme']
        