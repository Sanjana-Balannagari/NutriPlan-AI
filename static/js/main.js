document.addEventListener('DOMContentLoaded', () => {
  const query = document.getElementById('query');
  const genBtn = document.getElementById('generate');
  const results = document.getElementById('results');
  const calSlider = document.getElementById('calories');
  const calVal = document.getElementById('calVal');

  // Update calorie display
  calSlider.addEventListener('input', () => {
    calVal.textContent = calSlider.value;
  });

  // Generate meal plan
  const generate = async () => {
    const q = query.value.trim();
    const calories = calSlider.value;
    const prefs = Array.from(document.querySelectorAll('#filters input:checked'))
                     .map(c => c.value);

    const resp = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: q,
        calories: calories,
        prefs: prefs.join(',')
      })
    });

    const plan = await resp.json();  // Always 3 meals: [Breakfast, Lunch, Dinner]
    render(plan);
    window.currentPlan = plan; // For PDF export
  };

  genBtn.addEventListener('click', generate);
  query.addEventListener('keypress', e => e.key === 'Enter' && generate());

  // === RENDER FUNCTION ===
  function render(plan) {
    if (!plan || plan.length === 0) {
      results.innerHTML = '<p class="text-center text-muted">No meals found.</p>';
      return;
    }

    // Total calories (only count valid meals)
    const totalCalories = plan.reduce((sum, m) => sum + (m.id !== 'N/A' ? m.calories : 0), 0);

    let html = `
      <div class="text-center mb-4">
        <h3>Your ${totalCalories}-Calorie Plan</h3>
        <button class="btn btn-outline-success btn-sm" onclick="exportPDF()">Export PDF</button>
        <button class="btn btn-outline-primary btn-sm ms-2" onclick="share()">Share</button>
      </div>
      <div class="row g-4">
    `;

    // Always render 3 meals in order
    plan.forEach(m => {
      const isMissing = m.id === 'N/A';
      const tags = m.tags.map(t => `<span class="badge tag-${t}">${t}</span>`).join('');
      const iconClass = m.type === 'Breakfast' ? 'bi-sun' :
                        m.type === 'Lunch' ? 'bi-cup-straw' : 'bi-moon-stars';

      html += `
        <div class="col-md-4">
          <div class="meal-card ${isMissing ? 'opacity-60' : ''}">
            <div class="icon-circle ${m.type.toLowerCase()}">
              <i class="bi ${iconClass}"></i>
            </div>
            <h5>${m.type}</h5>
            <h6 class="text-primary">${isMissing ? '<em>No match found</em>' : m.name}</h6>
            ${!isMissing ? `<p class="text-muted small">ID: <code>${m.id}</code></p>` : ''}
            <span class="badge bg-gradient ${isMissing ? 'bg-secondary' : ''}">
              ${m.calories} kcal
            </span>
            <div class="mt-2">${tags}</div>
            ${isMissing ? '<p class="text-danger small mt-2 mb-0">Try adjusting preferences</p>' : ''}
          </div>
        </div>
      `;
    });

    html += `</div>`;
    results.innerHTML = html;
  }

  // === EXPORT PDF ===
  window.exportPDF = async () => {
    if (!window.currentPlan) {
      alert("Generate a plan first!");
      return;
    }

    const resp = await fetch('/export_pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(window.currentPlan)
    });

    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'nutriplan_meal_plan.pdf';
    a.click();
    URL.revokeObjectURL(url);
  };

  // === SHARE LINK ===
  window.share = () => {
    navigator.clipboard.writeText(location.href).then(() => {
      alert('Link copied to clipboard!');
    }).catch(() => {
      prompt('Copy this link:', location.href);
    });
  };
});