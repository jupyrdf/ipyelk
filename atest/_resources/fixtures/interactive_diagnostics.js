// Failure context for 04_Interactive only. Never alters handlers or diagram state.
const key = '__ipyelkInteractiveDiagnostics';
const mode = arguments[0];
if (mode === 'stop' || mode === 'start') {
  const previous = window[key];
  if (previous) {
    window.removeEventListener('error', previous.error);
    window.removeEventListener('unhandledrejection', previous.rejection);
    delete window[key];
  }
}
if (mode === 'start') {
  const errors = [];
  const record = (kind, value) => {
    if (errors.length < 50) errors.push({ at: Date.now(), kind, message: String(value).slice(0, 2000) });
  };
  const error = (event) => record('error', event.error || event.message);
  const rejection = (event) => record('unhandledrejection', event.reason);
  window[key] = { errors, error, rejection };
  window.addEventListener('error', error);
  window.addEventListener('unhandledrejection', rejection);
}
if (mode === 'capture') {
  return {
    captured_at: Date.now(),
    dom: [...document.querySelectorAll('.jp-ElkView')].map((view) => ({
      id: view.id,
      edges: [...view.querySelectorAll('.elkedge')].map((edge) => ({
        id: edge.id, hidden: !!edge.closest('.sprotty-hidden')
      }))
    })),
    errors: window[key]?.errors || { unavailable: 'collector not installed' },
    frontend_model: { unavailable: 'no validated output renderer/widget manager reference on this test page' },
    sprotty_root: { unavailable: 'no validated renderer view reference on this test page' }
  };
}
