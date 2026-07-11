'use strict';

const DEFAULT_MODEL = 'gemma3:4b';
const DEFAULT_OLLAMA_URL = 'http://10.200.5.122:11434/api/generate';
const DEFAULT_OPTIONS = { temperature: 0.1, num_predict: 120 };

function stableEventKey(event = {}) {
  return event.key || [event.topic, event.type, event.status, event.reason].filter(Boolean).join(':') || 'unknown';
}

function createEvent(topic, type, decision = {}, extra = {}) {
  const status = decision.mode || decision.status || extra.status || 'unknown';
  const reason = decision.reason || extra.reason || 'unknown';
  return {
    topic,
    type,
    key: extra.key || `${type}:${status}:${reason}`,
    importance: extra.importance || 'normal',
    status,
    status_display: decision.status_display || extra.status_display || String(status),
    reason,
    reason_display: decision.reason_display || extra.reason_display || String(reason),
    notify: Boolean(extra.notify),
    speak: Boolean(extra.speak),
    ts: extra.ts || Date.now(),
  };
}

function compactSnapshot(ems = {}, event = {}) {
  const core = ems.core || {};
  return {
    timestamp: new Date().toISOString(),
    event: { ...event, key: stableEventKey(event) },
    core: {
      ems_enabled: Boolean(core.ems_enabled),
      hdo_state: core.hdo_state,
      battery_soc: core.battery_soc,
      battery_power: core.battery_power,
      pv_power: core.pv_power,
      grid_power: core.grid_power,
      surplus_power: core.surplus_power,
      deficit_power: core.deficit_power,
      house_power: core.house_power,
      target_soc: core.target_soc || ems.plan?.battery?.target_soc,
      effective_min_soc: core.effective_min_soc || ems.plan?.battery?.effective_min_soc,
      forecast_day_type_tomorrow: ems.plan?.strategy?.day_type_tomorrow,
    },
    safety: ems.safety,
    wallbox: ems.wallbox,
    boiler: ems.boiler,
    battery_grid: ems.battery_grid,
  };
}

function buildOllamaPayload(prompt, snapshot, model = DEFAULT_MODEL, options = DEFAULT_OPTIONS) {
  return {
    model,
    prompt: `${prompt}\n\nStav:\n${JSON.stringify(snapshot, null, 2)}`,
    stream: false,
    options,
  };
}

module.exports = {
  DEFAULT_MODEL,
  DEFAULT_OLLAMA_URL,
  DEFAULT_OPTIONS,
  stableEventKey,
  createEvent,
  compactSnapshot,
  buildOllamaPayload,
};
