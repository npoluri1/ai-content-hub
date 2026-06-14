import { useState } from 'react';
import { Box, Typography, Card, CardContent, TextField, Button, CircularProgress, Avatar, Paper, Chip, IconButton } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import { ragQuery } from '../api/client';

export default function RagChat() {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<{role:string;content:string;sources?:any[]}[]>([]);
  const [loading, setLoading] = useState(false);

  const ask = async () => {
    if (!question.trim()) return;
    const q = question;
    setQuestion('');
    setMessages(prev => [...prev, { role: 'user', content: q }]);
    setLoading(true);
    try {
      const r = await ragQuery(q);
      setMessages(prev => [...prev, { role: 'assistant', content: r.answer || r, sources: r.sources }]);
    } catch { setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error.' }]) }
    finally { setLoading(false) }
  };

  return (
    <Box sx={{ display:'flex', flexDirection:'column', height: 'calc(100vh - 140px)' }}>
      <Typography variant="h4" gutterBottom>RAG Chat</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Ask questions about your ingested content</Typography>

      <Card sx={{ flex: 1, display:'flex', flexDirection:'column', overflow:'hidden' }}>
        <Box sx={{ flex: 1, overflow:'auto', p: 2, display:'flex', flexDirection:'column', gap: 2 }}>
          {messages.length === 0 && (
            <Box sx={{ textAlign:'center', my: 'auto', color:'text.secondary' }}>
              <SmartToyIcon sx={{ fontSize: 48, mb: 1 }} />
              <Typography>Ask a question about your content</Typography>
            </Box>
          )}
          {messages.map((m, i) => (
            <Box key={i} sx={{ display:'flex', gap: 1.5, alignItems: 'flex-start', flexDirection: m.role === 'user' ? 'row-reverse' : 'row' }}>
              <Avatar sx={{ bgcolor: m.role === 'user' ? 'primary.main' : 'secondary.main', width: 32, height: 32 }}>
                {m.role === 'user' ? <PersonIcon fontSize="small" /> : <SmartToyIcon fontSize="small" />}
              </Avatar>
              <Paper sx={{ p: 2, maxWidth: '75%', bgcolor: m.role === 'user' ? 'primary.main' : 'background.default', color: m.role === 'user' ? '#000' : 'inherit' }}>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{m.content}</Typography>
                {m.sources && m.sources.length > 0 && (
                  <Box sx={{ mt: 1, display:'flex', gap: 0.5, flexWrap:'wrap' }}>
                    {m.sources.map((s:any, j:number) => <Chip key={j} label={s.title?.slice(0,40) || 'Source'} size="small" variant="outlined" />)}
                  </Box>
                )}
              </Paper>
            </Box>
          ))}
          {loading && <Box sx={{ display:'flex', gap: 1.5 }}><Avatar sx={{ bgcolor:'secondary.main', width:32, height:32 }}><SmartToyIcon fontSize="small" /></Avatar><CircularProgress size={24} /></Box>}
        </Box>
        <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider', display:'flex', gap: 1 }}>
          <TextField fullWidth size="small" value={question} onChange={e => setQuestion(e.target.value)} onKeyDown={e => e.key === 'Enter' && ask()} placeholder="Ask about your content..." />
          <IconButton color="primary" onClick={ask} disabled={loading || !question.trim()}><SendIcon /></IconButton>
        </Box>
      </Card>
    </Box>
  );
}
