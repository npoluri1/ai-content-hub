import { Card, CardContent, Typography, Box } from '@mui/material';
import { ReactNode } from 'react';

interface Props {
  title: string;
  value: string | number;
  icon: ReactNode;
  color?: string;
  subtitle?: string;
  onClick?: () => void;
}

export default function StatsCard({ title, value, icon, color, subtitle, onClick }: Props) {
  return (
    <Card
      onClick={onClick}
      sx={{
        cursor: onClick ? 'pointer' : 'default',
        height: '100%',
        position: 'relative',
        overflow: 'hidden',
        transition: 'transform 0.2s, box-shadow 0.2s',
        '&:hover': onClick ? { transform: 'translateY(-2px)', boxShadow: 8 } : {},
        '&::before': { content: '""', position: 'absolute', top: 0, left: 0, right: 0, height: 3, background: color || 'primary.main' },
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box>
            <Typography variant="overline" color="text.secondary" sx={{ letterSpacing: 1, fontSize: 11 }}>{title}</Typography>
            <Typography variant="h3" fontWeight={800} sx={{ lineHeight: 1.1, mt: 0.5 }}>{value}</Typography>
            {subtitle && <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>{subtitle}</Typography>}
          </Box>
          <Box sx={{ color: color || 'primary.main', opacity: 0.6, transform: 'scale(1.2)', transformOrigin: 'top right' }}>{icon}</Box>
        </Box>
      </CardContent>
    </Card>
  );
}
