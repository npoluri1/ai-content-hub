import { Box, Typography, Card, CardContent, TextField, Chip, Grid, InputAdornment, IconButton } from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import FilterListIcon from '@mui/icons-material/FilterList';

export default function EnterpriseSearch() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>Enterprise Search</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>Advanced faceted search with semantic understanding</Typography>
      <Card sx={{ p: 2, mb: 3 }}>
        <TextField fullWidth placeholder="Enterprise search..." size="medium" slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchIcon /></InputAdornment>, endAdornment: <IconButton><FilterListIcon /></IconButton> } }} />
        <Box sx={{ display:'flex', gap: 0.5, mt: 2 }}>
          <Chip label="Source: All" size="small" onDelete={()=>{}} />
          <Chip label="Date: Last 30 days" size="small" onDelete={()=>{}} />
          <Chip label="Type: Articles" size="small" onDelete={()=>{}} />
        </Box>
      </Card>
      <Typography color="text.secondary">Use the search bar above to find content across all sources with faceted filtering.</Typography>
    </Box>
  );
}
