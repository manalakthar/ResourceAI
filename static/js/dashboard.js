const COLORS = {High: '#d9534f', Medium: '#e8a33d', Low: '#3f9d78'};
const map = L.map('map', {scrollWheelZoom: false}).setView([12.95, 75.6], 7);
L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
  {attribution: '&copy; OpenStreetMap &copy; CARTO', maxZoom: 18}).addTo(map);
const layer = L.layerGroup().addTo(map);
let chart = null;

const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

async function load(type) {
  const res = await fetch('/api/dashboard?type=' + type);
  const d = await res.json();
  render(d);
}

function render(d) {
  const L_ = d.locations, unit = L_.length ? L_[0].unit : '';
  const deficits = L_.filter(r => r.status === 'Deficit').length;
  const surplus = L_.filter(r => r.status === 'Surplus').length;
  const moved = d.transfers.reduce((a, t) => a + t.quantity, 0);
  document.getElementById('meta').textContent =
    `${d.type === 'water' ? 'Water' : 'Food'} · data from ${d.date} · source: ${d.sources.join(', ')}` +
    (d.sources.includes('SAMPLE') ? ' (demo data, not real observations)' : '');
  document.getElementById('cards').innerHTML = [
    ['Locations tracked', L_.length, ''], ['In deficit', deficits, 'red'],
    ['In surplus', surplus, 'green'], ['Suggested to move', `${moved} ${unit}`, '']
  ].map(c => `<div class="card ${c[2]}"><span>${c[0]}</span><b>${esc(c[1])}</b></div>`).join('');

  layer.clearLayers();
  const pts = [];
  d.transfers.forEach(t => {
    L.polyline([[t.from_lat, t.from_lng], [t.to_lat, t.to_lng]], {
      color: '#1f7a8c', weight: 2 + Math.min(t.quantity / 15, 6), opacity: .85, className: 'flow-line'
    }).bindTooltip(`${esc(t.from)} → ${esc(t.to)}: ${t.quantity} ${esc(t.unit)} (${t.distance_km} km)`, {sticky: true}).addTo(layer);
  });
  L_.forEach(r => {
    pts.push([r.lat, r.lng]);
    L.circleMarker([r.lat, r.lng], {
      radius: 10 + Math.sqrt(r.required_quantity) / 2.2, color: '#fff', weight: 2,
      fillColor: COLORS[r.risk], fillOpacity: .9
    }).bindPopup(`<b>${esc(r.location)}</b><br>Available: ${r.available_quantity} ${esc(r.unit)}<br>` +
      `Required: ${r.required_quantity} ${esc(r.unit)}<br>Balance: ${r.balance > 0 ? '+' : ''}${r.balance}<br>` +
      `Coverage: ${Math.round(r.coverage * 100)}% (${r.risk} risk)`).addTo(layer);
  });
  if (pts.length) map.fitBounds(pts, {padding: [50, 50]});

  if (chart) chart.destroy();
  chart = new Chart(document.getElementById('chart'), {
    type: 'bar',
    data: {labels: L_.map(r => r.location), datasets: [
      {label: 'Available', data: L_.map(r => r.available_quantity), backgroundColor: '#1f7a8c', borderRadius: 4},
      {label: 'Required', data: L_.map(r => r.required_quantity), backgroundColor: '#c5d6d6', borderRadius: 4}]},
    options: {maintainAspectRatio: false, indexAxis: 'y',
      plugins: {legend: {position: 'bottom'}}, scales: {x: {title: {display: true, text: unit}}}}
  });

  const tbl = document.getElementById('tbl');
  tbl.innerHTML = d.transfers.length
    ? '<tr><th>From</th><th>To</th><th>Category</th><th>Quantity</th><th>Distance</th></tr>' +
      d.transfers.map(t => `<tr><td>${esc(t.from)}</td><td>${esc(t.to)}</td><td>${esc(t.category)}</td>` +
        `<td>${t.quantity} ${esc(t.unit)}</td><td>${t.distance_km} km</td></tr>`).join('')
    : '<tr><td>No transfers needed: there is no surplus or no deficit.</td></tr>';
  document.getElementById('unmet').textContent = d.unmet.length
    ? 'Still unmet after transfers: ' + d.unmet.map(u => `${u.location} (${u.quantity} ${u.unit})`).join(', ') : '';
}

document.querySelectorAll('#seg button').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('#seg button').forEach(x => x.classList.remove('on'));
  b.classList.add('on');
  load(b.dataset.type);
}));
load('water');
