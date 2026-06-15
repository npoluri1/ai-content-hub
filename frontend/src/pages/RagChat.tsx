import { useState } from 'react';
import { Box, Typography, Card, CardContent, TextField, Button, CircularProgress, Avatar, Paper, Chip, IconButton, ToggleButtonGroup, ToggleButton } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import SettingsIcon from '@mui/icons-material/Settings';
import { ragQuery } from '../api/client';
import { useModels } from '../context/ModelContext';

export default function RagChat() {
  const { activeModel, freeModels, premiumModels, activeTier, switchToModel, switchToTier, loading: modelLoading, globalModelId } = useModels();
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<{role:string;content:string;sources?:any[]}[]>([]);
  const [loading, setLoading] = useState(false);
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [tier, setTier] = useState<'free' | 'premium'>('free');

  const models = tier === 'free' ? freeModels : premiumModels;

  const effectiveModelId = globalModelId || activeModel?.id || '';

  const ask = async () => {
    if (!question.trim()) return;
    const q = question;
    setQuestion('');
    setMessages(prev => [...prev, { role: 'user', content: q }]);
    setLoading(true);
    try {
      const r = await ragQuery(q, effectiveModelId);
      setMessages(prev => [...prev, { role: 'assistant', content: r.answer || r, sources: r.sources }]);
    } catch { setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error.' }]) }
    finally { setLoading(false) }
  };

  return (
    <Box sx={{ display:'flex', flexDirection:'column', height: 'calc(100vh - 140px)' }}>
      <Box sx={{ display:'flex', alignItems:'center', justifyContent:'space-between', mb: 1 }}>
        <Typography variant="h4">RAG Chat</Typography>
        <Button size="small" startIcon={<SettingsIcon />} onClick={() => setShowModelPicker(!showModelPicker)}>
          {activeModel?.name || 'Select Model'}
        </Button>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Active: <strong>{activeModel?.name || 'Default'}</strong>
        {globalModelId && <> · Global override: <strong>{globalModelId}</strong></>}
      </Typography>

      {showModelPicker && (
        <Card sx={{ mb: 2, p: 2 }}>
          <Typography variant="subtitle2" gutterBottom>Model Selection</Typography>
          <ToggleButtonGroup value={tier} exclusive onChange={(_, v) => v && setTier(v)} size="small" sx={{ mb: 2 }}>
            <ToggleButton value="free">Free ({freeModels.length})</ToggleButton>
            <ToggleButton value="premium">Premium ({premiumModels.length})</ToggleButton>
          </ToggleButtonGroup>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, maxHeight: 200, overflow: 'auto' }}>
            {models.map(m => (
              <Paper
                key={m.id}
                sx={{ p: 1, cursor: 'pointer', width: 'calc(25% - 8px)', minWidth: 140, border: m.id === (globalModelId || activeModel?.id) ? 2 : 1, borderColor: m.id === (globalModelId || activeModel?.id) ? 'primary.main' : 'divider', '&:hover': { bgcolor: 'action.hover' } }}
                onClick={() => { switchToModel(m.id); setShowModelPicker(false) }}
              >
                <Typography variant="caption" fontWeight="bold" noWrap>{m.name}</Typography>
                <Typography variant="caption" display="block" color="text.secondary" noWrap>{m.provider} · {m.context_window.toLocaleString()} ctx</Typography>
              </Paper>
            ))}
          </Box>
        </Card>
      )}

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
