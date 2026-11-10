import 'vite/modulepreload-polyfill';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const initial = JSON.parse(document.getElementById('initial-state').textContent);

async function post(url, payload) {
  const response = await fetch(url, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Could not apply this setting. Please try again.');
  return data;
}

// Debounce dragging and serialize writes so a slow response cannot overwrite a newer setting.
function useSlider(start, url, key) {
  const [value, setValue] = useState(start);
  const [status, setStatus] = useState('Changes apply automatically.');
  const [failed, setFailed] = useState(false);
  const queue = useRef(Promise.resolve());
  const revision = useRef(0);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (value === start && revision.current === 0 && attempt === 0) return;
    const current = ++revision.current;
    setStatus('Applying…');
    setFailed(false);
    const timer = setTimeout(() => {
      queue.current = queue.current.catch(() => {}).then(() => post(url, { [key]: value }))
        .then(() => { if (current === revision.current) setStatus('Applied to matrix.'); })
        .catch(error => { if (current === revision.current) { setStatus(error.message); setFailed(true); } });
    }, 180);
    return () => clearTimeout(timer);
  }, [value, attempt, start, url, key]);
  return { value, setValue, status, failed, retry: () => setAttempt(n => n + 1) };
}

function SliderCard({ id, title, setting, min, unit, low, high }) {
  return <section className="card control-card" aria-labelledby={`${id}-title`}>
    <h2 id={`${id}-title`}>{title}</h2>
    <div className="value"><output htmlFor={id}>{setting.value}</output><span>{unit}</span></div>
    <label className="sr-only" htmlFor={id}>{title}</label>
    <input id={id} type="range" min={min} max="100" step="1" value={setting.value}
      style={{ '--fill': `${(setting.value - min) / (100 - min) * 100}%` }}
      onChange={event => setting.setValue(Number(event.target.value))} />
    <div className="range-labels"><span>{low}</span><span>{high}</span></div>
    <div className="setting-status"><p role="status">{setting.status}</p>{setting.failed && <button className="text-button" onClick={setting.retry}>Retry</button>}</div>
  </section>;
}

function WeatherCard() {
  const [zipcode, setZipcode] = useState(initial.weatherLocation);
  const [saved, setSaved] = useState(initial.weatherLocation);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState('');
  async function save(event) {
    event.preventDefault(); setBusy(true); setStatus('Saving ZIP code…');
    try {
      const data = await post('/weather-location', { zipcode: zipcode.trim() });
      setZipcode(data.zipcode); setSaved(data.zipcode);
      setStatus(`Saved. Refreshing weather for ${data.zipcode}.`);
    } catch (error) { setStatus(error.message); }
    finally { setBusy(false); }
  }
  return <section className="card weather-card" aria-labelledby="weather-title">
    <div><h2 id="weather-title">Weather</h2>
      <p className="location">Current ZIP code <strong>{saved}</strong></p></div>
    <form onSubmit={save}><label htmlFor="zipcode">Weather ZIP code</label><div className="input-group">
      <input id="zipcode" type="text" inputMode="numeric" autoComplete="postal-code" pattern="[0-9]{5}(-[0-9]{4})?" maxLength="10" required value={zipcode} disabled={busy} onChange={event => setZipcode(event.target.value)} />
      <button className="primary-button" disabled={busy}>{busy ? 'Saving…' : 'Save ZIP code'}</button>
    </div><p className="hint">US ZIP or ZIP+4. Saved between restarts.</p><p role="status" className="form-status">{status}</p></form>
  </section>;
}

function formatDate(value) {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
}

function NewsFeed() {
  const [news, setNews] = useState(initial.news);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const active = useRef(false);
  const pending = useRef(null);
  const load = useCallback(async () => {
    if (!active.current || pending.current) return;
    const controller = new AbortController();
    pending.current = controller;
    setRefreshing(true);
    try {
      const response = await fetch('/news', { cache: 'no-store', signal: controller.signal });
      if (!response.ok) throw new Error();
      const data = await response.json();
      if (active.current) { setNews(data); setError(''); }
    } catch {
      if (active.current) setError('Could not refresh news. Try again.');
    } finally {
      pending.current = null;
      if (active.current) setRefreshing(false);
    }
  }, []);
  useEffect(() => {
    active.current = true;
    load();
    const timer = setInterval(load, 30000);
    return () => { active.current = false; pending.current?.abort(); clearInterval(timer); };
  }, [load]);
  return <section className="card news-card" aria-labelledby="news-title">
    <div className="news-header"><h2 id="news-title">Headlines<span className="count">{news.articles.length}</span></h2><button type="button" className="primary-button" disabled={refreshing} onClick={load} aria-controls="news-links">{refreshing ? 'Refreshing…' : 'Refresh'}</button></div>
    <p className="feed-status" role="status">{refreshing ? 'Refreshing headlines…' : news.cached ? 'Cached headlines' : `Loaded headlines${formatDate(news.updatedAt) ? ` · Updated ${formatDate(news.updatedAt)}` : ''}`}</p>
    {(error || news.error) && <p className="error" role="status">{error || news.error}</p>}
    <ol id="news-links" className="news-list" aria-busy={refreshing}>{news.articles.map((article, index) => {
      const safeUrl = /^https?:\/\//i.test(article.url || '') ? article.url : null;
      return <li key={`${article.url}-${index}`}><span className="story-number" aria-hidden="true">{String(index + 1).padStart(2, '0')}</span><div>
        {safeUrl ? <a href={safeUrl} target="_blank" rel="noopener noreferrer">{article.title}<span className="external-arrow" aria-hidden="true"> ↗</span></a> : <span className="story-title">{article.title}</span>}
        <p className="story-meta">{[article.source, formatDate(article.publishedAt)].filter(Boolean).join(' · ')}</p>
      </div></li>;
    })}</ol>
    {news.articles.length === 0 && <div className="empty-state">No headlines available.</div>}
    <div className="news-footer">List refreshes every 30 seconds.</div>
  </section>;
}

function FishTable({ disabled, onBusyChange }) {
  const [fishes, setFishes] = useState(initial.fishes || []);
  const [pending, setPending] = useState(null);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    let timer;
    const controller = new AbortController();
    async function load() {
      try {
        const response = await fetch('/aquarium/fishes', { cache: 'no-store', signal: controller.signal });
        if (!response.ok) throw new Error('Could not load fish. Retrying…');
        const data = await response.json();
        if (active) { setFishes(data.fishes); setError(''); }
      } catch (error) { if (active) setError(error.message); }
      finally { if (active) timer = setTimeout(load, 1000); }
    }
    load();
    return () => { active = false; controller.abort(); clearTimeout(timer); };
  }, []);
  async function changeFish(id = null, action = 'regenerate') {
    setPending(id === null ? 'add' : `${action}-${id}`);
    onBusyChange(true);
    setStatus('');
    try {
      if (action === 'delete') {
        const response = await fetch(`/aquarium/fishes/${id}`, { method: 'DELETE' });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Could not delete fish.');
        setStatus(`Deletion requested for Fish ${id}.`);
      } else {
        await post(id === null ? '/aquarium/fishes' : `/aquarium/fishes/${id}/regenerate`, {});
        setStatus(id === null ? 'New fish requested.' : `New shape and colors requested for Fish ${id}.`);
      }
    } catch (error) { setStatus(error.message); }
    finally { setPending(null); onBusyChange(false); }
  }
  return <section className="fish-table-section" aria-labelledby="fish-table-title">
    <div className="news-header"><h2 id="fish-table-title">Fish <span className="count">{fishes.length}</span></h2>
      <button type="button" className="primary-button" disabled={disabled || pending !== null}
        onClick={() => changeFish()}>{pending === 'add' ? 'Adding…' : 'add fish'}</button></div>
    <div className="fish-table-scroll"><table className="fish-table">
      <thead><tr><th scope="col">Fish</th><th scope="col">Cruise speed (px/s)</th><th scope="col">Seed</th><th scope="col"><span className="sr-only">Actions</span></th></tr></thead>
      <tbody>{fishes.map(fish => <tr key={fish.id}><th scope="row">Fish {fish.id}</th>
        <td>{Number(fish.speed).toFixed(1)}</td><td className="fish-seed">{fish.seed}</td>
        <td><button type="button" className="primary-button" disabled={disabled || pending !== null}
          aria-label={`gen new fish ${fish.id}`} onClick={() => changeFish(fish.id)}>
          {pending === `regenerate-${fish.id}` ? 'Generating…' : 'gen new fish'}</button>
          <button type="button" className="text-button delete-fish" disabled={disabled || pending !== null}
            aria-label={`delete fish ${fish.id}`} onClick={() => changeFish(fish.id, 'delete')}>
            {pending === `delete-${fish.id}` ? 'Deleting…' : 'delete fish'}</button></td></tr>)}</tbody>
    </table></div>
    {fishes.length === 0 && <p>No fish. Use add fish to create one.</p>}
    <p role="status">{error || status}</p>
  </section>;
}

function App() {
  const brightness = useSlider(initial.brightness, '/', 'out');
  const speed = useSlider(initial.tickerSpeed, '/ticker-speed', 'speed');
  const [tickerEnabled, setTickerEnabled] = useState(initial.tickerEnabled);
  const [toggling, setToggling] = useState(false);
  const [toggleStatus, setToggleStatus] = useState('');
  const [fishMode, setFishMode] = useState(initial.fishMode);
  const [switchingMode, setSwitchingMode] = useState(false);
  const [modeError, setModeError] = useState('');
  const [generatingSand, setGeneratingSand] = useState(false);
  const [sandStatus, setSandStatus] = useState('');
  const [generatingFish, setGeneratingFish] = useState(false);
  const [shadowMode, setShadowMode] = useState(initial.shadowMode);
  const [switchingShadow, setSwitchingShadow] = useState(false);
  const [shadowStatus, setShadowStatus] = useState('');
  async function toggleShadowMode() {
    setSwitchingShadow(true);
    setShadowStatus('');
    try {
      const data = await post('/aquarium/shadow', { enabled: !shadowMode });
      setShadowMode(data.enabled);
      setShadowStatus(data.enabled ? 'Shadow mode on.' : 'Random fish colors restored.');
    } catch (error) { setShadowStatus(error.message); }
    finally { setSwitchingShadow(false); }
  }
  async function generateSand() {
    setGeneratingSand(true);
    setSandStatus('');
    try {
      await post('/aquarium/sand', {});
      setSandStatus('New sand requested.');
    } catch (error) { setSandStatus(error.message); }
    finally { setGeneratingSand(false); }
  }
  async function toggleFishMode() {
    setSwitchingMode(true);
    setModeError('');
    try {
      const data = await post('/fish-mode', { enabled: !fishMode });
      setFishMode(data.enabled);
      setSandStatus('');
    } catch (error) { setModeError(error.message); }
    finally { setSwitchingMode(false); }
  }
  async function toggleTicker() {
    setToggling(true);
    setToggleStatus('');
    try {
      const data = await post('/ticker-enabled', { enabled: !tickerEnabled });
      setTickerEnabled(data.enabled);
      setToggleStatus(data.enabled ? 'Ticker on.' : 'Ticker off.');
    } catch (error) { setToggleStatus(error.message); }
    finally { setToggling(false); }
  }
  return <div className="app-shell">
    <header className="site-header"><a className="brand" href="/" aria-label="LED Matrix home"><span className="matrix-mark" aria-hidden="true">{Array.from({ length: 9 }, (_, i) => <i key={i} />)}</span>LED<span> / </span>MATRIX</a><span className="device-address">{initial.ip}</span></header>
    <main><div className="page-heading"><h1>LED Matrix Settings</h1><div className="hardware-tag">128 × 32 RGB MATRIX</div></div>
      <section className="card display-mode" aria-label="Display mode">
        <button type="button" className="primary-button fish-button" aria-pressed={fishMode}
          disabled={switchingMode || generatingSand || generatingFish} onClick={toggleFishMode}>FISH</button>
        <p role="status">{modeError || (switchingMode ? 'Applying…' : fishMode
          ? 'FISH mode on. Clock, weather, and ticker off. Press FISH to restore.'
          : 'FISH mode off.')}</p>
      </section>
      {fishMode && <section className="card aquarium-controls" aria-label="Aquarium controls">
        <button type="button" className="primary-button" disabled={generatingSand || generatingFish || switchingMode}
          onClick={generateSand}>{generatingSand ? 'Generating…' : 'Generate new sand'}</button>
        <div className="ticker-toggle"><span id="shadow-mode-label">Shadow mode</span>
          <button type="button" className="toggle-switch" role="switch" aria-checked={shadowMode}
            aria-labelledby="shadow-mode-label" disabled={switchingShadow || switchingMode}
            onClick={toggleShadowMode}>
            <span className="toggle-track" aria-hidden="true"><span /></span>
            <span>{switchingShadow ? 'Applying…' : shadowMode ? 'On' : 'Off'}</span>
          </button>
        </div>
        <p role="status">{sandStatus}</p>
        <p role="status">{shadowStatus}</p>
        <FishTable disabled={switchingMode || generatingSand} onBusyChange={setGeneratingFish} />
      </section>}
      <div className="controls-grid"><SliderCard id="brightness" title="Brightness" setting={brightness} min={1} unit="%" low="Dim" high="Bright" />
        <WeatherCard /></div>
      <p className="session-note">Brightness resets when the app restarts. Automatic brightness scheduling is not available.</p>
      <section className="card ticker-section" aria-labelledby="ticker-title">
        <div className="ticker-heading"><h2 id="ticker-title">News</h2>
          <div className="ticker-toggle"><span id="ticker-toggle-label">Ticker tape</span>
            <button type="button" className="toggle-switch" role="switch" aria-checked={tickerEnabled}
              aria-labelledby="ticker-toggle-label" disabled={toggling} onClick={toggleTicker}>
              <span className="toggle-track" aria-hidden="true"><span /></span>
              <span>{toggling ? 'Applying…' : tickerEnabled ? 'On' : 'Off'}</span>
            </button>
          </div>
          <p className="toggle-status" role="status">{toggleStatus}</p>
        </div>
        <div className="ticker-grid">
          <div><SliderCard id="ticker-speed" title="Ticker speed" setting={speed} min={0} unit="px / second" low="0 · Paused" high="100 · Fast" />
            <p className="session-note">Ticker settings reset when the app restarts.</p></div>
          <NewsFeed />
        </div>
      </section>
    </main>
  </div>;
}

createRoot(document.getElementById('root')).render(<App />);
