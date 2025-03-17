// Add this route to your API routes
app.post('/api/notifications/read-all', async (req, res) => {
    try {
        // Mark all AniList notifications as read
        await db.query('UPDATE anilist_notifications SET read = 1 WHERE user_id = ?', [req.user.id]);
        
        // Mark all manga status notifications as read
        await db.query('UPDATE manga_status_notifications SET read = 1 WHERE user_id = ?', [req.user.id]);
        
        // Add similar query for bato_updates_notifications when you implement it
        
        res.json({ success: true });
    } catch (error) {
        console.error('Error marking all notifications as read:', error);
        res.status(500).json({ success: false, error: 'Server error' });
    }
});

app.get('/api/notifications/count', async (req, res) => {
    try {
        // Get count of unread AniList notifications
        const [anilistResult] = await db.query(
            'SELECT COUNT(*) as count FROM anilist_notifications WHERE user_id = ? AND read = 0',
            [req.user.id]
        );
        
        // Get count of unread manga status notifications
        const [mangaStatusResult] = await db.query(
            'SELECT COUNT(*) as count FROM manga_status_notifications WHERE user_id = ? AND read = 0',
            [req.user.id]
        );
        
        // Add count for bato_updates_notifications when implemented
        
        const totalCount = anilistResult[0].count + mangaStatusResult[0].count;
        
        res.json({ count: totalCount });
    } catch (error) {
        console.error('Error counting notifications:', error);
        res.status(500).json({ count: 0 });
    }
}); 