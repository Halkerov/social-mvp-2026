-- Представление (VIEW) популярных постов
CREATE VIEW IF NOT EXISTS popular_posts AS
SELECT 
    p.id,
    p.title,
    p.content,
    p.author_id,
    p.created_at,
    (SELECT COUNT(*) FROM main_post_likes WHERE post_id = p.id) as likes_count,
    (SELECT COUNT(*) FROM main_comment WHERE post_id = p.id AND is_deleted = 0) as comments_count
FROM main_post p
ORDER BY likes_count DESC, comments_count DESC;

-- Представление активных пользователей
CREATE VIEW IF NOT EXISTS active_users AS
SELECT 
    u.id,
    u.username,
    COUNT(DISTINCT p.id) as posts_count,
    COUNT(DISTINCT c.id) as comments_count,
    COUNT(DISTINCT m.id) as messages_count
FROM auth_user u
LEFT JOIN main_post p ON u.id = p.author_id
LEFT JOIN main_comment c ON u.id = c.author_id
LEFT JOIN main_message m ON u.id = m.sender_id
GROUP BY u.id
HAVING posts_count > 0 OR comments_count > 0 OR messages_count > 0;

-- Триггер автоматического обновления даты при редактировании комментария
CREATE TRIGGER IF NOT EXISTS update_comment_timestamp
AFTER UPDATE OF content ON main_comment
FOR EACH ROW
WHEN OLD.content != NEW.content
BEGIN
    UPDATE main_comment 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;