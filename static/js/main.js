document.addEventListener('DOMContentLoaded', () => {
  const query = document.getElementById('query');
  const genBtn = document.getElementById('generate');
  const results = document.getElementById('results');
  const calSlider = document.getElementById('calories');
  const calVal = document.getElementById('calVal');

  calSlider.addEventListener('input', () => calVal.textContent = calSlider.value);

  const generate = async () => {
    const q = query.value.trim();
    const calories = calSlider.value;
    const prefs = Array.from(document.querySelectorAll('#filters input:checked')).map(c => c.value);

    const resp = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: q, calories, prefs: prefs.join(',') })
    });
    const plan = await resp.json();
    render(plan);
  };

  genBtn.addEventListener('click', generate);
  query.addEventListener('keypress', e => e.key === 'Enter' && generate());

  function render(plan) {
    if (!plan.length) { results.innerHTML = '<p class="text-center text-muted">No meals found.</p>'; return; }

    let html = `<div class="text-center mb-4">
      <h3>Your ${plan[0].total_calories}-Calorie Plan</h3>
      <button class="btn btn-outline-success btn-sm" onclick="exportPDF()">Export PDF</button>
      <button class="btn btn-outline-primary btn-sm ms-2" onclick="share()">Share</button>
    </div><div class="row g-4">`;

    plan.forEach(m => {
      const tags = m.tags.map(t => `<span class="badge tag-${t}">${t}</span>`).join('');
      html += `<div class="col-md-4">
        <div class="meal-card">
          <div class="icon-circle ${m.type.toLowerCase()}">
            <i class="bi ${m.type==='Breakfast'?'bi-sun':m.type==='Lunch'?'bi-cup-straw':'bi-moon-stars'}"></i>
          </div>
          <h5>${m.type}</h5>
          <h6 class="text-primary">${m.name}</h6>
          <p class="text-muted small">ID: <code>${m.id}</code></p>
          <span class="badge bg-gradient">${m.calories} kcal</span>
          <div class="mt-2">${tags}</div>
        </div>
      </div>`;
    });
    html += `</div>`;
    results.innerHTML = html;
  }

  window.exportPDF = async () => {
    const resp = await fetch('/export_pdf', { method: 'POST' });
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'meal_plan.pdf'; a.click();
  };

  window.share = () => {
    navigator.clipboard.writeText(location.href);
    alert('Link copied!');
  };
});