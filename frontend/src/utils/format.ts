export function compactNumber(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(value);
}

export function oneDecimal(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return Number(value).toFixed(1);
}

export function percentage(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `${(Number(value) * 100).toFixed(1)}%`;
}

export function actionTone(action: string): 'orange' | 'blue' | 'green' | 'purple' | 'slate' {
  const lower = action.toLowerCase();
  if (lower.includes('tow')) return 'orange';
  if (lower.includes('engineering')) return 'purple';
  if (lower.includes('metro') || lower.includes('market')) return 'green';
  if (lower.includes('fixed')) return 'blue';
  return 'slate';
}

