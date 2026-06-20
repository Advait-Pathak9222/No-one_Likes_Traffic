import { Printer } from 'lucide-react';
import type { EnforcementPlanRow, RoadspaceHotspot } from '../types';
import { compactNumber, oneDecimal } from '../utils/format';

interface ZoneBriefProps {
  plan: EnforcementPlanRow;
  roadspace?: RoadspaceHotspot;
}

function recoveryRange(plan: EnforcementPlanRow): string {
  const expected = plan.estimated_lane_recovery_minutes;
  const low = plan.estimated_lane_recovery_minutes_low;
  const high = plan.estimated_lane_recovery_minutes_high;
  if (expected === undefined || expected === null) return '—';
  if (low !== undefined && high !== undefined) {
    return `${oneDecimal(expected)} min (range ${oneDecimal(low)}–${oneDecimal(high)})`;
  }
  return `${oneDecimal(expected)} min`;
}

export function ZoneBrief({ plan, roadspace }: ZoneBriefProps) {
  return (
    <article className="zone-brief" id="print-root">
      <header className="brief-header">
        <div>
          <span className="brief-eyebrow">ParkPulse Field Brief · Bengaluru Traffic Police</span>
          <h2>{plan.zone_name}</h2>
          <p>{plan.police_station} · {plan.best_time_window} · Priority rank #{plan.rank}</p>
        </div>
        <button type="button" className="no-print brief-print" onClick={() => window.print()}>
          <Printer size={16} /> Print brief
        </button>
      </header>

      <div className="brief-chips">
        <span className="brief-chip action">{plan.recommended_action}</span>
        <span className="brief-chip">{plan.confidence_band} confidence</span>
        <span className="brief-chip">Repeat pressure {oneDecimal(plan.repeat_pressure_score_0_100)}</span>
        <span className="brief-chip">Patrol gap {oneDecimal(plan.patrol_gap_score_0_100)}</span>
        {plan.hotspot_persistence_class && <span className="brief-chip">{plan.hotspot_persistence_class}</span>}
        {plan.hidden_hotspot_flag && <span className="brief-chip">{plan.hidden_hotspot_flag}</span>}
        {plan.time_window_reliability_band && <span className="brief-chip">{plan.time_window_reliability_band}</span>}
        {plan.station_load_band && <span className="brief-chip">{plan.station_load_band}</span>}
        {plan.carriageway_recovery_class && <span className="brief-chip">{plan.carriageway_recovery_class}</span>}
        {roadspace?.bottleneck_class && <span className="brief-chip">{roadspace.bottleneck_class}</span>}
      </div>

      <div className="brief-metrics">
        <div><span>Queue spillback risk</span><strong>{oneDecimal(plan.queue_spillback_risk_0_100)}</strong></div>
        <div><span>Clearance SLA</span><strong>{compactNumber(plan.clearance_sla_minutes)} min</strong></div>
        <div><span>Capacity pressure</span><strong>{oneDecimal(plan.capacity_loss_pressure_0_100)}</strong></div>
        <div><span>Lane-min at risk</span><strong>{compactNumber(plan.estimated_capacity_loss_minutes)}</strong></div>
        <div><span>Equivalent lane recovery</span><strong>{recoveryRange(plan)}</strong></div>
        <div><span>Repeat pressure</span><strong>{oneDecimal(plan.repeat_pressure_score_0_100)}</strong></div>
        <div><span>Patrol gap</span><strong>{oneDecimal(plan.patrol_gap_score_0_100)}</strong></div>
        <div><span>Emerging score</span><strong>{oneDecimal(plan.emerging_hotspot_score_0_100)}</strong></div>
        <div><span>Hidden score</span><strong>{oneDecimal(plan.hidden_hotspot_score_0_100)}</strong></div>
        <div><span>Time-window reliability</span><strong>{oneDecimal(plan.time_window_reliability_score_0_100)}</strong></div>
        <div><span>Text severity</span><strong>{oneDecimal(plan.violation_text_severity_score_0_100)}</strong></div>
        <div><span>Recovery / resource-hr</span><strong>{oneDecimal(plan.recovery_minutes_per_resource_hour)}</strong></div>
        <div><span>Evidence quality</span><strong>{oneDecimal(plan.evidence_quality_score_0_100)}</strong></div>
        <div><span>Operational priority</span><strong>{oneDecimal(plan.operational_priority_score_0_100)}</strong></div>
        <div><span>Patrol / tow hours</span><strong>{oneDecimal(plan.estimated_patrol_hours)} / {oneDecimal(plan.estimated_tow_hours)}</strong></div>
        <div><span>Recorded violations</span><strong>{compactNumber(plan.expected_violations)}</strong></div>
      </div>

      {roadspace && (
        <section className="brief-section">
          <h3>Road-space read</h3>
          <p><strong>Lane context:</strong> {roadspace.lane_context}</p>
          <p><strong>Dominant issue:</strong> {roadspace.dominant_lane_issue}</p>
          {roadspace.junction_sensitivity_label && <p><strong>Junction sensitivity:</strong> {roadspace.junction_sensitivity_label}</p>}
          {roadspace.corridor_name && (
            <p>
              <strong>Corridor:</strong> part of {roadspace.corridor_name}
              {roadspace.corridor_linked_hotspots ? ` — ${roadspace.corridor_linked_hotspots} linked hotspots` : ''}
              {roadspace.corridor_length_km ? `, ~${oneDecimal(roadspace.corridor_length_km)} km` : ''}
            </p>
          )}
          {plan.violation_text_severity_signature && (
            <p><strong>Violation severity signature:</strong> {plan.violation_text_severity_signature}</p>
          )}
          {plan.time_window_coverage_warning && (
            <p><strong>Reliability note:</strong> {plan.time_window_coverage_warning}</p>
          )}
        </section>
      )}

      {roadspace && roadspace.reason_codes?.length > 0 && (
        <section className="brief-section">
          <h3>Why this zone matters</h3>
          <ul className="brief-list">
            {roadspace.reason_codes.slice(0, 4).map((reason, index) => (
              <li key={index}>
                <strong>{reason.reason}</strong> <em>({reason.support_level})</em>
                <span>{reason.evidence}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="brief-section">
        <h3>Field action plan</h3>
        {roadspace && roadspace.mitigation_plan?.length > 0 ? (
          <ol className="brief-steps">
            {roadspace.mitigation_plan.map((step, index) => (
              <li key={index}><strong>{step.phase}:</strong> {step.step}</li>
            ))}
          </ol>
        ) : (
          <p>{plan.reasoning}</p>
        )}
      </section>

      <footer className="brief-footer">
        <span>Centroid {oneDecimal(plan.centroid_lat)}, {oneDecimal(plan.centroid_lon)} (from violation coordinates)</span>
        <span>
          Modelled estimates derived only from the enforcement violation dataset. Not live vehicle speed,
          surveyed lane GIS, signal-health telemetry, or live workforce data.
        </span>
      </footer>
    </article>
  );
}

export default ZoneBrief;
