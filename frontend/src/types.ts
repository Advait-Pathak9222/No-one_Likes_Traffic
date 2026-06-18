export type ConfidenceBand = 'Low' | 'Medium' | 'High' | string;

export type ActionType =
  | 'Tow + fixed-window enforcement'
  | 'Engineering fix + targeted patrol'
  | 'Fixed-window enforcement'
  | 'Targeted patrol'
  | 'Metro/market spillover control'
  | 'Watchlist monitoring'
  | string;

export interface Metrics {
  total_violations?: number | null;
  total_hotspots?: number | null;
  high_impact_hotspots?: number | null;
  predicted_risk_tomorrow?: number | null;
  tow_priority_zones?: number | null;
  average_confidence?: number | null;
  capture_at_10?: number | null;
  capture_at_20?: number | null;
  precision_at_10?: number | null;
  precision_at_20?: number | null;
  raw_count_baseline_capture_at_20?: number | null;
  parkpulse_capture_at_20?: number | null;
  robust_top20_overlap?: number | null;
  headline_recurrence_signal?: string | null;
  headline_recurrence_capture_at_20?: number | null;
  selected_forecast_model?: string | null;
  selected_forecast_capture_at_20?: number | null;
  weighted_obstruction_capture_at_20?: number | null;
  time_safe_historical_capture_at_20?: number | null;
  tori_capture_at_20?: number | null;
  elrm_capture_at_20?: number | null;
  elrm_efficiency_capture_at_20?: number | null;
  capacity_loss_capture_at_20?: number | null;
  spillback_risk_capture_at_20?: number | null;
  operational_priority_capture_at_20?: number | null;
  evidence_quality_capture_at_20?: number | null;
  best_validation_method_at_20?: string | null;
  best_validation_capture_at_20?: number | null;
  evening_records?: number | null;
  night_records?: number | null;
  evening_to_night_record_ratio?: number | null;
  evening_window_quality_note?: string | null;
  judge_positioning?: string | null;
  top20_lane_recovery_minutes?: number | null;
  top20_lane_recovery_minutes_low?: number | null;
  top20_lane_recovery_minutes_high?: number | null;
  top20_capacity_loss_minutes?: number | null;
  top20_mean_spillback_risk?: number | null;
  top20_mean_evidence_quality?: number | null;
  top20_mean_repeat_pressure?: number | null;
  top20_mean_patrol_gap?: number | null;
  plan_lane_recovery_minutes?: number | null;
  plan_lane_recovery_minutes_low?: number | null;
  plan_lane_recovery_minutes_high?: number | null;
  plan_capacity_loss_minutes?: number | null;
  high_spillback_risk_zones?: number | null;
  chronic_repeat_priority_zones?: number | null;
  patrol_gap_priority_zones?: number | null;
  immediate_clearance_zones?: number | null;
  median_clearance_sla_minutes?: number | null;
  avg_evidence_quality_score?: number | null;
  recovery_minutes_per_resource_hour?: number | null;
  best_station_for_recovery?: string | null;
  standard_budget_policy?: string | null;
  standard_budget_best_recovery_policy?: string | null;
  standard_budget_recovery_minutes?: number | null;
  standard_budget_capacity_loss_minutes?: number | null;
  standard_budget_high_spillback_zones?: number | null;
  standard_budget_immediate_clearance_zones?: number | null;
  standard_budget_recovery_per_resource_hour?: number | null;
  standard_budget_mean_evidence_quality?: number | null;
  parkpulse_vs_tori_recovery_uplift_pct?: number | null;
  parkpulse_vs_density_recovery_uplift_pct?: number | null;
  policy_lab_note?: string | null;
}

export interface EnforcementPlanRow {
  rank: number;
  zone_id: string;
  zone_name: string;
  police_station: string;
  best_time_window: string;
  expected_violations: number;
  expected_impact_score: number;
  final_priority_score: number;
  stable_pcis: number;
  emerging_score: number;
  confidence_band: ConfidenceBand;
  recommended_action: ActionType;
  reasoning: string;
  repeat_vehicle_record_share?: number;
  chronic_vehicle_record_share?: number;
  multi_station_repeat_vehicle_share?: number;
  repeat_pressure_score_0_100?: number;
  chronic_vehicle_pressure_0_100?: number;
  patrol_gap_score_0_100?: number;
  patrol_gap_band?: string;
  estimated_patrol_hours: number;
  estimated_tow_hours: number;
  enforcement_roi: number;
  estimated_capacity_loss_minutes?: number;
  capacity_loss_pressure_0_100?: number;
  queue_spillback_risk_0_100?: number;
  clearance_sla_minutes?: number;
  clearance_decision_band?: string;
  evidence_quality_score_0_100?: number;
  operational_priority_score_0_100?: number;
  estimated_lane_recovery_minutes?: number;
  estimated_lane_recovery_minutes_low?: number;
  estimated_lane_recovery_minutes_high?: number;
  recovery_minutes_per_resource_hour?: number;
  carriageway_recovery_class?: string;
  junction_clearance_bonus?: number;
  impact_confidence_note?: string;
  centroid_lat: number;
  centroid_lon: number;
}

export interface HotspotFeature {
  type: 'Feature';
  geometry: {
    type: 'Point';
    coordinates: [number, number];
  };
  properties: {
    zone_id: string;
    zone_name: string;
    police_station: string;
    centroid_lat: number;
    centroid_lon: number;
    tori_score: number;
    final_priority_score: number;
    stable_pcis: number;
    emerging_score: number;
    recommended_action: ActionType;
    confidence_band: ConfidenceBand;
    best_time_window: string;
    expected_violations: number;
    expected_impact_score: number;
    enforcement_roi: number;
    reasoning: string;
    repeat_pressure_score_0_100?: number | null;
    chronic_vehicle_pressure_0_100?: number | null;
    patrol_gap_score_0_100?: number | null;
    patrol_gap_band?: string | null;
  };
}

export interface HotspotsGeoJson {
  type: 'FeatureCollection';
  features: HotspotFeature[];
}

export interface ReasonCode {
  reason: string;
  evidence: string;
  support_level: 'observed' | 'observed-low-volume' | 'proxy' | 'external-feed-required' | string;
}

export interface MitigationStep {
  phase: string;
  step: string;
}

export interface LaneHotspotFeature {
  type: 'Feature';
  geometry: {
    type: 'Point';
    coordinates: [number, number];
  };
  properties: {
    zone_id: string;
    zone_name: string;
    police_station: string;
    time_window: string;
    lane_context: string;
    dominant_lane_issue: string;
    lane_obstruction_proxy_0_100: number;
    lane_obstruction_band: string;
    final_tori_0_100: number;
    violation_count: number;
    confidence_band: ConfidenceBand;
    recommended_action: ActionType;
    repeat_pressure_score_0_100?: number | null;
    chronic_vehicle_pressure_0_100?: number | null;
    patrol_gap_score_0_100?: number | null;
    patrol_gap_band?: string | null;
    mitigation_plan: MitigationStep[];
    reason_codes: ReasonCode[];
    officer_brief: string;
    historical_workforce_proxy: string;
    signal_health_status: string;
    live_workforce_status: string;
    exact_location_note: string;
    bottleneck_class?: string | null;
    junction_sensitivity_band?: string | null;
    corridor_name?: string | null;
    corridor_linked_hotspots?: number | null;
    corridor_length_km?: number | null;
  };
}

export interface LaneHotspotsGeoJson {
  type: 'FeatureCollection';
  features: LaneHotspotFeature[];
}

export interface CongestionSegmentFeature {
  type: 'Feature';
  geometry: {
    type: 'LineString';
    coordinates: [number, number][];
  };
  properties: {
    segment_id: string;
    station: string;
    corridor_name: string;
    snap_method?: string | null;
    obstruction_score: number;
    risk_band: 'low' | 'moderate' | 'severe' | string;
    risk_label: string;
    color: string;
    max_tori: number;
    total_violations: number;
    top_time_window: string;
    lane_context: string;
    dominant_issue: string;
    bottleneck_class?: string | null;
    recommended_action: string;
  };
}

export interface CongestionSegmentsGeoJson {
  type: 'FeatureCollection';
  features: CongestionSegmentFeature[];
}

export interface CorridorSummary {
  rank: number;
  corridor_id: string;
  station: string;
  corridor_name: string;
  linked_hotspots: number;
  total_violations: number;
  approx_length_m: number;
  approx_length_km: number;
  max_tori: number;
  mean_obstruction: number;
  dominant_bottleneck: string;
  peak_window: string;
  centroid_lat: number;
  centroid_lon: number;
}

export interface RoadspaceHotspot {
  zone_id: string;
  zone_name_readable: string;
  station: string;
  time_window_readable: string;
  centroid_lat: number;
  centroid_lon: number;
  lane_context: string;
  dominant_lane_issue: string;
  lane_obstruction_proxy_0_100: number;
  lane_obstruction_band: string;
  final_tori_0_100: number;
  violation_count: number;
  confidence_band: ConfidenceBand;
  recommended_action: ActionType;
  repeat_vehicle_record_share?: number | null;
  chronic_vehicle_record_share?: number | null;
  multi_station_repeat_vehicle_share?: number | null;
  repeat_pressure_score_0_100?: number | null;
  chronic_vehicle_pressure_0_100?: number | null;
  patrol_gap_score_0_100?: number | null;
  patrol_gap_band?: string | null;
  historical_workforce_proxy: string;
  signal_health_status: string;
  live_workforce_status: string;
  reason_codes: ReasonCode[];
  mitigation_plan: MitigationStep[];
  officer_brief: string;
  bottleneck_class?: string | null;
  junction_sensitivity_band?: string | null;
  junction_sensitivity_label?: string | null;
  corridor_name?: string | null;
  corridor_linked_hotspots?: number | null;
  corridor_length_km?: number | null;
}

export interface StationSummary {
  police_station: string;
  total_violations: number;
  high_impact_hotspots: number;
  avg_priority_score: number;
  peak_time_window: string;
  top_action: string;
  confidence_band: ConfidenceBand;
  patrol_hours_required: number;
  tow_hours_required: number;
  recoverable_lane_minutes?: number;
  recovery_minutes_per_resource_hour?: number;
  avg_repeat_pressure?: number;
  avg_patrol_gap?: number;
}

export interface ForecastSummary {
  created_date?: string;
  best_time_window: string;
  zone_id: string;
  zone_name: string;
  police_station: string;
  predicted_impact_score: number;
  predicted_violation_count: number;
  emerging_score: number;
  confidence_band: ConfidenceBand;
}

export interface ChartPoint {
  name?: string;
  hour?: number;
  date?: string;
  value: number;
}

export interface Drilldown {
  zone_id: string;
  zone_name: string;
  hourly_pattern: ChartPoint[];
  weekday_pattern: ChartPoint[];
  violation_mix: ChartPoint[];
  vehicle_mix: ChartPoint[];
  validation_status_mix: ChartPoint[];
  recurrence_trend: ChartPoint[];
  explanation: string;
}

export interface ParkPulseData {
  metrics: Metrics;
  enforcementPlan: EnforcementPlanRow[];
  hotspots: HotspotsGeoJson;
  stationSummary: StationSummary[];
  forecastSummary: ForecastSummary[];
  drilldowns: Drilldown[];
  laneHotspots: LaneHotspotsGeoJson;
  roadspaceIntelligence: RoadspaceHotspot[];
  congestionSegments: CongestionSegmentsGeoJson;
  corridorSummary: CorridorSummary[];
  usingMockData: boolean;
}
