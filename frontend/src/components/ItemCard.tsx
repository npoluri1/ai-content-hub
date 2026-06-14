import { Card, CardContent, Typography, Chip, Box } from '@mui/material';
import ThumbUpIcon from '@mui/icons-material/ThumbUp';
import type { ContentItem } from '../api/client';

interface Props {
  item: ContentItem;
  onClick?: (item: ContentItem) => void;
}

const SOURCE_COLORS: Record<string,string> = {
  arxiv:'#FF6B6B', github:'#6CC644', medium:'#00AB6C', reddit:'#FF4500',
  hackernews:'#FF6600', devto:'#0A0A0A', youtube:'#FF0000', linkedin:'#0A66C2',
  techcrunch:'#0A9E01', techgig:'#F47920', newsapi:'#F5A623', rss:'#FFA500', demo:'#90CAF9',
};

const SOURCE_EMOJI: Record<string,string> = {
  hackernews:'🔥', devto:'💻', medium:'📖', reddit:'💬', arxiv:'📄',
  youtube:'🎬', linkedin:'💼', techcrunch:'📰', techgig:'⚡', newsapi:'📡', rss:'📡', demo:'🧪',
};

export default function ItemCard({ item, onClick }: Props) {
  const published = item.published_at
    ? new Date(item.published_at).toLocaleDateString('en-US', { month:'short', day:'numeric' })
    : null;
  const snippet = (item.snippet || item.content || '').slice(0, 180);
  const topics = (item.topics || item.topic || '').split(',').filter(Boolean).slice(0, 3);
  const sc = SOURCE_COLORS[item.source] || 'primary.main';

  return (
    <Card
      onClick={() => onClick?.(item)}
      sx={{
        cursor: 'pointer', height: '100%', display: 'flex', flexDirection: 'column',
        transition: 'transform 0.15s, box-shadow 0.15s',
        '&:hover': { transform: 'translateY(-3px)', boxShadow: `0 8px 25px ${sc}22` },
        position: 'relative', overflow: 'hidden',
        '&::after': { content: '""', position: 'absolute', top: 0, left: 0, width: 3, height: '100%', background: sc },
      }}
    >
      <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 1, pb: '12px !important' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.8, flexWrap: 'wrap' }}>
          <Chip label={`${SOURCE_EMOJI[item.source] || '📌'} ${item.source}`} size="small" sx={{ bgcolor: sc, color: '#000', fontWeight: 700, fontSize: 10, height: 22 }} />
          {item.engagement !== undefined && item.engagement > 0 && (
            <Box sx={{ display:'flex', alignItems:'center', gap:0.3, color:'text.secondary', fontSize:11 }}>
              <ThumbUpIcon sx={{ fontSize: 12 }} /> {item.engagement}
            </Box>
          )}
        </Box>

        <Typography variant="subtitle2" fontWeight={700} sx={{ lineHeight: 1.3, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
          {item.title || 'Untitled'}
        </Typography>

        {snippet && (
          <Typography variant="caption" color="text.secondary" sx={{
            flex: 1, display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden', lineHeight: 1.6, fontSize: 12,
          }}>
            {snippet}...
          </Typography>
        )}

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 'auto' }}>
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
            {topics.map(t => <Chip key={t} label={t} size="small" variant="outlined" sx={{ fontSize: 9, height: 18 }} />)}
          </Box>
          {published && <Typography variant="caption" color="text.secondary" sx={{ fontSize: 10, whiteSpace: 'nowrap', ml: 1 }}>{published}</Typography>}
        </Box>
      </CardContent>
    </Card>
  );
}
