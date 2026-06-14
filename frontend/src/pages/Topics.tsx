import { useEffect, useState, useCallback } from 'react';
import { Box, Typography, Grid, List, ListItemButton, ListItemText, Chip, CircularProgress, Alert, Paper, Badge, TextField, InputAdornment } from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import ItemCard from '../components/ItemCard';
import { getTopics, getByTopic, fetchStats, ContentItem } from '../api/client';

interface Props { onItemClick: (item: ContentItem) => void }

export default function Topics({ onItemClick }: Props) {
  const [allTopics, setAllTopics] = useState<string[]>([]);
  const [filteredTopics, setFilteredTopics] = useState<string[]>([]);
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [items, setItems] = useState<ContentItem[]>([]);
  const [topicCounts, setTopicCounts] = useState<Record<string, number>>({});
  const [loadingTopics, setLoadingTopics] = useState(true);
  const [loadingItems, setLoadingItems] = useState(false);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const [topics, stats] = await Promise.all([getTopics(), fetchStats()]);
        setAllTopics(topics);
        setFilteredTopics(topics);
        setTopicCounts(stats.by_topic);
      } catch (e: any) { setError(e.message) }
      finally { setLoadingTopics(false) }
    })();
  }, []);

  useEffect(() => {
    setFilteredTopics(allTopics.filter(t => t.toLowerCase().includes(search.toLowerCase())));
  }, [search, allTopics]);

  const handleSelect = useCallback(async (topic: string) => {
    setSelectedTopic(topic); setLoadingItems(true); setError('');
    try {
      const data = await getByTopic(topic);
      setItems(data);
    } catch (e: any) { setError(e.message) }
    finally { setLoadingItems(false) }
  }, []);

  if (loadingTopics) return <Box sx={{ display:'flex', justifyContent:'center', mt:8 }}><CircularProgress /></Box>;

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Topics</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>Browse content by AI-classified topic categories</Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={3}>
          <TextField
            fullWidth size="small" placeholder="Filter topics..." value={search} onChange={e => setSearch(e.target.value)}
            sx={{ mb: 1.5 }}
            slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> } }}
          />
          <Paper sx={{ maxHeight: 500, overflow: 'auto', borderRadius: 2 }}>
            {filteredTopics.length === 0 ? (
              <Box sx={{ p: 2, textAlign:'center' }}><Typography color="text.secondary" variant="body2">No topics</Typography></Box>
            ) : (
              <List dense disablePadding>
                {filteredTopics.map(topic => (
                  <ListItemButton key={topic} selected={selectedTopic === topic} onClick={() => handleSelect(topic)} sx={{ borderRadius: 1, mx: 0.5, my: 0.3 }}>
                    <ListItemText primary={topic} primaryTypographyProps={{ variant: 'body2', fontWeight: selectedTopic === topic ? 700 : 500 }} />
                    {topicCounts[topic] > 0 && <Badge badgeContent={topicCounts[topic]} color="primary" max={999} />}
                  </ListItemButton>
                ))}
              </List>
            )}
          </Paper>
        </Grid>
        <Grid item xs={12} md={9}>
          {!selectedTopic && <Box sx={{ textAlign:'center', py:8 }}><Typography color="text.secondary">Select a topic to view items</Typography></Box>}
          {loadingItems && <Box sx={{ display:'flex', justifyContent:'center', mt:4 }}><CircularProgress /></Box>}
          {error && <Alert severity="error">{error}</Alert>}
          {!loadingItems && selectedTopic && items.length === 0 && !error && <Typography color="text.secondary">No items for this topic</Typography>}
          {selectedTopic && (
            <Box sx={{ mb: 2, display:'flex', alignItems:'center', gap: 1 }}>
              <Chip label={selectedTopic} color="primary" onDelete={() => setSelectedTopic(null)} />
              <Typography variant="body2" color="text.secondary">{items.length} items</Typography>
            </Box>
          )}
          <Grid container spacing={2}>
            {items.map(item => (
              <Grid item xs={12} sm={6} key={item.id}>
                <ItemCard item={item} onClick={onItemClick} />
              </Grid>
            ))}
          </Grid>
        </Grid>
      </Grid>
    </Box>
  );
}
