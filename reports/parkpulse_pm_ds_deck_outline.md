# ParkPulse PM + Data Science Deck Outline

This rewrite follows the ChatGPT Plus deck prompt: product-led, judge-facing, honest about proxies, and built around impact-weighted enforcement prioritization.

## Slide 1: ParkPulse Bengaluru
- Objective: Hook judges on the decision question.
- Main takeaway: Which illegal parking should Bengaluru solve first?
- Content blocks: Dark title, headline metrics, product thesis.
- Suggested visual: Strong hero title with KPI strip.
- Speaker note: Open by saying this is not a heatmap; it is impact-weighted enforcement prioritization.
- Remove from current deck: Remove generic title clutter.

## Slide 2: The Real Problem
- Objective: Show that prioritization is the bottleneck.
- Main takeaway: All violations are not equal.
- Content blocks: Violation-to-spillback chain, raw heatmap limitation, ParkPulse addition.
- Suggested visual: Four-step flow plus three cards.
- Speaker note: Use lane blockage and scarce tow units as the story.
- Remove from current deck: Remove generic traffic dashboard language.

## Slide 3: Current Workflow vs ParkPulse Workflow
- Objective: Make the PM before/after obvious.
- Main takeaway: ParkPulse changes the operating model.
- Content blocks: Before/after table across bias, impact, ROI and feedback.
- Suggested visual: Two-column comparison.
- Speaker note: Say the current workflow sees records; ParkPulse creates actions.
- Remove from current deck: Remove dense methodology text.

## Slide 4: User Personas
- Objective: Show product users and jobs-to-be-done.
- Main takeaway: Command, station and field workflows share one OS.
- Content blocks: Commander, inspector, field officer cards.
- Suggested visual: Persona cards with metric.
- Speaker note: Explain that each user gets a different surface, not a generic dashboard.
- Remove from current deck: Remove broad user statements.

## Slide 5: Day-in-the-Life Journey
- Objective: Make adoption feel real.
- Main takeaway: The product fits the morning shift ritual.
- Content blocks: Five-step timeline from 7:30 AM to end-of-shift feedback.
- Suggested visual: Operational timeline.
- Speaker note: Narrate a real control-room morning.
- Remove from current deck: Remove abstract roadmap from early deck.

## Slide 6: Dataset and Honest Measurement
- Objective: Build trust.
- Main takeaway: Every claim is labelled.
- Content blocks: Observed/modelled/proxy/not available.
- Suggested visual: Four-column evidence contract.
- Speaker note: Say exact speed/queue reduction is not claimed.
- Remove from current deck: Remove overclaiming phrases.

## Slide 7: Bias Stress Test
- Objective: Explain why raw counts are risky.
- Main takeaway: ParkPulse corrects for visibility bias.
- Content blocks: Exposure correlation, validation timestamp, robust overlap, sparse evening records.
- Suggested visual: Metric strip plus validation figures.
- Speaker note: Say high count can mean more enforcement visibility.
- Remove from current deck: Remove unsupported density claims.

## Slide 8: EDA Insights
- Objective: Show the data story in few signals.
- Main takeaway: Targeted enforcement is justified.
- Content blocks: Concentration, repeat vehicles, chronic zones, road-space context.
- Suggested visual: Concentration chart and context chart.
- Speaker note: Use only 3-4 insights.
- Remove from current deck: Remove extra tables.

## Slide 9: Product Architecture
- Objective: Frame as an operating system.
- Main takeaway: Raw records become ranked actions.
- Content blocks: Five layers with input and output.
- Suggested visual: Architecture stack.
- Speaker note: Make it product architecture, not ML pipeline only.
- Remove from current deck: Remove code/process laundry lists.

## Slide 10: DS Core
- Objective: Explain modelling without overload.
- Main takeaway: Optimize top-K operational capture.
- Content blocks: Spatial/temporal units, features, target, validation, metrics.
- Suggested visual: Six modelling blocks.
- Speaker note: Tell why top-K matters for police.
- Remove from current deck: Remove generic accuracy metrics.

## Slide 11: Why Raw Density Is Not Enough
- Objective: Defend differentiation.
- Main takeaway: Prediction and action are different jobs.
- Content blocks: Three scenarios: over-patrolled, obstructive medium count, hidden risk.
- Suggested visual: Scenario cards.
- Speaker note: Say raw density predicts recurrence; ParkPulse decides action.
- Remove from current deck: Remove any 'model beats everything' framing.

## Slide 12: Scoring Logic
- Objective: Separate recurrence, explanation and dispatch.
- Main takeaway: No single magic score.
- Content blocks: Recurrence model, obstruction index, dispatch priority.
- Suggested visual: Three-score logic board.
- Speaker note: Repeat proxy honesty.
- Remove from current deck: Remove formula overload.

## Slide 13: Validation + Differentiation
- Objective: Show why honest validation still supports a stronger product.
- Main takeaway: Raw density tells us where violations return; ParkPulse tells us where limited enforcement creates highest payoff.
- Content blocks: Capture@20, raw-density baseline, robustness, recovery-proxy uplift, and raw heatmap vs ParkPulse table.
- Suggested visual: Metric strip plus comparison table.
- Speaker note: Defend the close model-vs-density result by separating prediction from action.
- Remove from current deck: Remove inflated ML claims and unclear metric denominators.

## Slide 14: Command Center
- Objective: Show working product.
- Main takeaway: A control room can act in seconds.
- Content blocks: Large product screenshot, KPI cards, risk map, priority queue, proxy labels.
- Suggested visual: Dominant live screenshot with short callouts.
- Speaker note: Walk through the screen like a duty officer.
- Remove from current deck: Remove decorative screenshots and long paragraph blocks.

## Slide 15: Station + Field Officer
- Objective: Complete the field journey.
- Main takeaway: The hotspot card becomes an action brief.
- Content blocks: Live hotspot screenshot plus field-brief card: location, window, action, reason, confidence, SLA, resource.
- Suggested visual: Screenshot plus mock field brief.
- Speaker note: Show how a field officer knows what to do.
- Remove from current deck: Remove excess charts.

## Slide 16: Deployment Simulator
- Objective: Show resource allocation.
- Main takeaway: Limited units become measurable plans.
- Content blocks: Resource inputs, selected zones, covered/uncovered risk, recovery-proxy uplift.
- Suggested visual: Large simulator screenshot plus resource-flow cards.
- Speaker note: Move sliders in the demo and clarify proxy meaning.
- Remove from current deck: Remove generic ROI claims.

## Slide 17: Rollout Roadmap
- Objective: Prove implementability.
- Main takeaway: Useful now; measurable as feeds arrive.
- Content blocks: Day 1 decision support, 30-day outcome learning, 90-day measured traffic impact, next command feeds.
- Suggested visual: PM roadmap.
- Speaker note: State exactly what data is needed next.
- Remove from current deck: Remove vague future AI.

## Slide 18: Defensibility and Close
- Objective: End with trust and ambition.
- Main takeaway: Defensible today. Measurable tomorrow.
- Content blocks: Claim with confidence now, transparent proxy, measure after integration.
- Suggested visual: Clean dark closing board.
- Speaker note: Final line: not a heatmap, a decision system for deciding what Bengaluru should solve first.
- Remove from current deck: Remove duplicate columns and hidden caveats.
