import {
  Card,
  CardContent,
  Typography,
  Chip,
  Box,
  Link,
} from '@mui/material';
import { format, parseISO } from 'date-fns';
import type { ContentItem } from '../api/client';

interface ItemCardProps {
  item: ContentItem;
}

const SOURCE_COLORS: Record<string, string> = {
  arxiv: '#ff6b6b',
  github: '#6cc644',
  medium: '#00ab6c',
  reddit: '#ff4500',
  twitter: '#1da1f2',
  news: '#90caf9',
  blog: '#f48fb1',
  youtube: '#ff0000',
};

function getSourceColor(source: string): string {
  const key = source.toLowerCase();
  return SOURCE_COLORS[key] ?? '#90caf9';
}

export default function ItemCard({ item }: ItemCardProps) {
  const publishedDate =
    item.published_at
      ? (() => {
          try {
            return format(parseISO(item.published_at), 'MMM d, yyyy');
          } catch {
            return item.published_at;
          }
        })()
      : null;

  const snippet =
    item.snippet && item.snippet.length > 200
      ? item.snippet.slice(0, 200) + '...'
      : item.snippet;

  return (
    <Card
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        transition: 'box-shadow 0.2s',
        '&:hover': {
          boxShadow: 6,
        },
      }}
    >
      <CardContent sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
          <Chip
            label={item.source}
            size="small"
            sx={{
              backgroundColor: getSourceColor(item.source),
              color: '#000',
              fontWeight: 600,
              fontSize: 11,
            }}
          />
          {item.topic && (
            <Chip
              label={item.topic}
              size="small"
              variant="outlined"
              sx={{ fontSize: 11 }}
            />
          )}
        </Box>

        <Typography variant="subtitle1" fontWeight={600} sx={{ lineHeight: 1.3 }}>
          {item.title}
        </Typography>

        {snippet && (
          <Typography variant="body2" color="text.secondary" sx={{ flexGrow: 1 }}>
            {snippet}
          </Typography>
        )}

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 'auto' }}>
          {publishedDate && (
            <Typography variant="caption" color="text.secondary">
              {publishedDate}
            </Typography>
          )}
          <Link
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            underline="hover"
            variant="caption"
            sx={{ ml: 'auto' }}
          >
            Open Source
          </Link>
        </Box>
      </CardContent>
    </Card>
  );
}
