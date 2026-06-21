import { useMemo, useState } from 'react';
import {
  AlertTriangle,
  BarChart3,
  Car,
  Info,
  MapPinned,
  Navigation,
  ShieldCheck,
  SlidersHorizontal,
  Target,
  Truck,
  Zap
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';
import { useParkPulseData } from './data/useParkPulseData';
import RiskMap from './components/RiskMap';
import ZoneBrief from './components/ZoneBrief';
import type {
  ChartPoint,
  CongestionSegmentsGeoJson,
  Drilldown,
  EnforcementPlanRow,
  HotspotFeature,
  LaneHotspotFeature,
  ParkPulseData,
  RoadspaceHotspot,
  StationSummary
} from './types';
import { actionTone, compactNumber, oneDecimal, percentage } from './utils/format';

type Page =
  | 'Command Center'
  | 'Live Ops Brief'
  | 'Intelligence Report'
  | 'Priority Queue'
  | 'Hotspot Intelligence'
  | "Tomorrow's Risk"
  | 'Deployment Simulator'
  | 'Station View'
  | 'Methodology';

const pages: Array<{ name: Page; icon: React.ElementType }> = [
  { name: 'Command Center', icon: ShieldCheck },
  { name: 'Live Ops Brief', icon: Zap },
  { name: 'Intelligence Report', icon: BarChart3 },
  { name: 'Hotspot Intelligence', icon: MapPinned },
  { name: 'Deployment Simulator', icon: SlidersHorizontal },
  { name: 'Methodology', icon: Info }
];

function actionColor(action: string): [number, number, number] {
  const tone = actionTone(action);
  if (tone === 'orange') return [251, 100, 27];
  if (tone === 'purple') return [128, 90, 213];
  if (tone === 'green') return [38, 166, 91];
  if (tone === 'blue') return [40, 116, 240];
  return [92, 104, 122];
}

function actionCssColor(action: string): string {
  const [red, green, blue] = actionColor(action);
  return `rgb(${red}, ${green}, ${blue})`;
}

function actionLabel(action: string): string {
  if (action.toLowerCase().includes('tow')) return 'Tow';
  if (action.toLowerCase().includes('engineering')) return 'Engineering';
  if (action.toLowerCase().includes('metro')) return 'Metro/Market';
  if (action.toLowerCase().includes('fixed')) return 'Fixed Window';
  if (action.toLowerCase().includes('watch')) return 'Watch';
  return 'Patrol';
}

function officerActionText(action: string): string {
  const lower = action.toLowerCase();
  if (lower.includes('tow')) return 'Send tow support and clear parked vehicles';
  if (lower.includes('engineering')) return 'Send patrol and flag for engineering fix';
  if (lower.includes('fixed')) return 'Place a fixed-window enforcement unit';
  if (lower.includes('metro') || lower.includes('market')) return 'Control pickup/drop and spillover parking';
  if (lower.includes('watch')) return 'Keep on watchlist and audit if pressure rises';
  return 'Send targeted patrol';
}

function resourceText(plan: EnforcementPlanRow): string {
  const patrol = plan.estimated_patrol_hours ?? 0;
  const tow = plan.estimated_tow_hours ?? 0;
  if (tow > 0 && patrol > 0) return `Tow + patrol support (${oneDecimal(patrol)} patrol hr, ${oneDecimal(tow)} tow hr)`;
  if (tow > 0) return `Tow support (${oneDecimal(tow)} tow hr)`;
  if (patrol > 0) return `Patrol support (${oneDecimal(patrol)} patrol hr)`;
  return 'Officer audit / watchlist';
}

function urgencyText(plan: EnforcementPlanRow): string {
  const sla = plan.clearance_sla_minutes;
  if (sla === undefined || sla === null) return plan.clearance_decision_band ?? 'Act in target window';
  if (sla <= 30) return `Immediate response: within ${compactNumber(sla)} min`;
  if (sla <= 90) return `Same-shift response: within ${compactNumber(sla)} min`;
  return `Planned response: within ${compactNumber(sla)} min`;
}

function plainWhy(plan: EnforcementPlanRow, roadspace?: RoadspaceHotspot): string {
  if (roadspace?.dominant_lane_issue) return roadspace.dominant_lane_issue;
  if (plan.reasoning) return plan.reasoning;
  return 'Recurring illegal-parking pressure is likely to affect usable road space in this area.';
}

type MapFeature = HotspotFeature | LaneHotspotFeature;

function mapProps(feature: MapFeature) {
  const props = feature.properties;
  const isLaneHotspot = 'lane_obstruction_proxy_0_100' in props;
  return {
    zoneId: props.zone_id,
    zoneName: props.zone_name,
    station: props.police_station,
    action: props.recommended_action,
    confidence: props.confidence_band,
    timeWindow: isLaneHotspot ? props.time_window : props.best_time_window,
    score: isLaneHotspot ? props.lane_obstruction_proxy_0_100 : props.final_priority_score,
    tori: isLaneHotspot ? props.final_tori_0_100 : props.final_priority_score,
    repeatPressure: props.repeat_pressure_score_0_100,
    patrolGap: props.patrol_gap_score_0_100,
    issue: isLaneHotspot ? props.dominant_lane_issue : props.reasoning,
    laneContext: isLaneHotspot ? props.lane_context : 'Hotspot centroid',
    mitigation: isLaneHotspot ? props.mitigation_plan?.[0]?.step : undefined,
    workforce: isLaneHotspot ? props.historical_workforce_proxy : undefined,
    signal: isLaneHotspot ? props.signal_health_status : undefined
  };
}

const ALL_PAGES: Page[] = [
  'Command Center', 'Live Ops Brief', 'Intelligence Report', 'Priority Queue', 'Hotspot Intelligence',
  "Tomorrow's Risk", 'Deployment Simulator', 'Station View', 'Methodology'
];

function initialPage(): Page {
  if (typeof window === 'undefined') return 'Command Center';
  const q = new URLSearchParams(window.location.search).get('page');
  if (!q) return 'Command Center';
  const norm = q.toLowerCase().replace(/[^a-z]/g, '');
  return ALL_PAGES.find((p) => p.toLowerCase().replace(/[^a-z]/g, '').includes(norm)) ?? 'Command Center';
}

function App() {
  const { data, loading, error } = useParkPulseData();
  const [page, setPage] = useState<Page>(initialPage());
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);

  if (loading || !data) {
    return <LoadingState />;
  }

  const selectedPlan =
    data.enforcementPlan.find((row) => row.zone_id === selectedZoneId) ?? data.enforcementPlan[0];

  function openHotspotIntelligence(zoneId?: string | null) {
    if (!zoneId) return;
    setSelectedZoneId(zoneId);
    setPage('Hotspot Intelligence');
  }

  return (
    <div className="app-shell">
      <Sidebar active={page} onChange={setPage} usingMockData={data.usingMockData} />
      <main className="main-surface">
        <Header error={error} data={data} />
        {page === 'Command Center' && (
          <CommandCenter data={data} selectedPlan={selectedPlan} onSelect={openHotspotIntelligence} />
        )}
        {page === 'Live Ops Brief' && <LiveOpsBrief data={data} onSelect={openHotspotIntelligence} />}
        {page === 'Intelligence Report' && <OperationalIntelligenceReport data={data} onSelect={openHotspotIntelligence} />}
        {page === 'Priority Queue' && <PriorityQueue data={data} onSelect={openHotspotIntelligence} />}
        {page === 'Hotspot Intelligence' && (
          <HotspotIntelligence data={data} selectedPlan={selectedPlan} onSelect={openHotspotIntelligence} />
        )}
        {page === "Tomorrow's Risk" && <TomorrowRisk data={data} />}
        {page === 'Deployment Simulator' && <DeploymentSimulator rows={data.enforcementPlan} />}
        {page === 'Station View' && <StationView data={data} onSelect={openHotspotIntelligence} />}
        {page === 'Methodology' && <Methodology />}
      </main>
    </div>
  );
}

function Header({ error, data }: { error: string | null; data: ParkPulseData }) {
  return (
    <section className="hero-panel">
      <div className="hero-text">
        <p className="eyebrow">Bengaluru Traffic Police · Poor Visibility on Parking-Induced Congestion</p>
        <h1>ParkPulse Bengaluru</h1>
        <p className="hero-subtitle">
          A simple enforcement console: where to go, when to go, what action to take, and why.
        </p>
      </div>
      <div className="hero-side">
        <div className="hero-action">Officer-ready view</div>
        {error && <div className="mock-badge">Fallback data active</div>}
      </div>
    </section>
  );
}

function Sidebar({
  active,
  onChange,
  usingMockData
}: {
  active: Page;
  onChange: (page: Page) => void;
  usingMockData: boolean;
}) {
  return (
    <aside className="sidebar">
      <div className="brand-lockup">
        <div className="brand-mark">P</div>
        <div>
          <strong>ParkPulse</strong>
          <span>Bengaluru</span>
        </div>
      </div>
      <nav>
        {pages.map(({ name, icon: Icon }) => (
          <button
            key={name}
            className={`nav-item ${active === name ? 'active' : ''}`}
            onClick={() => onChange(name)}
            type="button"
          >
            <Icon size={18} />
            {name}
          </button>
        ))}
      </nav>
      <div className="sidebar-note">
        <Info size={16} />
        <span>
          Built for clear instructions. Traffic-flow numbers are decision-support estimates, not live speed measurements.
        </span>
      </div>
      {usingMockData && <div className="sidebar-warning">Using mock fallback data</div>}
    </aside>
  );
}

function CommandCenter({
  data,
  selectedPlan,
  onSelect
}: {
  data: ParkPulseData;
  selectedPlan: EnforcementPlanRow;
  onSelect: (zoneId: string) => void;
}) {
  const mapHotspots = data.laneHotspots.features.length > 0 ? data.laneHotspots.features : data.hotspots.features;
  const firstRows = data.enforcementPlan.slice(0, 10);
  const towCount = firstRows.filter((row) => row.recommended_action.toLowerCase().includes('tow')).length;
  const highConfidenceCount = firstRows.filter((row) => row.confidence_band === 'High').length;

  return (
    <section className="page-grid">
      <div className="simple-command-strip">
        <article className="radio-card command-first-card">
          <span className="ops-label">First action now</span>
          <h2>{officerActionText(selectedPlan.recommended_action)}</h2>
          <p>
            <strong>{selectedPlan.zone_name}</strong> · {selectedPlan.police_station} · {selectedPlan.best_time_window}
          </p>
          <p>{plainWhy(selectedPlan)}</p>
          <button type="button" onClick={() => onSelect(selectedPlan.zone_id)}>Open field brief</button>
        </article>
        <div className="simple-status-cards">
          <SummaryItem label="First-wave zones" value={compactNumber(firstRows.length)} />
          <SummaryItem label="Need tow support" value={compactNumber(towCount)} />
          <SummaryItem label="High confidence" value={compactNumber(highConfidenceCount)} />
        </div>
      </div>

      <div className="command-layout">
        <ChartCard title="Where to act" subtitle="Click a hotspot to open a simple field brief. Red corridors need the earliest attention.">
          <RiskMap
            segments={data.congestionSegments}
            hotspots={mapHotspots}
            selectedId={selectedPlan?.zone_id}
            onSelect={onSelect}
            fallback={
              <CommandMap segments={data.congestionSegments} hotspots={mapHotspots} selectedId={selectedPlan?.zone_id} onSelect={onSelect} />
            }
          />
        </ChartCard>
        <TopPriorityPanel rows={firstRows} onSelect={onSelect} />
      </div>
    </section>
  );
}

function KpiCard({
  label,
  value,
  icon: Icon,
  sub,
  accent,
  hint
}: {
  label: string;
  value: string;
  icon: React.ElementType;
  sub?: string;
  accent?: boolean;
  hint?: string;
}) {
  return (
    <article className={`kpi-card ${accent ? 'accent' : ''}`} title={hint}>
      <div className="kpi-top">
        <div className="kpi-icon">
          <Icon size={20} />
        </div>
        {hint && <span className="kpi-info" aria-label={hint}>i</span>}
      </div>
      <span>{label}</span>
      <strong>{value}</strong>
      {sub && <small className="kpi-sub">{sub}</small>}
    </article>
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="summary-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ChartCard({
  title,
  subtitle,
  children
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <article className="chart-card">
      <div className="card-heading">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
      </div>
      {children}
    </article>
  );
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="empty-state">
      <Info size={22} />
      <strong>{title}</strong>
      <p>{body}</p>
    </div>
  );
}

function CommandMap({
  segments,
  hotspots,
  selectedId,
  onSelect
}: {
  segments?: CongestionSegmentsGeoJson;
  hotspots: MapFeature[];
  selectedId?: string;
  onSelect: (zoneId: string) => void;
}) {
  const [hovered, setHovered] = useState<MapFeature | null>(null);
  const [station, setStation] = useState('All');
  const [action, setAction] = useState('All');
  const [minScore, setMinScore] = useState(88);
  const [highConfidenceOnly, setHighConfidenceOnly] = useState(false);
  const width = 1000;
  const height = 620;
  const pad = 46;

  const stations = useMemo(
    () => ['All', ...Array.from(new Set(hotspots.map((item) => mapProps(item).station))).sort()],
    [hotspots]
  );
  const actions = useMemo(
    () => ['All', ...Array.from(new Set(hotspots.map((item) => mapProps(item).action))).sort()],
    [hotspots]
  );
  const bounds = useMemo(() => {
    const valid = hotspots.filter((item) => Number.isFinite(item.geometry.coordinates[0]) && Number.isFinite(item.geometry.coordinates[1]));
    return {
      minLon: Math.min(...valid.map((item) => item.geometry.coordinates[0])),
      maxLon: Math.max(...valid.map((item) => item.geometry.coordinates[0])),
      minLat: Math.min(...valid.map((item) => item.geometry.coordinates[1])),
      maxLat: Math.max(...valid.map((item) => item.geometry.coordinates[1]))
    };
  }, [hotspots]);
  const selectedFeature = useMemo(
    () => hotspots.find((item) => mapProps(item).zoneId === selectedId) ?? null,
    [hotspots, selectedId]
  );
  const visibleSegments = useMemo(() => {
    const stationAllow = station === 'All' ? null : station;
    return (segments?.features ?? [])
      .filter((feature) => !stationAllow || feature.properties.station === stationAllow)
      .sort((a, b) => b.properties.obstruction_score - a.properties.obstruction_score)
      .slice(0, 1200);
  }, [segments, station]);
  const visibleHotspots = useMemo(() => {
    const filtered = hotspots.filter((item) => {
      const props = mapProps(item);
      return (
        props.score >= minScore &&
        (station === 'All' || props.station === station) &&
        (action === 'All' || props.action === action) &&
        (!highConfidenceOnly || props.confidence === 'High')
      );
    });
    const capped = [...filtered]
      .sort((a, b) => mapProps(b).score - mapProps(a).score)
      .slice(0, 850)
      .reverse();
    if (selectedFeature && !capped.some((item) => mapProps(item).zoneId === mapProps(selectedFeature).zoneId)) {
      capped.push(selectedFeature);
    }
    return capped;
  }, [action, highConfidenceOnly, hotspots, minScore, selectedFeature, station]);

  function projectCoord(lon: number, lat: number) {
    const x = pad + ((lon - bounds.minLon) / Math.max(0.0001, bounds.maxLon - bounds.minLon)) * (width - pad * 2);
    const y = height - pad - ((lat - bounds.minLat) / Math.max(0.0001, bounds.maxLat - bounds.minLat)) * (height - pad * 2);
    return { x, y };
  }

  function project(feature: MapFeature) {
    const [lon, lat] = feature.geometry.coordinates;
    return projectCoord(lon, lat);
  }

  const topVisible = [...visibleHotspots]
    .sort((a, b) => mapProps(b).score - mapProps(a).score)
    .slice(0, 3);
  const activeFeature = hovered ?? selectedFeature ?? topVisible[0] ?? null;

  return (
    <div className="map-shell">
      <div className="map-controls">
        <select value={station} onChange={(event) => setStation(event.target.value)} aria-label="Filter by police station">
          {stations.map((item) => <option key={item}>{item}</option>)}
        </select>
        <select value={action} onChange={(event) => setAction(event.target.value)} aria-label="Filter by enforcement action">
          {actions.map((item) => <option key={item}>{item}</option>)}
        </select>
        <label className="map-slider">
          Min obstruction score {minScore}
          <input type="range" min="0" max="100" value={minScore} onChange={(event) => setMinScore(Number(event.target.value))} />
        </label>
        <label className="toggle-pill">
          <input type="checkbox" checked={highConfidenceOnly} onChange={(event) => setHighConfidenceOnly(event.target.checked)} />
          High confidence only
        </label>
      </div>

      <div className="tactical-map">
        <svg className="map-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Offline tactical hotspot map of Bengaluru">
          <defs>
            <radialGradient id="mapGlow" cx="50%" cy="48%" r="58%">
              <stop offset="0%" stopColor="#ffffff" />
              <stop offset="100%" stopColor="#dce8f8" />
            </radialGradient>
          </defs>
          <rect width={width} height={height} rx="26" fill="url(#mapGlow)" />
          <g className="map-grid">
            {Array.from({ length: 9 }, (_, index) => (
              <line key={`v-${index}`} x1={pad + index * ((width - pad * 2) / 8)} x2={pad + index * ((width - pad * 2) / 8)} y1={pad} y2={height - pad} />
            ))}
            {Array.from({ length: 6 }, (_, index) => (
              <line key={`h-${index}`} x1={pad} x2={width - pad} y1={pad + index * ((height - pad * 2) / 5)} y2={pad + index * ((height - pad * 2) / 5)} />
            ))}
          </g>
          {visibleHotspots.length === 0 ? (
            <text className="map-empty-label" x={width / 2} y={height / 2}>No hotspots match current filters</text>
          ) : (
            <>
              <g className="offline-corridor-lines">
                {visibleSegments.map((segment) => {
                  const points = segment.geometry.coordinates
                    .map(([lon, lat]) => {
                      const { x, y } = projectCoord(lon, lat);
                      return `${x},${y}`;
                    })
                    .join(' ');
                  return (
                    <polyline
                      key={segment.properties.segment_id}
                      points={points}
                      fill="none"
                      stroke={segment.properties.color}
                      strokeWidth={Math.max(2.2, Math.min(8, 1.5 + segment.properties.obstruction_score / 18))}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  );
                })}
              </g>
              {visibleHotspots.map((feature) => {
              const { x, y } = project(feature);
              const props = mapProps(feature);
              const score = props.score;
              const isSelected = props.zoneId === selectedId;
              const radius = Math.max(4, Math.min(15, 3 + score / 9));
              return (
                <circle
                  key={props.zoneId}
                  className={`map-point ${isSelected ? 'selected' : ''}`}
                  cx={x}
                  cy={y}
                  r={isSelected ? radius + 4 : radius}
                  fill={actionCssColor(props.action)}
                  opacity={isSelected ? 0.98 : 0.62}
                  tabIndex={0}
                  role="button"
                  aria-label={`${props.zoneName}, score ${oneDecimal(score)}`}
                  onMouseEnter={() => setHovered(feature)}
                  onFocus={() => setHovered(feature)}
                  onMouseLeave={() => setHovered(null)}
                  onBlur={() => setHovered(null)}
                  onClick={() => onSelect(props.zoneId)}
                />
              );
              })}
            </>
          )}
        </svg>
        <div className="map-compass">
          <span>N</span>
          <strong>Offline coordinate view (real lat/lon)</strong>
        </div>
      </div>

      <div className="map-footer">
        <span>{visibleHotspots.length} hotspots visible</span>
        <span>{hotspots.length} mapped hotspots</span>
        {segments && <span>{visibleSegments.length} corridor lines</span>}
        <span>Click any dot to open its brief</span>
      </div>

      {activeFeature && (
        <div className="map-tooltip">
          {(() => {
            const props = mapProps(activeFeature);
            return (
              <>
                <strong>{props.zoneName}</strong>
                <span>{props.station} · {props.laneContext}</span>
                <span>Lane score {oneDecimal(props.score)} · TORI {oneDecimal(props.tori)}</span>
                <span>Repeat {oneDecimal(props.repeatPressure)} · Patrol gap {oneDecimal(props.patrolGap)}</span>
                <ActionChip action={props.action} />
                <span>{props.timeWindow} · {props.confidence} confidence</span>
                <span>{props.issue}</span>
                {props.mitigation && <span>Plan: {props.mitigation}</span>}
                {props.workforce && <span>{props.workforce}</span>}
                {props.signal && <span>{props.signal}</span>}
                <button type="button" onClick={() => onSelect(props.zoneId)}>Open brief</button>
              </>
            );
          })()}
        </div>
      )}
    </div>
  );
}

function TopPriorityPanel({ rows, onSelect }: { rows: EnforcementPlanRow[]; onSelect: (zoneId: string) => void }) {
  return (
    <aside className="priority-panel">
      <div className="panel-heading">
        <h2>Next actions</h2>
        <p>Simple dispatch list for the first enforcement wave.</p>
      </div>
      <div className="priority-list">
        {rows.map((row) => (
          <button className="priority-row" key={row.zone_id} onClick={() => onSelect(row.zone_id)} type="button">
            <span className="rank">#{row.rank}</span>
            <span className="zone">
              <strong>{row.zone_name}</strong>
              <small>{row.police_station} · {row.best_time_window}</small>
              <small>{urgencyText(row)} · {row.confidence_band} confidence</small>
            </span>
            <ActionChip action={row.recommended_action} />
            <strong className="score">Open</strong>
          </button>
        ))}
      </div>
    </aside>
  );
}

function ActionChip({ action }: { action: string }) {
  return <span className={`action-chip ${actionTone(action)}`}>{actionLabel(action)}</span>;
}

function ConfidenceBadge({ band }: { band: string }) {
  return <span className={`confidence ${band.toLowerCase()}`}>{band}</span>;
}

function LiveOpsBrief({ data, onSelect }: { data: ParkPulseData; onSelect: (zoneId: string) => void }) {
  const timeWindows = useMemo(
    () => ['All', ...Array.from(new Set(data.enforcementPlan.map((row) => row.best_time_window))).sort()],
    [data.enforcementPlan]
  );
  const stations = useMemo(
    () => ['All', ...Array.from(new Set(data.enforcementPlan.map((row) => row.police_station))).sort()],
    [data.enforcementPlan]
  );
  const [timeWindow, setTimeWindow] = useState(timeWindows[1] ?? 'All');
  const [station, setStation] = useState('All');

  const filtered = data.enforcementPlan.filter((row) => {
    return (
      (timeWindow === 'All' || row.best_time_window === timeWindow) &&
      (station === 'All' || row.police_station === station)
    );
  });
  const criticalRows = [...filtered]
    .sort(
      (a, b) =>
        (b.operational_priority_score_0_100 ?? b.final_priority_score) -
        (a.operational_priority_score_0_100 ?? a.final_priority_score)
    )
    .slice(0, 8);
  const firstRow = criticalRows[0] ?? data.enforcementPlan[0];
  const stationWaves = useMemo(() => {
    const groups = new globalThis.Map<string, EnforcementPlanRow[]>();
    filtered.forEach((row) => {
      groups.set(row.police_station, [...(groups.get(row.police_station) ?? []), row]);
    });
    return Array.from(groups.entries())
      .map(([name, rows]) => ({
        name,
        rows: [...rows].sort((a, b) => b.final_priority_score - a.final_priority_score).slice(0, 3),
        score: rows.reduce((sum, row) => sum + row.final_priority_score, 0),
        patrol: rows.reduce((sum, row) => sum + row.estimated_patrol_hours, 0),
        tow: rows.reduce((sum, row) => sum + row.estimated_tow_hours, 0)
      }))
      .sort((a, b) => b.score - a.score)
      .slice(0, 6);
  }, [filtered]);

  return (
    <section className="stack">
      <PageTitle
        title="Live Ops Brief"
        subtitle="A simple shift brief: first action, station wave, and field runbook."
      />
      <div className="filter-bar ops-filter">
        <select value={timeWindow} onChange={(event) => setTimeWindow(event.target.value)}>
          {timeWindows.map((item) => <option key={item}>{item}</option>)}
        </select>
        <select value={station} onChange={(event) => setStation(event.target.value)}>
          {stations.map((item) => <option key={item}>{item}</option>)}
        </select>
      </div>

      <div className="ops-layout">
        <article className="radio-card">
          <span className="ops-label">Radio brief</span>
          <h2>{firstRow ? `Send first unit to ${firstRow.zone_name}` : 'No active hotspot selected'}</h2>
          {firstRow && (
            <>
              <p>
                {firstRow.police_station}: <strong>{officerActionText(firstRow.recommended_action)}</strong> during{' '}
                <strong>{firstRow.best_time_window}</strong>. {urgencyText(firstRow)}.
              </p>
              <p className="reason-large">{firstRow.reasoning}</p>
              <button type="button" onClick={() => onSelect(firstRow.zone_id)}>Open hotspot intelligence</button>
            </>
          )}
        </article>
        <div className="simple-status-cards vertical">
          <SummaryItem label="Actions in this view" value={compactNumber(criticalRows.length)} />
          <SummaryItem label="First station" value={firstRow?.police_station ?? '—'} />
          <SummaryItem label="First time window" value={firstRow?.best_time_window ?? '—'} />
        </div>
      </div>

      <div className="ops-grid">
        <article className="ops-card">
          <div className="card-heading">
            <h2>Dispatch Wave</h2>
            <p>Station-wise sequence for the next enforcement window.</p>
          </div>
          <div className="wave-list">
            {stationWaves.map((wave, index) => (
              <button
                key={wave.name}
                type="button"
                onClick={() => {
                  if (wave.rows[0]?.zone_id) onSelect(wave.rows[0].zone_id);
                }}
                className="wave-row"
              >
                <span className="rank">W{index + 1}</span>
                <strong>{wave.name}</strong>
                <small>{wave.rows.map((row) => row.zone_name).join(' · ')}</small>
                <em>{oneDecimal(wave.patrol)} patrol h / {oneDecimal(wave.tow)} tow h</em>
              </button>
            ))}
          </div>
        </article>

        <article className="ops-card runbook-card">
          <div className="card-heading">
            <h2>Five-Minute Runbook</h2>
            <p>Designed for a duty officer who has no time to inspect tables.</p>
          </div>
          <ol className="runbook">
            <li>Dispatch first unit to the highest operational-priority, high-confidence hotspot.</li>
            <li>If action contains tow, reserve tow capacity before patrol arrival.</li>
            <li>If spillback risk is high, clear junction-mouth and kerb-lane obstruction before issuing routine challans.</li>
            <li>After the window, mark the hotspot as cleared, unchanged, or shifted nearby.</li>
          </ol>
        </article>
      </div>
    </section>
  );
}

function TriggerCard({
  title,
  rows,
  fallback,
  onSelect
}: {
  title: string;
  rows: EnforcementPlanRow[];
  fallback: string;
  onSelect: (zoneId: string) => void;
}) {
  return (
    <div className="trigger-card">
      <strong>{title}</strong>
      {rows.length === 0 ? (
        <p>{fallback}</p>
      ) : (
        rows.slice(0, 2).map((row) => (
          <button key={row.zone_id} type="button" onClick={() => onSelect(row.zone_id)}>
            <span>{row.police_station}</span>
            <em>{row.zone_name}</em>
            <small>
              Priority {oneDecimal(row.operational_priority_score_0_100 ?? row.final_priority_score)} ·
              Repeat {oneDecimal(row.repeat_pressure_score_0_100)} ·
              Gap {oneDecimal(row.patrol_gap_score_0_100)}
            </small>
          </button>
        ))
      )}
    </div>
  );
}

type IntelligenceMetric = {
  title: string;
  question: string;
  primary: string;
  primaryLabel: string;
  score: string;
  scoreLabel: string;
  plainMeaning: string;
  officerUse: string;
  watchFor: string;
  examples: EnforcementPlanRow[];
  icon: React.ElementType;
  tone: 'blue' | 'orange' | 'green' | 'purple' | 'slate';
};

function numericField(row: EnforcementPlanRow, key: keyof EnforcementPlanRow): number {
  const value = row[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

function meanField(rows: EnforcementPlanRow[], key: keyof EnforcementPlanRow): number {
  if (rows.length === 0) return 0;
  return rows.reduce((sum, row) => sum + numericField(row, key), 0) / rows.length;
}

function countWhere(rows: EnforcementPlanRow[], predicate: (row: EnforcementPlanRow) => boolean): number {
  return rows.reduce((count, row) => count + (predicate(row) ? 1 : 0), 0);
}

function topRows(rows: EnforcementPlanRow[], key: keyof EnforcementPlanRow, limit = 3): EnforcementPlanRow[] {
  return [...rows].sort((a, b) => numericField(b, key) - numericField(a, key)).slice(0, limit);
}

function countDistribution(rows: EnforcementPlanRow[], accessor: (row: EnforcementPlanRow) => string | null | undefined, limit = 5): ChartPoint[] {
  const counts = new globalThis.Map<string, number>();
  rows.forEach((row) => {
    const label = accessor(row)?.trim() || 'Not labelled';
    counts.set(label, (counts.get(label) ?? 0) + 1);
  });
  return Array.from(counts.entries())
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, limit);
}

function scoreBandDistribution(rows: EnforcementPlanRow[], key: keyof EnforcementPlanRow): ChartPoint[] {
  const bands = [
    { name: '0-40', min: 0, max: 40 },
    { name: '40-60', min: 40, max: 60 },
    { name: '60-80', min: 60, max: 80 },
    { name: '80-90', min: 80, max: 90 },
    { name: '90-100', min: 90, max: 101 }
  ];
  return bands.map((band) => ({
    name: band.name,
    value: rows.filter((row) => {
      const score = numericField(row, key);
      return score >= band.min && score < band.max;
    }).length
  }));
}

function percentText(count: number, total: number): string {
  if (!total) return '—';
  return `${oneDecimal((count / total) * 100)}%`;
}

function OperationalIntelligenceReport({
  data,
  onSelect
}: {
  data: ParkPulseData;
  onSelect: (zoneId: string) => void;
}) {
  const stations = useMemo(
    () => ['All', ...Array.from(new Set(data.enforcementPlan.map((row) => row.police_station))).sort()],
    [data.enforcementPlan]
  );
  const timeWindows = useMemo(
    () => ['All', ...Array.from(new Set(data.enforcementPlan.map((row) => row.best_time_window))).sort()],
    [data.enforcementPlan]
  );
  const [station, setStation] = useState('All');
  const [timeWindow, setTimeWindow] = useState('All');
  const [priorityOnly, setPriorityOnly] = useState(true);

  const rows = useMemo(() => {
    return data.enforcementPlan.filter((row) => {
      const priorityScore = row.operational_priority_score_0_100 ?? row.final_priority_score;
      return (
        (station === 'All' || row.police_station === station) &&
        (timeWindow === 'All' || row.best_time_window === timeWindow) &&
        (!priorityOnly || priorityScore >= 80)
      );
    });
  }, [data.enforcementPlan, priorityOnly, station, timeWindow]);

  const recurringCount = countWhere(rows, (row) =>
    ['Chronic hotspot', 'Time-window persistent', 'Recurring watchlist', 'Emerging hotspot'].includes(
      row.hotspot_persistence_class ?? ''
    )
  );
  const repeatHeavyCount = countWhere(
    rows,
    (row) =>
      numericField(row, 'repeat_pressure_score_0_100') >= 75 ||
      numericField(row, 'repeat_vehicle_movement_score_0_100') >= 75
  );
  const highConfidenceCount = countWhere(rows, (row) => row.confidence_band === 'High');
  const visibilityCheckedCount = countWhere(
    rows,
    (row) =>
      numericField(row, 'station_recording_bias_score_0_100') >= 60 ||
      numericField(row, 'patrol_gap_score_0_100') >= 40
  );
  const metrics = useMemo<IntelligenceMetric[]>(() => {
    const total = rows.length;
    const emergingCount = countWhere(rows, (row) => numericField(row, 'emerging_hotspot_score_0_100') >= 85);
    const biasedCount = countWhere(rows, (row) => numericField(row, 'station_recording_bias_score_0_100') >= 75);
    const repeatMovementCount = countWhere(rows, (row) => numericField(row, 'repeat_vehicle_movement_score_0_100') >= 75);
    const reliableCount = countWhere(rows, (row) => numericField(row, 'time_window_reliability_score_0_100') >= 70);
    const persistentCount = countWhere(rows, (row) =>
      ['Chronic hotspot', 'Time-window persistent', 'Recurring watchlist', 'Emerging hotspot'].includes(
        row.hotspot_persistence_class ?? ''
      )
    );
    const severeTextCount = countWhere(rows, (row) => numericField(row, 'violation_text_severity_score_0_100') >= 70);
    const loadedStationCount = countWhere(rows, (row) => ['High load', 'Critical load'].includes(row.station_load_band ?? ''));
    const confidencePriorityCount = countWhere(rows, (row) => numericField(row, 'confidence_adjusted_priority_0_100') >= 90);

    return [
      {
        title: '1. Emerging Hotspot Index',
        question: 'Is this location getting worse recently?',
        primary: compactNumber(emergingCount),
        primaryLabel: `${percentText(emergingCount, total)} fast-rising zones`,
        score: oneDecimal(meanField(rows, 'emerging_hotspot_score_0_100')),
        scoreLabel: 'average rise signal',
        plainMeaning: 'Recent parking pressure is higher than the earlier pattern for this location.',
        officerUse: 'Send a quick audit or short fixed-window patrol before the hotspot becomes chronic.',
        watchFor: 'High score + low past coverage means a hidden problem may be forming.',
        examples: topRows(rows, 'emerging_hotspot_score_0_100'),
        icon: Zap,
        tone: 'orange'
      },
      {
        title: '2. Station Recording Bias Score',
        question: 'Is this hotspot truly risky, or just recorded more often?',
        primary: compactNumber(biasedCount),
        primaryLabel: `${percentText(biasedCount, total)} high-visibility rows`,
        score: oneDecimal(meanField(rows, 'station_recording_bias_score_0_100')),
        scoreLabel: 'average visibility score',
        plainMeaning: 'Some areas look worse because officers or devices already record there frequently.',
        officerUse: 'Compare with exposure-adjusted ranking before sending scarce patrol or tow resources.',
        watchFor: 'High visibility does not mean ignore it; it means verify impact before over-allocating.',
        examples: topRows(rows, 'station_recording_bias_score_0_100'),
        icon: ShieldCheck,
        tone: 'blue'
      },
      {
        title: '3. Repeat Vehicle Movement Pattern',
        question: 'Are the same vehicles causing repeated pressure?',
        primary: compactNumber(repeatMovementCount),
        primaryLabel: `${percentText(repeatMovementCount, total)} repeat-heavy rows`,
        score: oneDecimal(meanField(rows, 'repeat_vehicle_movement_score_0_100')),
        scoreLabel: 'average repeat pressure',
        plainMeaning: 'The same anonymised vehicles or movement patterns are appearing again and again.',
        officerUse: 'Move from routine challans to targeted repeat-offender follow-up or towing.',
        watchFor: 'Cross-station repeat movement can signal displacement from nearby enforcement.',
        examples: topRows(rows, 'repeat_vehicle_movement_score_0_100'),
        icon: Car,
        tone: 'purple'
      },
      {
        title: '4. Time-Window Reliability Score',
        question: 'Can we trust this time-window signal?',
        primary: compactNumber(reliableCount),
        primaryLabel: `${percentText(reliableCount, total)} reliable windows`,
        score: oneDecimal(meanField(rows, 'time_window_reliability_score_0_100')),
        scoreLabel: 'average reliability',
        plainMeaning: 'Checks whether a morning/night/evening window has enough records to support a decision.',
        officerUse: 'Deploy confidently in reliable windows; audit low-reliability windows before major action.',
        watchFor: 'A quiet-looking window may simply be under-recorded, not actually safe.',
        examples: topRows(rows, 'time_window_reliability_score_0_100'),
        icon: Target,
        tone: 'green'
      },
      {
        title: '5. Hotspot Persistence Class',
        question: 'Is this chronic, emerging, recurring, or one-off?',
        primary: compactNumber(persistentCount),
        primaryLabel: `${percentText(persistentCount, total)} recurring or emerging`,
        score: compactNumber(countWhere(rows, (row) => row.hotspot_persistence_class === 'Chronic hotspot')),
        scoreLabel: 'chronic hotspots',
        plainMeaning: 'Classifies the lifecycle of the hotspot so the action is not one-size-fits-all.',
        officerUse: 'Clear chronic zones, audit emerging zones, and watch sparse/one-off zones.',
        watchFor: 'Emerging hotspots need early attention; chronic hotspots need repeated enforcement windows.',
        examples: rows
          .filter((row) => ['Chronic hotspot', 'Emerging hotspot'].includes(row.hotspot_persistence_class ?? ''))
          .slice(0, 3),
        icon: MapPinned,
        tone: 'blue'
      },
      {
        title: '6. Violation Text Severity Mining',
        question: 'Does the violation wording imply road blockage?',
        primary: compactNumber(severeTextCount),
        primaryLabel: `${percentText(severeTextCount, total)} severe text rows`,
        score: oneDecimal(meanField(rows, 'violation_text_severity_score_0_100')),
        scoreLabel: 'average text severity',
        plainMeaning: 'Looks for wording linked to no-parking, main-road obstruction, double parking or running-lane pressure.',
        officerUse: 'Use the wording to explain why the action is tow, patrol, fixed-window enforcement or engineering.',
        watchFor: 'Text signals support the decision; they do not replace field judgement.',
        examples: topRows(rows, 'violation_text_severity_score_0_100'),
        icon: Info,
        tone: 'slate'
      },
      {
        title: '7. Station-Level Enforcement Load',
        question: 'Is this police station overloaded?',
        primary: compactNumber(loadedStationCount),
        primaryLabel: `${percentText(loadedStationCount, total)} high/critical load`,
        score: oneDecimal(meanField(rows, 'station_enforcement_load_score_0_100')),
        scoreLabel: 'average station load',
        plainMeaning: 'Shows whether a station has too many priority zones for a normal shift.',
        officerUse: 'Escalate tow support, pooled patrols, or staggered deployment windows.',
        watchFor: 'A high-load station may need help even if each individual hotspot looks manageable.',
        examples: topRows(rows, 'station_enforcement_load_score_0_100'),
        icon: Truck,
        tone: 'orange'
      },
      {
        title: '8. Confidence-Aware Priority',
        question: 'Which priority is strong enough to act on first?',
        primary: compactNumber(confidencePriorityCount),
        primaryLabel: `${percentText(confidencePriorityCount, total)} high-confidence priorities`,
        score: oneDecimal(meanField(rows, 'confidence_adjusted_priority_0_100')),
        scoreLabel: 'average confidence priority',
        plainMeaning: 'Combines priority with evidence quality so noisy rows do not dominate the dispatch queue.',
        officerUse: 'Use this as the final sorting layer when choosing the first 10-20 actions.',
        watchFor: 'A high score with weak evidence should become an audit, not a full deployment.',
        examples: topRows(rows, 'confidence_adjusted_priority_0_100'),
        icon: BarChart3,
        tone: 'green'
      }
    ];
  }, [rows]);

  const topEvidenceRows = useMemo(
    () =>
      [...rows]
        .sort((a, b) => {
          const bScore =
            numericField(b, 'confidence_adjusted_priority_0_100') +
            numericField(b, 'emerging_hotspot_score_0_100') +
            numericField(b, 'repeat_vehicle_movement_score_0_100');
          const aScore =
            numericField(a, 'confidence_adjusted_priority_0_100') +
            numericField(a, 'emerging_hotspot_score_0_100') +
            numericField(a, 'repeat_vehicle_movement_score_0_100');
          return bScore - aScore;
        })
        .slice(0, 6),
    [rows]
  );
  const proofCards = [
    {
      label: 'Recurring pressure',
      value: compactNumber(recurringCount),
      body: 'These zones are not one-off records; they keep returning or are rising fast.'
    },
    {
      label: 'Repeat vehicle pressure',
      value: compactNumber(repeatHeavyCount),
      body: 'The same vehicles or repeat patterns make normal one-time challans less effective.'
    },
    {
      label: 'Visibility checked',
      value: compactNumber(visibilityCheckedCount),
      body: 'The ranking checks whether a place is genuinely risky or only heavily recorded.'
    },
    {
      label: 'High confidence',
      value: compactNumber(highConfidenceCount),
      body: 'These rows have stronger evidence for immediate officer action.'
    }
  ];

  return (
    <section className="stack">
      <PageTitle
        title="Intelligence Report"
        subtitle="The same eight signals from the pitch, translated into simple field questions and actions."
      />
      <article className="intel-hero simple-intel-hero">
        <div>
          <span className="ops-label">Officer proof layer</span>
          <h2>Read every metric as: what is happening, why it matters, what to do next.</h2>
          <p>
            The technical names stay unchanged for the presentation, but each card now explains the metric in plain language.
            Scores near 80-100 usually mean “act or verify now”; lower scores usually mean “watch or audit.”
          </p>
        </div>
        <div className="intel-hero-stats">
          <div><strong>{compactNumber(rows.length)}</strong><span>filtered priority rows</span></div>
          <div><strong>{compactNumber(recurringCount)}</strong><span>recurring/rising</span></div>
          <div><strong>{compactNumber(highConfidenceCount)}</strong><span>high confidence</span></div>
        </div>
      </article>

      <div className="filter-bar intel-filter">
        <select value={station} onChange={(event) => setStation(event.target.value)}>
          {stations.map((item) => <option key={item}>{item}</option>)}
        </select>
        <select value={timeWindow} onChange={(event) => setTimeWindow(event.target.value)}>
          {timeWindows.map((item) => <option key={item}>{item}</option>)}
        </select>
        <label className="toggle-pill">
          <input type="checkbox" checked={priorityOnly} onChange={(event) => setPriorityOnly(event.target.checked)} />
          Priority rows only
        </label>
      </div>

      {rows.length === 0 ? (
        <EmptyState title="No report rows" body="Relax the station, time-window or priority filter." />
      ) : (
        <>
          <div className="intel-guide">
            <div>
              <strong>Metric name</strong>
              <span>Same terminology as the pitch deck.</span>
            </div>
            <div>
              <strong>Plain question</strong>
              <span>The field interpretation in one line.</span>
            </div>
            <div>
              <strong>Officer use</strong>
              <span>How this changes patrol, tow or audit action.</span>
            </div>
            <div>
              <strong>Examples</strong>
              <span>Click any example to open the full field brief.</span>
            </div>
          </div>

          <div className="plain-evidence-grid report-proof-grid">
            {proofCards.map((card) => (
              <div key={card.label}>
                <span>{card.label}</span>
                <strong>{card.value}</strong>
                <small>{card.body}</small>
              </div>
            ))}
          </div>

          <details className="technical-details">
            <summary>Show detailed signal explanations</summary>
            <div className="intelligence-grid readable-intel-grid">
              {metrics.map((metric) => (
                <IntelligenceMetricCard key={metric.title} metric={metric} onSelect={onSelect} />
              ))}
            </div>
          </details>

          <ChartCard title="Best proof examples" subtitle="Click any row to open the exact field brief.">
            <div className="intel-evidence-list">
              {topEvidenceRows.map((row) => (
                <button key={row.zone_id} type="button" onClick={() => onSelect(row.zone_id)}>
                  <span>#{row.rank}</span>
                  <strong>{row.zone_name}</strong>
                  <small>{row.police_station} · {row.best_time_window}</small>
                  <em>
                    {officerActionText(row.recommended_action)} · {row.confidence_band} confidence
                  </em>
                </button>
              ))}
            </div>
          </ChartCard>
        </>
      )}
    </section>
  );
}

function IntelligenceMetricCard({
  metric,
  onSelect
}: {
  metric: IntelligenceMetric;
  onSelect: (zoneId: string) => void;
}) {
  const Icon = metric.icon;
  return (
    <article className={`intel-card ${metric.tone}`}>
      <div className="intel-card-top">
        <div className="intel-icon"><Icon size={20} /></div>
        <span>{metric.title}</span>
      </div>
      <div className="intel-primary">
        <strong>{metric.primary}</strong>
        <small>{metric.primaryLabel}</small>
      </div>
      <div className="intel-score">
        <span>{metric.scoreLabel}</span>
        <strong>{metric.score}</strong>
      </div>
      <div className="intel-explain-block">
        <span>Plain question</span>
        <strong>{metric.question}</strong>
      </div>
      <div className="intel-explain-block">
        <span>What it means</span>
        <p>{metric.plainMeaning}</p>
      </div>
      <div className="intel-explain-block action">
        <span>Officer use</span>
        <p>{metric.officerUse}</p>
      </div>
      <div className="intel-watch">
        <strong>Watch for:</strong> {metric.watchFor}
      </div>
      <div className="intel-examples">
        {metric.examples.slice(0, 3).map((row) => (
          <button key={row.zone_id} type="button" onClick={() => onSelect(row.zone_id)}>
            <span>{row.police_station}</span>
            <strong>{row.zone_name}</strong>
          </button>
        ))}
      </div>
    </article>
  );
}

function DistributionBars({ data, compact = false }: { data: ChartPoint[]; compact?: boolean }) {
  const maxValue = Math.max(1, ...data.map((item) => item.value));
  if (data.length === 0) return <EmptyState title="No distribution" body="No rows match this report filter." />;
  return (
    <div className={`distribution-bars ${compact ? 'compact' : ''}`}>
      {data.map((item) => (
        <div className="distribution-row" key={item.name}>
          <span>{item.name}</span>
          <div><i style={{ width: `${Math.max(4, (item.value / maxValue) * 100)}%` }} /></div>
          <strong>{compactNumber(item.value)}</strong>
        </div>
      ))}
    </div>
  );
}

function PriorityQueue({ data, onSelect }: { data: ParkPulseData; onSelect: (zoneId: string) => void }) {
  const [station, setStation] = useState('All');
  const [action, setAction] = useState('All');
  const [confidence, setConfidence] = useState('All');
  const [minScore, setMinScore] = useState(80);

  const stations = ['All', ...Array.from(new Set(data.enforcementPlan.map((row) => row.police_station))).sort()];
  const actions = ['All', ...Array.from(new Set(data.enforcementPlan.map((row) => row.recommended_action))).sort()];
  const rows = data.enforcementPlan.filter((row) => {
    return (
      (station === 'All' || row.police_station === station) &&
      (action === 'All' || row.recommended_action === action) &&
      (confidence === 'All' || row.confidence_band === confidence) &&
      row.final_priority_score >= minScore
    );
  });

  return (
    <section className="stack">
      <PageTitle title="Enforcement Priority Queue" subtitle="Where to act, when to act, what action to take, and why." />
      <div className="filter-bar">
        <select value={station} onChange={(event) => setStation(event.target.value)}>
          {stations.map((item) => <option key={item}>{item}</option>)}
        </select>
        <select value={action} onChange={(event) => setAction(event.target.value)}>
          {actions.map((item) => <option key={item}>{item}</option>)}
        </select>
        <select value={confidence} onChange={(event) => setConfidence(event.target.value)}>
          {['All', 'High', 'Medium', 'Low'].map((item) => <option key={item}>{item}</option>)}
        </select>
        <label>
          Min score {minScore}
          <input type="range" min="0" max="100" value={minScore} onChange={(event) => setMinScore(Number(event.target.value))} />
        </label>
      </div>
      <div className="data-table">
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Zone</th>
              <th>Station</th>
              <th>Window</th>
              <th>Score</th>
              <th>Action</th>
              <th>Confidence</th>
              <th>ROI</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.zone_id} onClick={() => onSelect(row.zone_id)}>
                <td>#{row.rank}</td>
                <td><strong>{row.zone_name}</strong></td>
                <td>{row.police_station}</td>
                <td>{row.best_time_window}</td>
                <td>{oneDecimal(row.final_priority_score)}</td>
                <td><ActionChip action={row.recommended_action} /></td>
                <td><ConfidenceBadge band={row.confidence_band} /></td>
                <td>{oneDecimal(row.enforcement_roi)}</td>
                <td className="reason-cell">{row.reasoning}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function HotspotIntelligence({
  data,
  selectedPlan,
  onSelect
}: {
  data: ParkPulseData;
  selectedPlan: EnforcementPlanRow;
  onSelect: (zoneId: string) => void;
}) {
  const roadspace: RoadspaceHotspot | undefined = data.roadspaceIntelligence.find(
    (item) => item.zone_id === selectedPlan.zone_id
  );
  const mapHotspots = data.laneHotspots.features.length > 0 ? data.laneHotspots.features : data.hotspots.features;

  return (
    <section className="stack">
      <PageTitle title="Hotspot Intelligence" subtitle="Officer-ready brief for one selected hotspot." />
      <div className="drilldown-layout">
        <div className="zone-hero officer-brief-card">
          <div className="brief-topline">
            <span>Officer field brief</span>
            <div className="chip-row compact">
              <ActionChip action={selectedPlan.recommended_action} />
              <ConfidenceBadge band={selectedPlan.confidence_band} />
            </div>
          </div>
          <h2>{selectedPlan.zone_name}</h2>
          <p className="brief-location">{selectedPlan.police_station} · {selectedPlan.best_time_window}</p>

          <div className="officer-action-banner">
            <div>
              <span>Recommended action</span>
              <strong>{officerActionText(selectedPlan.recommended_action)}</strong>
            </div>
            <div>
              <span>Response urgency</span>
              <strong>{urgencyText(selectedPlan)}</strong>
            </div>
          </div>

          <div className="officer-brief-grid">
            <div>
              <span>Where</span>
              <strong>{selectedPlan.zone_name}</strong>
              <small>Centroid {oneDecimal(selectedPlan.centroid_lat)}, {oneDecimal(selectedPlan.centroid_lon)}</small>
            </div>
            <div>
              <span>When</span>
              <strong>{selectedPlan.best_time_window}</strong>
              <small>{selectedPlan.time_window_reliability_band ?? 'Usable time-window evidence'}</small>
            </div>
            <div>
              <span>Resource</span>
              <strong>{resourceText(selectedPlan)}</strong>
              <small>{selectedPlan.clearance_decision_band ?? 'Use shift judgement'}</small>
            </div>
            <div>
              <span>Why this matters</span>
              <strong>{plainWhy(selectedPlan, roadspace)}</strong>
              <small>{selectedPlan.reasoning}</small>
            </div>
          </div>

          {roadspace?.corridor_name && (
            <p className="corridor-note">
              Part of <strong>{roadspace.corridor_name}</strong>
              {roadspace.corridor_linked_hotspots ? ` — ${roadspace.corridor_linked_hotspots} linked hotspots` : ''}
              {roadspace.corridor_length_km ? `, ~${oneDecimal(roadspace.corridor_length_km)} km inferred corridor` : ''}.
            </p>
          )}

          <div className="plain-evidence-grid">
            <div>
              <span>Road pressure</span>
              <strong>{oneDecimal(selectedPlan.capacity_loss_pressure_0_100)}/100</strong>
              <small>Likely road-space blockage before clearance.</small>
            </div>
            <div>
              <span>Repeat pattern</span>
              <strong>{oneDecimal(selectedPlan.repeat_pressure_score_0_100)}/100</strong>
              <small>{selectedPlan.repeat_vehicle_movement_pattern ?? 'Repeat-vehicle pressure check.'}</small>
            </div>
            <div>
              <span>Coverage gap</span>
              <strong>{oneDecimal(selectedPlan.patrol_gap_score_0_100)}/100</strong>
              <small>{selectedPlan.patrol_gap_band ?? 'Compares risk with past patrol coverage.'}</small>
            </div>
            <div>
              <span>Evidence quality</span>
              <strong>{selectedPlan.confidence_band}</strong>
              <small>{selectedPlan.time_window_coverage_warning ?? 'Enough evidence for a field decision.'}</small>
            </div>
          </div>
        </div>
        <TopPriorityPanel rows={data.enforcementPlan.slice(0, 8)} onSelect={onSelect} />
      </div>
      <ChartCard
        title="Hotspot Location & Corridor Risk Map"
        subtitle="MapMyIndia/Mappls Bengaluru basemap with ParkPulse corridor-risk lanes: blue = low, yellow = moderate, red = severe. Click any nearby hotspot to switch the brief."
      >
        <RiskMap
          segments={data.congestionSegments}
          hotspots={mapHotspots}
          selectedId={selectedPlan.zone_id}
          onSelect={onSelect}
          compact
          focusSelected
          showControls={false}
          initialMinScore={70}
          maxVisible={160}
          fallback={
            <CommandMap
              segments={data.congestionSegments}
              hotspots={mapHotspots}
              selectedId={selectedPlan.zone_id}
              onSelect={onSelect}
            />
          }
        />
      </ChartCard>
      <ZoneBrief plan={selectedPlan} roadspace={roadspace} />
    </section>
  );
}

function DrilldownCharts({ drilldown }: { drilldown: Drilldown }) {
  return (
    <div className="chart-grid">
      <ChartCard title="Hourly Pattern">
        <MiniBarChart data={drilldown.hourly_pattern} xKey="hour" />
      </ChartCard>
      <ChartCard title="Vehicle Mix">
        <MiniPieChart data={drilldown.vehicle_mix} />
      </ChartCard>
      <ChartCard title="Violation Mix">
        <MiniBarChart data={drilldown.violation_mix} xKey="name" />
      </ChartCard>
      <ChartCard title="Recurrence Trend">
        <MiniLineChart data={drilldown.recurrence_trend} />
      </ChartCard>
    </div>
  );
}

function TomorrowRisk({ data }: { data: ParkPulseData }) {
  const forecastRows = data.forecastSummary.slice(0, 12);
  return (
    <section className="stack">
      <PageTitle title="Tomorrow's Risk" subtitle="Validated recurrence signals first; TORI and ELRM then decide severity, action, and payoff." />
      <div className="kpi-grid four">
        <KpiCard label="Weighted Obstruction @20" value={percentage(data.metrics.weighted_obstruction_capture_at_20)} icon={BarChart3}
          hint="Weighted-obstruction recurrence baseline: heavy/high-obstruction violations weighted more than light-space violations." />
        <KpiCard label="Time-Safe Forecast @20" value={percentage(data.metrics.selected_forecast_capture_at_20)} sub={data.metrics.selected_forecast_model ?? undefined} icon={Target}
          hint="Deployable validation result from the leakage-safe forecasting split." />
        <KpiCard label="Top-20 Capacity at Risk" value={`${compactNumber(data.metrics.top20_capacity_loss_minutes)} min`} icon={SlidersHorizontal}
          hint="Estimated obstruction-weighted lane-capacity minutes at risk in the top operational zones." />
        <KpiCard label="Top-20 Spillback Risk" value={oneDecimal(data.metrics.top20_mean_spillback_risk)} icon={Navigation}
          hint="Average queue-spillback risk across the top operational zones; this is an action-severity signal, not the recurrence headline." />
      </div>
      <div className="summary-strip validation-strip">
        <SummaryItem label="Best validation method" value={data.metrics.best_validation_method_at_20 ?? '—'} />
        <SummaryItem label="Best Capture@20" value={percentage(data.metrics.best_validation_capture_at_20)} />
        <SummaryItem label="Immediate clearance zones" value={compactNumber(data.metrics.immediate_clearance_zones)} />
        <SummaryItem label="Median clearance SLA" value={`${compactNumber(data.metrics.median_clearance_sla_minutes)} min`} />
      </div>
      <div className="summary-strip validation-strip">
        <SummaryItem label="18-22 records" value={compactNumber(data.metrics.evening_records)} />
        <SummaryItem label="00-06 records" value={compactNumber(data.metrics.night_records)} />
        <SummaryItem label="TORI action @20" value={percentage(data.metrics.tori_capture_at_20)} />
        <SummaryItem label="ELRM payoff @20" value={percentage(data.metrics.elrm_capture_at_20)} />
      </div>
      {data.metrics.evening_window_quality_note && (
        <p className="method-copy">{data.metrics.evening_window_quality_note}</p>
      )}
      {forecastRows.length === 0 ? (
        <EmptyState title="Forecast output unavailable" body="Current view will show after leakage-safe model exports are generated." />
      ) : (
        <div className="forecast-grid">
          {forecastRows.map((row) => (
            <article className="forecast-card" key={`${row.zone_id}-${row.best_time_window}`}>
              <span>{row.police_station}</span>
              <h3>{row.zone_name}</h3>
              <p>{row.best_time_window}</p>
              <strong>{oneDecimal(row.predicted_impact_score)}</strong>
              <small>predicted obstruction-risk estimate</small>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function DeploymentSimulator({ rows }: { rows: EnforcementPlanRow[] }) {
  const [patrolUnits, setPatrolUnits] = useState(10);
  const [towUnits, setTowUnits] = useState(3);
  const [station, setStation] = useState('All');
  const [timeWindow, setTimeWindow] = useState('All');
  const stations = ['All', ...Array.from(new Set(rows.map((row) => row.police_station))).sort()];
  const windows = ['All', ...Array.from(new Set(rows.map((row) => row.best_time_window))).sort()];

  const filtered = rows.filter((row) => {
    return (station === 'All' || row.police_station === station) && (timeWindow === 'All' || row.best_time_window === timeWindow);
  });
  const patrolBudget = patrolUnits * 2;
  const towBudget = towUnits * 2;
  let patrolUsed = 0;
  let towUsed = 0;
  const selected: EnforcementPlanRow[] = [];
  [...filtered]
    .sort(
      (a, b) =>
        (b.recovery_minutes_per_resource_hour ?? 0) - (a.recovery_minutes_per_resource_hour ?? 0) ||
        (b.estimated_lane_recovery_minutes ?? 0) - (a.estimated_lane_recovery_minutes ?? 0)
    )
    .forEach((row) => {
      if (patrolUsed + row.estimated_patrol_hours <= patrolBudget && towUsed + row.estimated_tow_hours <= towBudget) {
        selected.push(row);
        patrolUsed += row.estimated_patrol_hours;
        towUsed += row.estimated_tow_hours;
      }
    });
  const recoveredMinutes = selected.reduce((sum, row) => sum + (row.estimated_lane_recovery_minutes ?? 0), 0);
  const totalRecoverableMinutes = filtered.reduce((sum, row) => sum + (row.estimated_lane_recovery_minutes ?? 0), 0);
  const recoveryCoverage = totalRecoverableMinutes > 0 ? recoveredMinutes / totalRecoverableMinutes : 0;
  const coveredRisk = selected.reduce((sum, row) => sum + row.final_priority_score, 0);
  const totalRisk = filtered.reduce((sum, row) => sum + row.final_priority_score, 0);
  const riskCoverage = totalRisk > 0 ? coveredRisk / totalRisk : 0;

  return (
    <section className="stack">
      <PageTitle title="What-If Deployment Simulator" subtitle="Test limited patrol and tow capacity against the priority queue and recovery potential." />
      <div className="simulator">
        <div className="control-panel">
          <label>Patrol units <input type="range" min="1" max="30" value={patrolUnits} onChange={(e) => setPatrolUnits(Number(e.target.value))} /></label>
          <strong>{patrolUnits}</strong>
          <label>Tow vehicles <input type="range" min="0" max="15" value={towUnits} onChange={(e) => setTowUnits(Number(e.target.value))} /></label>
          <strong>{towUnits}</strong>
          <select value={station} onChange={(e) => setStation(e.target.value)}>{stations.map((item) => <option key={item}>{item}</option>)}</select>
          <select value={timeWindow} onChange={(e) => setTimeWindow(e.target.value)}>{windows.map((item) => <option key={item}>{item}</option>)}</select>
        </div>
        <div className="sim-output">
          <div className="kpi-grid auto">
            <KpiCard label="Covered Hotspots" value={compactNumber(selected.length)} icon={MapPinned}
              hint="Hotspots that fit within the chosen patrol and tow capacity." />
            <KpiCard label="Recoverable Lane-Min" value={compactNumber(recoveredMinutes)} icon={Navigation}
              hint="Total ELRM (equivalent lane-minutes) recovered by the covered hotspots." />
            <KpiCard label="Recovery Coverage" value={percentage(recoveryCoverage)} icon={Target}
              hint="Share of the filtered lane-recovery potential captured by this deployment." />
            <KpiCard label="Patrol / Tow Used" value={`${patrolUsed}/${towUsed}`} icon={Truck}
              hint="Patrol-hours / tow-hours consumed out of the available budget." />
          </div>
          <div className="coverage-bar"><span style={{ width: `${Math.min(100, recoveryCoverage * 100)}%` }} /></div>
          <p className="method-copy">
            With {patrolUnits} patrol units and {towUnits} tow vehicles, ParkPulse can cover {percentage(recoveryCoverage)} of filtered
            lane-recovery potential, equivalent to {compactNumber(recoveredMinutes)} recoverable lane-minutes in the target window.
          </p>
          <p className="method-copy">
            The same deployment also covers {percentage(riskCoverage)} of filtered obstruction-priority risk.
          </p>
        </div>
      </div>
      <PriorityMiniList rows={selected.slice(0, 8)} />
    </section>
  );
}

function StationView({ data, onSelect }: { data: ParkPulseData; onSelect: (zoneId: string) => void }) {
  const [stationName, setStationName] = useState(data.stationSummary[0]?.police_station ?? '');
  const station = data.stationSummary.find((item) => item.police_station === stationName) ?? data.stationSummary[0];
  const stationRows = data.enforcementPlan.filter((row) => row.police_station === station?.police_station).slice(0, 5);
  return (
    <section className="stack">
      <PageTitle title="Station Priority View" subtitle="Local action plans for traffic police stations." />
      <select className="wide-select" value={station?.police_station} onChange={(e) => setStationName(e.target.value)}>
        {data.stationSummary.map((item) => <option key={item.police_station}>{item.police_station}</option>)}
      </select>
      {station && (
        <div className="kpi-grid five">
          <KpiCard label="Total Violations" value={compactNumber(station.total_violations)} icon={Car}
            hint="Total illegal-parking records logged at this station across the period." />
          <KpiCard label="High-Impact Hotspots" value={compactNumber(station.high_impact_hotspots)} icon={AlertTriangle}
            hint="Zones in this station scoring in the top 10% of obstruction risk." />
          <KpiCard label="Load Band" value={station.station_load_band ?? '—'} icon={Target}
            hint="Relative enforcement load for this station versus the city (light / normal / heavy)." />
          <KpiCard label="Recoverable Lane-Min" value={compactNumber(station.recoverable_lane_minutes)} icon={Navigation}
            hint="Total Equivalent Lane Recovery Minutes available across this station's zones." />
          <KpiCard label="Emerging / Hidden score" value={`${oneDecimal(station.avg_emerging_pressure)} / ${oneDecimal(station.avg_hidden_hotspot_score)}`} icon={ShieldCheck}
            hint="Average emerging-pressure score (recent growth) and hidden-hotspot score (risky despite low past recording) for this station, each 0-100." />
        </div>
      )}
      <PriorityMiniList rows={stationRows} onSelect={onSelect} />
    </section>
  );
}

function Methodology() {
  return (
    <section className="stack">
      <PageTitle title="Methodology" subtitle="What ParkPulse measures, and what it does not claim." />
      <article className="method-card">
        <h2>Two-Score Design</h2>
        <p>
          ParkPulse separates two jobs. Recurrence is forecast with the best validated density, history, and model signal.
          TORI is then used as the action layer: it explains why the recurring pressure is damaging, how confident we are, and what
          enforcement response fits.
        </p>
        <p>
          This is intentional. The validation view keeps the predictive metric and the action metric visible side by side so the system
          does not pretend one score solves every decision.
        </p>
      </article>
      <article className="method-card">
        <h2>Traffic Obstruction Risk Index</h2>
        <p>
          ParkPulse estimates a Traffic Obstruction Risk Index using violation density, recurrence,
          time-window pressure, junction criticality, vehicle obstruction footprint, violation severity,
          validation confidence, repeat/chronic vehicle pressure, patrol-gap pressure, and enforcement-exposure adjustment.
        </p>
        <p>
          Since direct speed or queue-length data is not available, the score is used as an
          enforcement-prioritization estimate, not as an exact congestion measurement.
        </p>
      </article>
      <article className="method-card">
        <h2>Repeat Pressure and Patrol Gap</h2>
        <p>
          Repeat pressure counts whether the same anonymized vehicle ids appear repeatedly, especially chronic 3+ record vehicles.
          It helps separate one-off violations from zones that need fixed-window enforcement or towing follow-up.
        </p>
        <p>
          Patrol gap compares risk against historical officer/device/active-day coverage. A high patrol gap means the hotspot is risky
          relative to how much enforcement attention it has historically received; it is not a live roster feed.
        </p>
      </article>
      <article className="method-card">
        <h2>Exposure Adjustment</h2>
        <p>
          High violation counts can reflect both true parking pressure and enforcement visibility.
          ParkPulse compares raw hotspot intensity with exposure-adjusted rankings using device,
          officer, station, and active-day coverage estimates.
        </p>
      </article>
      <article className="method-card">
        <h2>Equivalent Lane Recovery Minutes (ELRM)</h2>
        <p>
          ParkPulse estimates Equivalent Lane Recovery Minutes as an operational planning estimate for how much running-lane time may be recovered
          if the recommended intervention is executed in the target window. It combines obstruction intensity, target-window duration,
          carriageway context, recurrence, action fit, and confidence.
        </p>
        <p>
          ELRM is reported as a <strong>range</strong> (conservative to optimistic enforcement effectiveness), not a single point, so the
          assumptions stay explicit. It is a decision-support estimate, not a live speed or queue-length measurement.
        </p>
      </article>
      <article className="method-card">
        <h2>Real-World Control-Room Metrics</h2>
        <p>
          ParkPulse now reports capacity-loss pressure, queue-spillback risk, clearance SLA, evidence quality, and recovery per
          resource-hour. These are more operational than a single index: one tells whether the road is likely losing capacity, one tells
          whether the queue can block a junction, one gives the response deadline, and one tells whether the evidence is strong enough to
          dispatch confidently.
        </p>
        <p>
          These metrics remain honest modelled estimates because the dataset has enforcement records, not live speed, queue, or signal-health feeds.
          In production, the same layer can absorb GPS/probe speed, signal-health, towing availability, and officer roster data without
          changing the command workflow.
        </p>
      </article>
      <article className="method-card">
        <h2>Deployment Policy Lab</h2>
        <p>
          ParkPulse compares multiple dispatch rules under lean, standard, and surge patrol/tow budgets: operational priority, ELRM
          maximum recovery, recovery per resource-hour, capacity-loss first, spillback first, TORI-only, and raw density. The goal is not
          to crown a magic score; it is to show what each rule sacrifices when resources are limited.
        </p>
        <p>
          This gives judges and police leaders a transparent planning back-test: if the city has ten patrol units and three tow vehicles,
          which rule recovers more lane capacity, covers more high-spillback zones, and stays evidence-safe?
        </p>
      </article>
      <article className="method-card">
        <h2>Carriageway Class, Junction Clearance &amp; Corridors</h2>
        <p>
          Each hotspot is labelled with a <strong>carriageway recovery class</strong> (full-lane, partial-lane, or edge/footpath) from
          observed main-road, heavy-vehicle, and context shares, and a small capped <strong>junction-clearance benefit</strong> where
          signal/crossing-approach context is present.
        </p>
        <p>
          Repeated hotspots are linked into <strong>inferred corridors</strong> with a data-fitted centerline and a bottleneck class.
          This corridor geometry is inferred purely from the spatial distribution of recorded violations — it is not surveyed road
          centerline or lane-level GIS.
        </p>
      </article>
      <article className="method-card">
        <h2>Built Only on the Provided Dataset</h2>
        <p>
          Every analytical layer in ParkPulse — hotspots, TORI, corridors, risk scores, and ELRM — is derived <strong>only</strong> from
          the provided enforcement violation records. There is no purchased traffic or speed feed, and no map-matching
          service. The command map uses MapMyIndia/Mappls as the geographic context layer; it feeds no analysis, and the
          risk layers still render if the basemap is unavailable.
        </p>
        <p>
          That means ParkPulse is deployable on the data a city already owns, with no data-sharing agreement. Where richer signals would
          help — surveyed lane geometry, signal-health telemetry, live workforce rosters, probe-vehicle speeds — they are marked as
          optional future integrations, never silently assumed.
        </p>
      </article>
      <article className="method-card">
        <h2>Acknowledgements</h2>
        <p>
          The enforcement dataset was provided through Flipkart Gridlock Round 2 by Bengaluru Traffic Police / ASTraM for
          Theme 1: Poor Visibility on Parking-Induced Congestion.
          MapMyIndia / Mappls provides the geographic context layer when the configured web key is active.
        </p>
        <p>
          ParkPulse generates the derived hotspot rankings, obstruction-risk estimates, field briefs, corridor overlays and
          deployment simulation from the provided enforcement records.
        </p>
      </article>
      <article className="method-card">
        <h2>Operational Time Windows</h2>
        <p>Hotspots are analysed inside seven daily enforcement windows so deployment matches when a zone is actually under pressure.</p>
        <dl className="glossary">
          <div><dt>00:00–06:00 Night</dt><dd>Late night / early morning — often goods-vehicle and long-stay parking.</dd></div>
          <div><dt>06:00–09:00 AM build-up</dt><dd>Morning traffic build-up before the commercial peak.</dd></div>
          <div><dt>09:00–12:00 AM peak</dt><dd>Commercial morning peak — markets and offices opening.</dd></div>
          <div><dt>12:00–15:00 Midday</dt><dd>Market and midday pressure.</dd></div>
          <div><dt>15:00–18:00 PM build-up</dt><dd>School dispersal and evening build-up.</dd></div>
          <div><dt>18:00–22:00 PM peak</dt><dd>Evening commercial peak label — unusually sparse in the provided records, so ParkPulse flags it as coverage risk.</dd></div>
          <div><dt>22:00–24:00 Late</dt><dd>Late evening wind-down.</dd></div>
        </dl>
      </article>
      <article className="method-card">
        <h2>Glossary</h2>
        <dl className="glossary">
          <div><dt>TORI</dt><dd>Traffic Obstruction Risk Index (0–100). An explainable priority score, not a measured speed.</dd></div>
          <div><dt>ELRM</dt><dd>Equivalent Lane Recovery Minutes — estimated running-lane time recovered if a zone is actioned, shown as a low–high range. A modelled estimate, not measured delay.</dd></div>
          <div><dt>Capacity-loss pressure</dt><dd>How strongly a hotspot is likely to reduce usable carriageway capacity before enforcement.</dd></div>
          <div><dt>Queue spillback risk</dt><dd>Likelihood that an obstruction can push queues into a junction, signal approach, or main-road choke point.</dd></div>
          <div><dt>Clearance SLA</dt><dd>Suggested response deadline: immediate, rapid, fixed-window, or watchlist.</dd></div>
          <div><dt>Evidence quality</dt><dd>How much trust to place in a hotspot score from record validation, recurrence volume, and observed road-space context.</dd></div>
          <div><dt>Carriageway recovery class</dt><dd>How much running lane a cleared obstruction frees: full-lane, partial-lane, or edge/footpath.</dd></div>
          <div><dt>Bottleneck class</dt><dd>How a hotspot most likely chokes the road (arterial kerb-lane choke, junction-mouth blocker, metro/market spillover, …).</dd></div>
          <div><dt>Junction sensitivity</dt><dd>How exposed a zone is to a signal/crossing approach, from observed context.</dd></div>
          <div><dt>Exposure adjustment</dt><dd>Down-weights zones that look busy only because they are policed/recorded more often.</dd></div>
          <div><dt>Recovery / resource-hr</dt><dd>Lane-minutes recovered per patrol+tow hour — deployment efficiency.</dd></div>
          <div><dt>Enforcement ROI</dt><dd>Estimated return: expected obstruction reduction per resource-hour.</dd></div>
          <div><dt>Confidence band</dt><dd>Data trust (High/Medium/Low) from record volume, validation status and active days.</dd></div>
          <div><dt>Robust Top-20</dt><dd>Share of top-20 hotspots that stay top-20 using only high-confidence records — a stability check.</dd></div>
          <div><dt>Capture@K</dt><dd>Share of next-period high-pressure cells captured by the top-K ranked zones (time-safe validation).</dd></div>
        </dl>
      </article>
      <article className="method-card highlight">
        <h2>Product Principle</h2>
        <p>ParkPulse does not just show illegal parking. It tells Bengaluru Traffic Police which illegal parking to solve first.</p>
      </article>
    </section>
  );
}

function PageTitle({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="page-title">
      <h1>{title}</h1>
      <p>{subtitle}</p>
    </div>
  );
}

function PriorityMiniList({ rows, onSelect }: { rows: EnforcementPlanRow[]; onSelect?: (zoneId: string) => void }) {
  if (rows.length === 0) return <EmptyState title="No feasible zones" body="Adjust filters or resource constraints." />;
  return (
    <div className="mini-list">
      {rows.map((row) => (
        <button key={row.zone_id} type="button" onClick={() => onSelect?.(row.zone_id)}>
          <span>#{row.rank}</span>
          <strong>{row.zone_name}</strong>
          <small>{row.police_station} · {row.best_time_window}</small>
          <ActionChip action={row.recommended_action} />
        </button>
      ))}
    </div>
  );
}

function MiniBarChart({ data, xKey }: { data: ChartPoint[]; xKey: keyof ChartPoint }) {
  if (!data || data.length === 0) return <EmptyState title="No chart data" body="Pipeline drilldown export is missing this chart." />;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip />
        <Bar dataKey="value" fill="#2874F0" radius={[6, 6, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function MiniLineChart({ data }: { data: ChartPoint[] }) {
  if (!data || data.length === 0) return <EmptyState title="No trend data" body="Pipeline recurrence export is missing." />;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="date" hide />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip />
        <Line dataKey="value" stroke="#FB641B" strokeWidth={3} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

function MiniPieChart({ data }: { data: ChartPoint[] }) {
  if (!data || data.length === 0) return <EmptyState title="No mix data" body="Pipeline mix export is missing." />;
  const colors = ['#2874F0', '#FB641B', '#32A66A', '#8060D0', '#5F6C7B'];
  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" innerRadius={58} outerRadius={92} paddingAngle={3}>
          {data.map((_, index) => <Cell key={index} fill={colors[index % colors.length]} />)}
        </Pie>
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  );
}

function LoadingState() {
  return (
    <div className="loading-state">
      <div className="brand-mark">P</div>
      <strong>Loading ParkPulse Bengaluru</strong>
      <span>Preparing command-center intelligence...</span>
    </div>
  );
}

export default App;
