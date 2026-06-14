from django.apps import AppConfig
from django.db import connection
import os

class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'
    
    def ready(self):
        # Выполняем кастомный SQL только если файл существует
        sql_file = os.path.join(os.path.dirname(__file__), 'sql', 'custom.sql')
        if os.path.exists(sql_file):
            try:
                with open(sql_file, 'r', encoding='utf-8') as f:
                    sql = f.read()
                    with connection.cursor() as cursor:
                        cursor.executescript(sql)
            except Exception as e:
                pass 