import { useEffect, useState, useCallback } from 'react';
import { Box, Typography, Grid, Card, CardContent, Chip, CircularProgress, Alert, Button, Avatar, IconButton, LinearProgress } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import StorageIcon from '@mui/icons-material/Storage';
import ItemCard from '../components/ItemCard';
import { getSources, getBySource, ContentItem } from '../api/client';

interface Props { onItemClick: (item: ContentItem) => void }

const SOURCE_META: Record<string, { color:string; icon:string }> = {
  hackernews:{ color:'#FF6600', icon:'🔥' },
  devto:{ color:'#0A0A0A', icon:'💻' },
  medium:{ color:'#00AB6C', icon:'📖' },
  reddit:{ color:'#FF4500', icon:'💬' },
  arxiv:{ color:'#FF6B6B', icon:'📄' },
  youtube:{ color:'#FF0000', icon:'🎬' },
  linkedin:{ color:'#0A66C2', icon:'💼' },
  techcrunch:{ color:'#0A9E01', icon:'📰' },
  techgig:{ color:'#F47920', icon:'⚡' },
  newsapi:{ color:'#F5A623', icon:'📡' },
  rss:{ color:'#FFA500', icon:'📡' },
  demo:{ color:'#90CAF9', icon:'🧪' },
};

export default function Sources({ onItemClick }: Props) {
  const [sources, setSources] = useState<{name:string;count:number}[]>([]);
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const [items, setItems] = useState<ContentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingItems, setLoadingItems] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try { setSources(await getSources()) }
    catch (e: any) { setError(e.message) }
    finally { setLoading(false) }
  }, []);

  useEffect(() => { load() }, [load]);

  const handleSelect = async (name: string) => {
    setSelectedSource(name); setLoadingItems(true); setError('');
    try { setItems(await getBySource(name)) }
    catch (e: any) { setError(e.message) }
    finally { setLoadingItems(false) }
  };

  if (loading) return <Box sx={{ display:'flex', justifyContent:'center', mt:8 }}><CircularProgress /></Box>;
  if (error) return <Alert severity="error">{error}</Alert>;

  const maxCount = Math.max(...sources.map(s => s.count), 1);

  return (
    <Box>
      <Box sx={{ display:'flex', justifyContent:'space-between', alignItems:'center', mb: 3 }}>
        <Box>
          <Typography variant="h4">Sources</Typography>
          <Typography variant="body2" color="text.secondary">{sources.length} active content sources</Typography>
        </Box>
        <Button size="small" startIcon={<RefreshIcon />} onClick={load} variant="outlined">Refresh</Button>
      </Box>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        {sources.sort((a,b) => b.count - a.count).map(src => {
          const meta = SOURCE_META[src.name] || { color:'#90CAF9', icon:'📌' };
          const isSelected = selectedSource === src.name;
          return (
            <Grid item xs={6} sm={4} md={3} lg={2} key={src.name}>
              <Card
                onClick={() => handleSelect(src.name)}
                sx={{
                  cursor: 'pointer', textAlign: 'center', position: 'relative', overflow: 'visible',
                  border: isSelected ? 2 : 0, borderColor: meta.color,
                  transition: 'transform 0.15s',
                  '&:hover': { transform: 'translateY(-2px)' },
                }}
              >
                <CardContent sx={{ py: 1.5 }}>
                  <Typography variant="h4" sx={{ mb: 0.5 }}>{meta.icon}</Typography>
                  <Typography variant="body2" fontWeight={700} noWrap>{src.name.charAt(0).toUpperCase() + src.name.slice(1)}</Typography>
                  <Typography variant="h5" fontWeight={800} color="primary" sx={{ mt: 0.5 }}>{src.count}</Typography>
                  <LinearProgress variant="determinate" value={(src.count / maxCount) * 100} sx={{ mt: 1, height: 3, borderRadius: 2, bgcolor: 'rgba(255,255,255,0.05)' }} />
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>

      {selectedSource && (
        <Box>
          <Box sx={{ display:'flex', alignItems:'center', gap: 1, mb: 2 }}>
            <Chip label={`${SOURCE_META[selectedSource]?.icon || '📌'} ${selectedSource}`} color="primary" onDelete={() => setSelectedSource(null)} />
            <Typography variant="body2" color="text.secondary">{items.length} items</Typography>
          </Box>
          {loadingItems ? <CircularProgress /> : (
            <Grid container spacing={2}>
              {items.map(item => (
                <Grid item xs={12} sm={6} md={4} key={item.id}>
                  <ItemCard item={item} onClick={onItemClick} />
                </Grid>
              ))}
            </Grid>
          )}
        </Box>
      )}
    </Box>
  );
}
