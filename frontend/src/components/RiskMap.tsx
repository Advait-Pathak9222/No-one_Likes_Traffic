import { useEffect, useMemo, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { CongestionSegmentFeature, CongestionSegmentsGeoJson, HotspotFeature, LaneHotspotFeature } from '../types';
import { oneDecimal } from '../utils/format';

type MapFeature = HotspotFeature | LaneHotspotFeature;

interface RiskMapProps {
  segments: CongestionSegmentsGeoJson;
  hotspots: MapFeature[];
  selectedId?: string;
  onSelect: (zoneId: string) => void;
  fallback: React.ReactNode;
  compact?: boolean;
  focusSelected?: boolean;
  showControls?: boolean;
  initialMinScore?: number;
  maxVisible?: number;
}

interface HotspotView {
  zoneId: string;
  zoneName: string;
  station: string;
  action: string;
  confidence: string;
  score: number;
  tori: number;
  timeWindow: string;
  laneContext: string;
  issue: string;
  bottleneck?: string;
  lon: number;
  lat: number;
}

function readHotspot(feature: MapFeature): HotspotView {
  const props = feature.properties as Record<string, unknown>;
  const isLane = 'lane_obstruction_proxy_0_100' in props;
  const num = (value: unknown, fallbackValue = 0): number =>
    typeof value === 'number' && Number.isFinite(value) ? value : fallbackValue;
  const str = (value: unknown, fallbackValue = ''): string =>
    typeof value === 'string' ? value : fallbackValue;
  const [lon, lat] = feature.geometry.coordinates;
  return {
    zoneId: str(props.zone_id),
    zoneName: str(props.zone_name, 'Hotspot'),
    station: str(props.police_station, '—'),
    action: str(props.recommended_action, 'Targeted patrol'),
    confidence: str(props.confidence_band, 'Medium'),
    score: isLane ? num(props.lane_obstruction_proxy_0_100) : num(props.final_priority_score),
    tori: isLane ? num(props.final_tori_0_100) : num(props.final_priority_score),
    timeWindow: isLane ? str(props.time_window) : str(props.best_time_window),
    laneContext: isLane ? str(props.lane_context, 'Hotspot centroid') : 'Hotspot centroid',
    issue: isLane ? str(props.dominant_lane_issue) : str(props.reasoning),
    bottleneck: typeof props.bottleneck_class === 'string' ? props.bottleneck_class : undefined,
    lon,
    lat
  };
}

function hotspotColor(action: string): string {
  const lower = action.toLowerCase();
  if (lower.includes('tow')) return '#fb641b';
  if (lower.includes('engineering')) return '#7c5cff';
  if (lower.includes('metro') || lower.includes('market')) return '#2fb673';
  if (lower.includes('fixed')) return '#2874f0';
  return '#9fb0c7';
}

function segmentWeight(segment: CongestionSegmentFeature): number {
  const score = segment.properties.obstruction_score || 0;
  return Math.max(2.5, Math.min(8.5, 2 + score / 18));
}

function toLatLng(coord: [number, number]): L.LatLngTuple {
  return [coord[1], coord[0]];
}

function boundsFromCoords(coords: Array<[number, number]>): L.LatLngBounds | null {
  const valid = coords.filter(([lon, lat]) => Number.isFinite(lon) && Number.isFinite(lat));
  if (valid.length === 0) return null;
  return L.latLngBounds(valid.map(toLatLng));
}

export function RiskMap({
  segments,
  hotspots,
  selectedId,
  onSelect,
  fallback,
  compact = false,
  focusSelected = false,
  showControls = true,
  initialMinScore = 80,
  maxVisible
}: RiskMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const hotspotLayerRef = useRef<L.LayerGroup | null>(null);
  const corridorCasingLayerRef = useRef<L.GeoJSON | null>(null);
  const corridorLayerRef = useRef<L.GeoJSON | null>(null);
  const selectedLayerRef = useRef<L.LayerGroup | null>(null);
  const onSelectRef = useRef(onSelect);
  const fittedRef = useRef(false);
  onSelectRef.current = onSelect;

  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [hovered, setHovered] = useState<HotspotView | null>(null);

  const [station, setStation] = useState('All');
  const [action, setAction] = useState('All');
  const [minScore, setMinScore] = useState(initialMinScore);
  const [highConfidenceOnly, setHighConfidenceOnly] = useState(false);
  const [showCorridors, setShowCorridors] = useState(true);

  const views = useMemo(() => hotspots.map(readHotspot), [hotspots]);
  const selectedView = useMemo(
    () => views.find((view) => view.zoneId === selectedId) ?? null,
    [selectedId, views]
  );
  const stations = useMemo(
    () => ['All', ...Array.from(new Set(views.map((view) => view.station))).sort()],
    [views]
  );
  const actions = useMemo(
    () => ['All', ...Array.from(new Set(views.map((view) => view.action))).sort()],
    [views]
  );

  const visible = useMemo(() => {
    const sourceViews =
      focusSelected && selectedView
        ? views.filter((view) => view.station === selectedView.station || view.zoneId === selectedView.zoneId)
        : views;
    const filtered = sourceViews.filter(
      (view) =>
        view.score >= minScore &&
        (station === 'All' || view.station === station) &&
        (action === 'All' || view.action === action) &&
        (!highConfidenceOnly || view.confidence === 'High')
    );
    const sorted = [...filtered].sort((a, b) => b.score - a.score);
    const capped = typeof maxVisible === 'number' ? sorted.slice(0, maxVisible) : sorted;
    if (selectedView && !capped.some((view) => view.zoneId === selectedView.zoneId)) {
      capped.push(selectedView);
    }
    return capped;
  }, [action, focusSelected, highConfidenceOnly, maxVisible, minScore, selectedView, station, views]);

  const corridorFeatures = useMemo(() => {
    if (!showCorridors) return [];
    const stationFilter = focusSelected && selectedView ? selectedView.station : station;
    return segments.features.filter((feature) => stationFilter === 'All' || feature.properties.station === stationFilter);
  }, [focusSelected, segments.features, selectedView, showCorridors, station]);

  useEffect(() => {
    if (!containerRef.current) return;
    let map: L.Map | null = null;
    try {
      map = L.map(containerRef.current, {
        preferCanvas: true,
        zoomControl: true,
        attributionControl: true,
        scrollWheelZoom: true,
        zoomSnap: 0.25
      }).setView([12.97, 77.59], 10.4);

      L.tileLayer('/data/tiles/carto_light/{z}/{x}/{y}.png', {
        minZoom: 10,
        maxNativeZoom: 13,
        maxZoom: 20,
        attribution: '© OpenStreetMap contributors © CARTO (local basemap cache for demo reliability)'
      }).addTo(map);

      L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        subdomains: 'abcd',
        minZoom: 10,
        maxNativeZoom: 19,
        maxZoom: 20,
        opacity: 0.82,
        attribution: '© OpenStreetMap contributors © CARTO (basemap for visual context only)'
      }).addTo(map);

      map.createPane('parkpulse-corridor-casing').style.zIndex = '410';
      map.createPane('parkpulse-corridors').style.zIndex = '420';
      map.createPane('parkpulse-hotspots').style.zIndex = '440';
      map.createPane('parkpulse-selected').style.zIndex = '455';

      corridorCasingLayerRef.current = L.geoJSON(undefined, {
        pane: 'parkpulse-corridor-casing',
        style: (feature) => ({
          color: '#ffffff',
          opacity: 0.86,
          weight: segmentWeight(feature as unknown as CongestionSegmentFeature) + 3.2,
          lineCap: 'round',
          lineJoin: 'round'
        })
      }).addTo(map);

      corridorLayerRef.current = L.geoJSON(undefined, {
        pane: 'parkpulse-corridors',
        style: (feature) => {
          const segment = feature as unknown as CongestionSegmentFeature;
          return {
            color: segment.properties.color || '#2874f0',
            opacity: 0.96,
            weight: segmentWeight(segment),
            lineCap: 'round',
            lineJoin: 'round'
          };
        }
      }).addTo(map);

      hotspotLayerRef.current = L.layerGroup([], { pane: 'parkpulse-hotspots' }).addTo(map);
      selectedLayerRef.current = L.layerGroup([], { pane: 'parkpulse-selected' }).addTo(map);
      mapRef.current = map;
      requestAnimationFrame(() => map?.invalidateSize());
      setTimeout(() => map?.invalidateSize(), 250);
      setReady(true);
    } catch (error) {
      if (typeof console !== 'undefined') console.warn('Leaflet map failed, using fallback', error);
      setFailed(true);
    }

    return () => {
      mapRef.current = null;
      map?.remove();
    };
  }, []);

  useEffect(() => {
    const layer = hotspotLayerRef.current;
    if (!ready || !layer) return;
    layer.clearLayers();
    visible.forEach((view) => {
      const marker = L.circleMarker([view.lat, view.lon], {
        pane: 'parkpulse-hotspots',
        radius: Math.max(5, Math.min(13, 4 + view.score / 10)),
        color: '#ffffff',
        weight: 1.6,
        fillColor: hotspotColor(view.action),
        fillOpacity: 0.84
      });
      marker.on('click', () => onSelectRef.current(view.zoneId));
      marker.on('mouseover', () => setHovered(view));
      marker.on('mouseout', () => setHovered(null));
      marker.addTo(layer);
    });
  }, [ready, visible]);

  useEffect(() => {
    if (!ready) return;
    corridorCasingLayerRef.current?.clearLayers();
    corridorLayerRef.current?.clearLayers();
    const collection = {
      type: 'FeatureCollection',
      features: corridorFeatures
    };
    corridorCasingLayerRef.current?.addData(collection as any);
    corridorLayerRef.current?.addData(collection as any);
  }, [corridorFeatures, ready]);

  useEffect(() => {
    const layer = selectedLayerRef.current;
    if (!ready || !layer) return;
    layer.clearLayers();
    if (!selectedView) return;
    L.circleMarker([selectedView.lat, selectedView.lon], {
      pane: 'parkpulse-selected',
      radius: 17,
      color: '#111827',
      weight: 4,
      fillColor: '#ffffff',
      fillOpacity: 0.06
    }).addTo(layer);
  }, [ready, selectedView]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map || views.length === 0) return;
    const coords: Array<[number, number]> = [];
    if (focusSelected && selectedView) {
      coords.push([selectedView.lon, selectedView.lat]);
      visible.slice(0, 80).forEach((view) => coords.push([view.lon, view.lat]));
      corridorFeatures.slice(0, 500).forEach((feature) => {
        feature.geometry.coordinates.forEach((coord) => coords.push(coord));
      });
    } else {
      if (fittedRef.current) return;
      views.forEach((view) => coords.push([view.lon, view.lat]));
    }
    const bounds = boundsFromCoords(coords);
    if (!bounds) return;
    map.fitBounds(bounds, {
      padding: focusSelected ? [92, 92] : [56, 56],
      maxZoom: focusSelected ? 15.5 : 13,
      animate: focusSelected
    });
    fittedRef.current = true;
    setTimeout(() => map.invalidateSize(), 120);
  }, [corridorFeatures, focusSelected, ready, selectedView, views, visible]);

  if (failed) {
    return <>{fallback}</>;
  }

  return (
    <div className={`map-shell ${compact ? 'compact' : ''} ${showControls ? '' : 'no-controls'}`}>
      {showControls && (
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
          <label className="toggle-pill">
            <input type="checkbox" checked={showCorridors} onChange={(event) => setShowCorridors(event.target.checked)} />
            Corridor risk
          </label>
        </div>
      )}

      <div className="risk-map-frame">
        <div ref={containerRef} className="risk-map-canvas" />
        <div className="risk-legend">
          <strong>Inferred corridor obstruction risk</strong>
          <span><i style={{ background: '#2874F0' }} /> Low</span>
          <span><i style={{ background: '#F4C430' }} /> Moderate</span>
          <span><i style={{ background: '#D93025' }} /> Severe</span>
          <small>Inferred from violation coordinates — not live vehicle speed.</small>
        </div>
        {hovered && (
          <div className="risk-map-tooltip">
            <strong>{hovered.zoneName}</strong>
            <span>{hovered.station} · {hovered.laneContext}</span>
            <span>Lane score {oneDecimal(hovered.score)} · TORI {oneDecimal(hovered.tori)}</span>
            {hovered.bottleneck && <span className="risk-tag">{hovered.bottleneck}</span>}
            <span>{hovered.timeWindow} · {hovered.confidence} confidence</span>
            {hovered.issue && <span className="risk-issue">{hovered.issue}</span>}
            <button type="button" onClick={() => onSelectRef.current(hovered.zoneId)}>Open brief</button>
          </div>
        )}
      </div>

      <div className="map-footer">
        <span>{visible.length} hotspots shown</span>
        <span>{corridorFeatures.length} corridor segments</span>
        <span>Bengaluru basemap · risk layers from ParkPulse data</span>
      </div>
    </div>
  );
}

export default RiskMap;
