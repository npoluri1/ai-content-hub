import { useEffect, useState, useCallback } from 'react';
import {
  Box,
  Typography,
  Grid,
  List,
  ListItemButton,
  ListItemText,
  CircularProgress,
  Alert,
  Paper,
} from '@mui/material';
import ItemCard from '../components/ItemCard';
import { getTopics, getByTopic, ContentItem } from '../api/client';

export default function Topics() {
  const [topics, setTopics] = useState<string[]>([]);
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [items, setItems] = useState<ContentItem[]>([]);
  const [loadingTopics, setLoadingTopics] = useState(true);
  const [loadingItems, setLoadingItems] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const data = await getTopics();
        setTopics(data);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to load topics';
        setError(msg);
      } finally {
        setLoadingTopics(false);
      }
    }
    load();
  }, []);

  const handleSelect = useCallback(async (topic: string) => {
    setSelectedTopic(topic);
    setLoadingItems(true);
    setError('');
    try {
      const data = await getByTopic(topic);
      setItems(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load items';
      setError(msg);
    } finally {
      setLoadingItems(false);
    }
  }, []);

  if (loadingTopics) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Topics
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={3}>
          <Paper sx={{ maxHeight: 600, overflow: 'auto' }}>
            <List dense>
              {topics.length === 0 ? (
                <ListItemButton disabled>
                  <ListItemText primary="No topics available" />
                </ListItemButton>
              ) : (
                topics.map((topic) => (
                  <ListItemButton
                    key={topic}
                    selected={selectedTopic === topic}
                    onClick={() => handleSelect(topic)}
                  >
                    <ListItemText primary={topic} />
                  </ListItemButton>
                ))
              )}
            </List>
          </Paper>
        </Grid>

        <Grid item xs={12} md={9}>
          {!selectedTopic && (
            <Typography color="text.secondary">Select a topic to view items</Typography>
          )}

          {loadingItems && (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
              <CircularProgress />
            </Box>
          )}

          {error && <Alert severity="error">{error}</Alert>}

          {!loadingItems && selectedTopic && items.length === 0 && !error && (
            <Typography color="text.secondary">No items for this topic</Typography>
          )}

          <Grid container spacing={2}>
            {items.map((item) => (
              <Grid item xs={12} sm={6} key={item.id}>
                <ItemCard item={item} />
              </Grid>
            ))}
          </Grid>
        </Grid>
      </Grid>
    </Box>
  );
}
