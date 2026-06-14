import { Box, Typography, Paper } from '@mui/material';

export default function Settings() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Settings
      </Typography>
      <Paper sx={{ p: 3 }}>
        <Typography color="text.secondary">
          Settings panel is under development.
        </Typography>
      </Paper>
    </Box>
  );
}
