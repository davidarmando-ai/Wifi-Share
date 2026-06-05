document.addEventListener('DOMContentLoaded', function () {

  /* ── Toggle activar/desactivar rede ────────────── */
  document.querySelectorAll('.toggle-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var id = this.dataset.id;
      var self = this;
      self.classList.add('loading');
      fetch('/api/redes/' + id + '/toggle', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var isOn = data.ativa === 1;
          self.classList.toggle('on', isOn);
          self.classList.toggle('off', !isOn);
          var lbl = self.querySelector('.toggle-lbl');
          if (lbl) lbl.textContent = isOn ? 'Activa' : 'Inactiva';
          showToast(isOn ? 'Rede activada' : 'Rede desactivada', 'ok');
        })
        .catch(function () { showToast('Erro ao alterar estado', 'err'); })
        .finally(function () { self.classList.remove('loading'); });
    });
  });

  /* ── Eliminar rede ────────────────────────────── */
  document.querySelectorAll('.del-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var id = this.dataset.id;
      var nome = this.dataset.nome;
      if (!confirm('Eliminar a rede "' + nome + '" definitivamente?')) return;

      var self = this;
      self.disabled = true;
      self.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 12a9 9 0 1 1-6.22-8.56"/></svg>';

      fetch('/api/redes/' + id + '/deletar', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function () {
          var row = document.querySelector('tr[data-id="' + id + '"]');
          if (row) {
            row.style.transition = 'opacity .35s var(--ease), transform .35s var(--ease)';
            row.style.opacity = '0';
            row.style.transform = 'translateX(20px) scale(.96)';
            setTimeout(function () { row.remove(); }, 360);
          }
          showToast('Rede eliminada', 'ok');
        })
        .catch(function () { showToast('Erro ao eliminar', 'err'); });
    });
  });

  /* ── Desbloquear IP (na página de sessões) ───── */
  var desbloquearBtns = document.querySelectorAll('.desbloquear-btn');
  if (desbloquearBtns.length) {
    desbloquearBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var redeId = this.dataset.redeId;
        var ip = this.dataset.ip;
        if (!confirm('Desbloquear o IP ' + ip + '?')) return;

        fetch('/api/sessoes/' + redeId + '/desbloquear', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ip: ip })
        })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (d.ok) {
              showToast('IP desbloqueado!', 'ok');
              setTimeout(function () { location.reload(); }, 1000);
            } else {
              showToast('Erro: ' + (d.erro || 'desconhecido'), 'err');
            }
          })
          .catch(function () { showToast('Erro de rede', 'err'); });
      });
    });
  }

});
