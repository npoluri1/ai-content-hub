import { Box, Typography, Card, CardContent, TextField, Button, Avatar, Chip } from '@mui/material';
import { useState } from 'react';

export default function Forum() {
  const [posts, setPosts] = useState([
    { author: 'Alice', text: 'Has anyone tried MCP with LangGraph for production?', replies: 5, time: '2h ago' },
    { author: 'Bob', text: 'Best vector DB for RAG in 2026? Comparing ChromaDB vs Qdrant.', replies: 12, time: '5h ago' },
    { author: 'Carol', text: 'Just deployed our first AI agent in production. Tips on monitoring?', replies: 8, time: '1d ago' },
  ]);
  const [newPost, setNewPost] = useState('');

  const addPost = () => {
    if (!newPost.trim()) return;
    setPosts([{ author: 'You', text: newPost, replies: 0, time: 'Just now' }, ...posts]);
    setNewPost('');
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Community Forum</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>Discuss AI topics with the community</Typography>
      <Box sx={{ display:'flex', gap: 1, mb: 3 }}>
        <TextField fullWidth size="small" value={newPost} onChange={e => setNewPost(e.target.value)} placeholder="Start a discussion..." onKeyDown={e => e.key === 'Enter' && addPost()} />
        <Button variant="contained" onClick={addPost} disabled={!newPost.trim()}>Post</Button>
      </Box>
      {posts.map((p, i) => (
        <Card key={i} sx={{ mb: 1 }}>
          <CardContent sx={{ display:'flex', gap: 2, py: 1.5, '&:last-child': { pb: 1.5 } }}>
            <Avatar sx={{ width: 32, height: 32, fontSize: 14 }}>{p.author[0]}</Avatar>
            <Box sx={{ flex:1 }}>
              <Typography variant="body2"><strong>{p.author}</strong> <Typography component="span" variant="caption" color="text.secondary">{p.time}</Typography></Typography>
              <Typography variant="body2" sx={{ mt: 0.5 }}>{p.text}</Typography>
              <Chip label={`${p.replies} replies`} size="small" variant="outlined" sx={{ mt: 0.5 }} />
            </Box>
          </CardContent>
        </Card>
      ))}
    </Box>
  );
}
