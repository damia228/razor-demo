const dialog = document.getElementById('leadDialog');
let currentLead = null;
const $ = (id) => document.getElementById(id);

async function openLead(id){
  const r = await fetch(`/admin/api/lead/${id}`);
  if(!r.ok) return;
  currentLead = await r.json();
  $('dName').textContent = currentLead.name;
  $('dPhone').textContent = currentLead.phone;
  $('dPhoneLink').href = `tel:${currentLead.phone}`;
  $('dService').textContent = currentLead.service || '—';
  $('dWidth').textContent = currentLead.width || '—';
  $('dBudget').textContent = currentLead.budget || '—';
  $('dSource').textContent = currentLead.source || 'site';
  $('dDetails').textContent = currentLead.details || '—';
  $('dStatus').value = currentLead.status;
  $('dDeal').value = currentLead.deal_value ?? '';
  $('dNotes').value = currentLead.notes || '';
  $('saveState').textContent = '';
  dialog.showModal();
}

document.querySelectorAll('.open-lead').forEach(b => b.addEventListener('click', () => openLead(b.dataset.id)));
$('saveLead')?.addEventListener('click', async () => {
  if(!currentLead) return;
  $('saveState').textContent = 'Сохраняем…';
  const r = await fetch(`/admin/api/lead/${currentLead.id}`, {
    method:'PATCH', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({status:$('dStatus').value,deal_value:$('dDeal').value,notes:$('dNotes').value})
  });
  const data = await r.json().catch(()=>({}));
  if(!r.ok){ $('saveState').textContent = data.error || 'Ошибка сохранения'; return; }
  $('saveState').textContent = 'Сохранено';
  setTimeout(()=>location.reload(), 450);
});

fetch('/admin/api/analytics').then(r=>r.json()).then(data=>{
  const max = Math.max(1, ...data.daily.map(x=>x.count));
  $('dailyChart').innerHTML = data.daily.map(x=>`<div class="bar" style="height:${Math.max(3, x.count/max*100)}%" data-tip="${x.date}: ${x.count}"></div>`).join('');
  const smax = Math.max(1, ...data.services.map(x=>x.count));
  $('serviceChart').innerHTML = data.services.length ? data.services.map(x=>`<div class="service-line"><span>${x.name}</span><div class="service-track"><div class="service-fill" style="width:${x.count/smax*100}%"></div></div><b>${x.count}</b></div>`).join('') : '<span style="color:#777;font-size:12px">Пока нет данных</span>';
}).catch(()=>{});
