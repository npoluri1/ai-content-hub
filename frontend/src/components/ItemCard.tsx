import { Card, CardContent, Typography, Chip, Box, Button } from '@mui/material';
import ThumbUpIcon from '@mui/icons-material/ThumbUp';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import PodcastsIcon from '@mui/icons-material/Podcasts';
import PlayCircleIcon from '@mui/icons-material/PlayCircle';
import ImageIcon from '@mui/icons-material/Image';
import ArticleIcon from '@mui/icons-material/Article';
import type { ContentItem } from '../api/client';

interface Props {
  item: ContentItem;
  onClick?: (item: ContentItem) => void;
}

const SOURCE_COLORS: Record<string,string> = {
  arxiv:'#FF6B6B', github:'#6CC644', medium:'#00AB6C', reddit:'#FF4500',
  hackernews:'#FF6600', devto:'#0A0A0A', youtube:'#FF0000', linkedin:'#0A66C2',
  techcrunch:'#0A9E01', techgig:'#F47920', newsapi:'#F5A623', rss:'#FFA500',
  global_rss:'#7C4DFF', podcast:'#E91E63', demo:'#90CAF9',
};

const SOURCE_EMOJI: Record<string,string> = {
  hackernews:'🔥', devto:'💻', medium:'📖', reddit:'💬', arxiv:'📄',
  youtube:'🎬', linkedin:'💼', techcrunch:'📰', techgig:'⚡', newsapi:'📡',
  rss:'📡', global_rss:'🌐', podcast:'🎙️', demo:'🧪',
};

const TYPE_BADGES: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  podcast: { label: '🎙️ Podcast', color: '#E91E63', icon: <PodcastsIcon sx={{ fontSize: 14 }} /> },
  video: { label: '🎬 Video', color: '#FF0000', icon: <PlayCircleIcon sx={{ fontSize: 14 }} /> },
  paper: { label: '📄 Paper', color: '#FF6B6B', icon: <ArticleIcon sx={{ fontSize: 14 }} /> },
  news: { label: '📰 News', color: '#0A9E01', icon: <ArticleIcon sx={{ fontSize: 14 }} /> },
  image: { label: '🖼️ Image', color: '#7C4DFF', icon: <ImageIcon sx={{ fontSize: 14 }} /> },
};

export default function ItemCard({ item, onClick }: Props) {
  const published = item.published_at
    ? new Date(item.published_at).toLocaleDateString('en-US', { month:'short', day:'numeric' })
    : null;
  const snippet = (item.snippet || item.content || '').slice(0, 180);
  const topics = (item.topics || item.topic || '').split(',').filter(Boolean).slice(0, 3);
  const src = item.source || 'unknown';
  const sc = SOURCE_COLORS[src] || 'primary.main';
  const hasUrl = !!item.url;
  const isPodcast = item.source_type === 'podcast' || src === 'podcast';
  const isVideo = !!item.video_url || item.source_type === 'video';
  const hasImage = item.image_urls && item.image_urls.length > 0;
  const audioUrl = item.audio_url;

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
      {hasImage && (
        <Box sx={{ width: '100%', height: 120, overflow: 'hidden', position: 'relative', bgcolor: 'grey.100' }}>
          <img
            src={item.image_urls![0]}
            alt=""
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
        </Box>
      )}

      {isPodcast && !hasImage && (
        <Box sx={{ width: '100%', height: 60, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: '#FCE4EC', gap: 1 }}>
          <PodcastsIcon sx={{ color: '#E91E63', fontSize: 28 }} />
          <Typography variant="caption" fontWeight={700} color="#E91E63">Podcast Episode</Typography>
        </Box>
      )}

      {isVideo && !hasImage && (
        <Box sx={{ width: '100%', height: 60, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: '#FFEBEE', gap: 1 }}>
          <PlayCircleIcon sx={{ color: '#FF0000', fontSize: 28 }} />
          <Typography variant="caption" fontWeight={700} color="#FF0000">Video</Typography>
        </Box>
      )}

      <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 1, pb: '12px !important', pt: hasImage ? 1 : 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.8, flexWrap: 'wrap' }}>
          <Chip label={`${SOURCE_EMOJI[src] || '📌'} ${src}`} size="small" sx={{ bgcolor: sc, color: '#000', fontWeight: 700, fontSize: 10, height: 22 }} />
          {item.engagement !== undefined && item.engagement > 0 && (
            <Box sx={{ display:'flex', alignItems:'center', gap:0.3, color:'text.secondary', fontSize:11 }}>
              <ThumbUpIcon sx={{ fontSize: 12 }} /> {item.engagement}
            </Box>
          )}
          {item.source_type && TYPE_BADGES[item.source_type] && (
            <Chip
              icon={TYPE_BADGES[item.source_type].icon as any}
              label={TYPE_BADGES[item.source_type].label}
              size="small"
              sx={{ bgcolor: `${TYPE_BADGES[item.source_type].color}18`, color: TYPE_BADGES[item.source_type].color, fontWeight: 600, fontSize: 9, height: 20, '& .MuiChip-icon': { ml: 0.3 } }}
            />
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

        {hasUrl && (
          <Typography
            variant="caption"
            sx={{ fontSize: 10, color: 'primary.main', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', cursor: 'pointer' }}
            onClick={(e: React.MouseEvent) => { e.stopPropagation(); window.open(item.url, '_blank', 'noopener,noreferrer'); }}
          >
            {item.url}
          </Typography>
        )}

        {audioUrl && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5, p: 0.5, bgcolor: '#FCE4EC', borderRadius: 1 }}>
            <PodcastsIcon sx={{ color: '#E91E63', fontSize: 16 }} />
            <audio controls style={{ height: 28, width: '100%', minWidth: 0 }}>
              <source src={audioUrl} type="audio/mpeg" />
            </audio>
          </Box>
        )}

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
            {topics.map(t => <Chip key={t} label={t} size="small" variant="outlined" sx={{ fontSize: 9, height: 18 }} />)}
          </Box>
          <Box sx={{ display: 'flex', gap: 0.8, alignItems: 'center', ml: 1, flexShrink: 0 }}>
            {published && <Typography variant="caption" color="text.secondary" sx={{ fontSize: 10, whiteSpace: 'nowrap' }}>{published}</Typography>}
            {hasUrl && (
              <Button
                size="small"
                variant="contained"
                endIcon={<OpenInNewIcon sx={{ fontSize: 11 }} />}
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e: React.MouseEvent) => e.stopPropagation()}
                sx={{ minWidth: 44, fontSize: 9, height: 20, p: '1px 5px', textTransform: 'none', borderRadius: 1 }}
              >
                Open
              </Button>
            )}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
}
