import { useEffect, useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button, Typography,
  Box, Chip, IconButton, CircularProgress, Tooltip,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import ThumbUpIcon from '@mui/icons-material/ThumbUp';
import PodcastsIcon from '@mui/icons-material/Podcasts';
import PlayCircleIcon from '@mui/icons-material/PlayCircle';
import type { ContentItem } from '../api/client';
import { analyzeSentiment } from '../api/client';

interface Props {
  item: ContentItem | null;
  open: boolean;
  onClose: () => void;
}

const SOURCE_EMOJI: Record<string,string> = {
  hackernews:'🔥', devto:'💻', medium:'📖', reddit:'💬', arxiv:'📄',
  youtube:'🎬', linkedin:'💼', techcrunch:'📰', techgig:'⚡', newsapi:'📡', rss:'📡', demo:'🧪',
};

export default function ItemDetail({ item, open, onClose }: Props) {
  const [sentiment, setSentiment] = useState<any>(null);
  const [loadingSentiment, setLoadingSentiment] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (open && item) {
      setSentiment(null);
      const text = item.content?.slice(0, 500);
      if (text && text.length > 20) {
        setLoadingSentiment(true);
        analyzeSentiment(text).then(r => setSentiment(r.sentiment)).catch(() => {}).finally(() => setLoadingSentiment(false));
      }
    }
  }, [open, item]);

  if (!item) return null;

  const topics = (item.topics || item.topic || '').split(',').filter(Boolean);
  const snippet = item.snippet || item.content?.slice(0, 300) || '';
  const fullContent = item.content || '';
  const isPodcast = item.source_type === 'podcast' || item.source === 'podcast';
  const hasImage = item.image_urls && item.image_urls.length > 0;

  const handleCopy = () => {
    navigator.clipboard.writeText(fullContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth scroll="paper">
      <DialogTitle sx={{ pb: 1, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, flexWrap: 'wrap' }}>
            <Chip label={`${SOURCE_EMOJI[item.source || ''] || '📌'} ${item.source || 'unknown'}`} size="small" color="primary" variant="outlined" />
            {item.source_type && item.source_type !== 'post' && (
              <Chip
                label={`${item.source_type === 'podcast' ? '🎙️' : item.source_type === 'video' ? '🎬' : item.source_type === 'paper' ? '📄' : '📰'} ${item.source_type}`}
                size="small" variant="outlined" color="secondary"
              />
            )}
            {item.author && <Chip label={item.author} size="small" variant="outlined" />}
            {item.engagement !== undefined && item.engagement > 0 && (
              <Chip icon={<ThumbUpIcon />} label={item.engagement} size="small" color="secondary" variant="outlined" />
            )}
          </Box>
          <Typography variant="h5" fontWeight={700}>{item.title || 'Untitled'}</Typography>
        </Box>
        <IconButton onClick={onClose} size="small"><CloseIcon /></IconButton>
      </DialogTitle>
      <DialogContent dividers>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
          {topics.map(t => <Chip key={t} label={t} size="small" sx={{ fontWeight: 600 }} />)}
          {item.published_at && <Chip label={new Date(item.published_at).toLocaleDateString('en-US', { year:'numeric',month:'long',day:'numeric' })} size="small" variant="outlined" />}
        </Box>

        {hasImage && (
          <Box sx={{ mb: 2, borderRadius: 2, overflow: 'hidden', maxHeight: 300 }}>
            <img src={item.image_urls![0]} alt="" style={{ width:'100%', maxHeight:300, objectFit:'cover' }} onError={(e)=>{ (e.target as HTMLImageElement).style.display='none'; }} />
          </Box>
        )}

        {isPodcast && item.audio_url && (
          <Box sx={{ mb: 2, p: 2, bgcolor:'#FCE4EC', borderRadius:2, display:'flex', alignItems:'center', gap:2 }}>
            <PodcastsIcon sx={{ color:'#E91E63', fontSize:40 }} />
            <Box sx={{ flex:1 }}>
              <Typography variant="subtitle2" fontWeight={700}>Podcast Episode</Typography>
              <audio controls style={{ width:'100%', height:32, marginTop:4 }}>
                <source src={item.audio_url} type="audio/mpeg" />
              </audio>
            </Box>
          </Box>
        )}

        {isPodcast && !item.audio_url && (
          <Box sx={{ mb: 2, p: 2, bgcolor:'#FCE4EC', borderRadius:2, display:'flex', alignItems:'center', gap:1 }}>
            <PodcastsIcon sx={{ color:'#E91E63' }} />
            <Typography variant="body2">Podcast Episode — audio not available for direct playback</Typography>
          </Box>
        )}

        {item.video_url && (
          <Box sx={{ mb: 2, p: 2, bgcolor:'#FFEBEE', borderRadius:2, display:'flex', alignItems:'center', gap:1 }}>
            <PlayCircleIcon sx={{ color:'#FF0000' }} />
            <Typography variant="body2">Video available — <a href={item.video_url} target="_blank" rel="noopener noreferrer" style={{ color:'#FF0000' }}>Watch here</a></Typography>
          </Box>
        )}

        <Typography variant="body1" sx={{ lineHeight: 1.8, whiteSpace: 'pre-wrap', mb: 3 }}>
          {fullContent || snippet || 'No content available'}
        </Typography>

        {loadingSentiment && <Box sx={{ display:'flex', alignItems:'center', gap:1, color:'text.secondary' }}><CircularProgress size={16} /> Analyzing sentiment...</Box>}
        {sentiment && !loadingSentiment && (
          <Box sx={{ mt: 2, p: 2, borderRadius: 2, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
            <Typography variant="subtitle2" sx={{ display:'flex', alignItems:'center', gap:1, mb:1 }}>
              <SmartToyIcon fontSize="small" /> AI Sentiment Analysis
            </Typography>
            <Box sx={{ display:'flex', gap: 3, flexWrap:'wrap' }}>
              <Typography variant="body2"><strong>Sentiment:</strong> {sentiment.sentiment}</Typography>
              <Typography variant="body2"><strong>Score:</strong> {(sentiment.score * 100).toFixed(0)}%</Typography>
              {sentiment.details?.emotional_tone && <Typography variant="body2"><strong>Tone:</strong> {sentiment.details.emotional_tone}</Typography>}
              {sentiment.confidence && <Typography variant="body2"><strong>Confidence:</strong> {(sentiment.confidence * 100).toFixed(0)}%</Typography>}
            </Box>
          </Box>
        )}
      </DialogContent>
      <DialogActions sx={{ justifyContent: 'space-between', px: 2, py: 1.5 }}>
        <Box sx={{ display:'flex', gap:1 }}>
          <Tooltip title="Copy content">
            <Button size="small" startIcon={<ContentCopyIcon />} onClick={handleCopy}>
              {copied ? 'Copied!' : 'Copy'}
            </Button>
          </Tooltip>
        </Box>
        {item.url && (
          <Button size="small" variant="contained" endIcon={<OpenInNewIcon />} href={item.url} target="_blank" rel="noopener noreferrer">
            Open Original
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
